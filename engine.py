"""Split Run Genesis: workers independientes y cola persistente SQLite."""
import hashlib, json, multiprocessing as mp, os, sqlite3, threading, time, uuid
from pathlib import Path
from crypto_analysis import analyze

DB = os.getenv("SPLIT_DB", "genesis.sqlite3")
POINTS = [(-3,0),(0,3),(3,3),(3,0),(3,-3),(0,-3),(-3,-3),(-3,3)]
AU_KM = 149597870.7
LD_KM = 384400

def connect(path=DB):
    db=sqlite3.connect(str(path),timeout=20,isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=20000")
    return db

def initialize(path=DB):
    with connect(path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS tasks
          (id TEXT PRIMARY KEY,kind TEXT NOT NULL,payload TEXT NOT NULL,
           status TEXT NOT NULL DEFAULT 'pending', result TEXT,
           worker INTEGER, created REAL NOT NULL, finished REAL, attempts INTEGER NOT NULL DEFAULT 0)""")
        db.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, at REAL, type TEXT, detail TEXT)")

def event(db,typ,detail):
    db.execute("INSERT INTO events(at,type,detail) VALUES(?,?,?)",(time.time(),typ,str(detail)))

def submit(kind,payload,path=DB):
    if kind not in ("sum_squares","sha256_chain","earthquake","asteroid","crypto_candles"):
        raise ValueError("Tipo de tarea no admitido")
    tid=uuid.uuid4().hex
    with connect(path) as db:
        db.execute("INSERT INTO tasks(id,kind,payload,status,created) VALUES(?,?,?,'pending',?)",
                   (tid,kind,json.dumps(payload),time.time()))
    return tid

def compute(kind,p):
    if kind=="crypto_candles":return analyze(p)
    if kind=="sum_squares":
        n=int(p.get("n",100)); assert 0<=n<=1000000
        return {"sum":n*(n+1)*(2*n+1)//6}
    if kind=="sha256_chain":
        n=int(p.get("n",1000)); assert 0<=n<=100000
        h=b"split-run"
        for _ in range(n): h=hashlib.sha256(h).digest()
        return {"digest":h.hex(),"iterations":n}
    if kind=="earthquake":
        return {"place":str(p.get("place","Desconocido"))[:150],
                "magnitude":float(p["magnitude"]),"depth_km":float(p.get("depth_km",0))}
    if kind=="asteroid":
        au=float(p["distance_au"]); km=au*AU_KM
        return {"designation":str(p.get("designation","?"))[:100],
                "distance_km":round(km,2),"lunar_distances":round(km/LD_KM,4),
                "within_10_lunar_distances":km<=10*LD_KM}
    raise ValueError("Tipo inválido")

def work(worker_id,path,stop):
    db=connect(path)
    try:
        while not stop.is_set():
            try:
                db.execute("BEGIN IMMEDIATE")
                item=db.execute("SELECT id,kind,payload FROM tasks WHERE status='pending' ORDER BY created LIMIT 1").fetchone()
                if item:
                    db.execute("UPDATE tasks SET status='running',worker=?,attempts=attempts+1 WHERE id=?",(worker_id,item[0]))
                db.execute("COMMIT")
                if item is None:
                    stop.wait(.035);continue
                tid,kind,payload=item
                try:
                    result=compute(kind,json.loads(payload))
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("UPDATE tasks SET status='done',result=?,finished=? WHERE id=? AND status='running' AND worker=?",
                               (json.dumps(result),time.time(),tid,worker_id))
                    db.execute("COMMIT")
                except Exception as exc:
                    db.execute("BEGIN IMMEDIATE")
                    db.execute("UPDATE tasks SET status='failed',result=?,finished=? WHERE id=? AND status='running' AND worker=?",(json.dumps({"error":str(exc)}),time.time(),tid,worker_id))
                    db.execute("COMMIT")
            except sqlite3.OperationalError:
                try:db.execute("ROLLBACK")
                except sqlite3.OperationalError:pass
                stop.wait(.05)
    finally: db.close()

class Network:
    def __init__(self,path=DB,count=8):
        self.path=str(path);self.count=count;initialize(self.path)
        with connect(self.path) as db:
            orphaned=db.execute("UPDATE tasks SET status='pending',worker=NULL WHERE status='running'").rowcount
            if orphaned:event(db,"restart_requeued",orphaned)
        self.stop=mp.Event();self.processes={};self.guard=threading.Lock()
        self.closed=False;self.started=time.monotonic();self.base_done=self._done_count();self.initial_restarts=self._event_count("worker_restarted")
        for i in range(1,count+1):self.launch(i)
        self.supervisor=threading.Thread(target=self.monitor,daemon=True)
        self.supervisor.start()
    def _done_count(self):
        with connect(self.path) as db:return db.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0]
    def _event_count(self,typ):
        with connect(self.path) as db:return db.execute("SELECT COUNT(*) FROM events WHERE type=?",(typ,)).fetchone()[0]
    def launch(self,i):
        p=mp.Process(target=work,args=(i,self.path,self.stop),daemon=True,name=f"Cell-{i}")
        p.start();self.processes[i]=p
    def monitor(self):
        while not self.closed:
            with self.guard:
                for i,p in list(self.processes.items()):
                    if not p.is_alive() and not self.closed:
                        p.join(timeout=.1)
                        with connect(self.path) as db:
                            db.execute("UPDATE tasks SET status='pending',worker=NULL WHERE status='running' AND worker=?",(i,))
                            event(db,"worker_restarted",i)
                        self.launch(i)
            time.sleep(.15)
    def kill(self,i):
        with self.guard:
            p=self.processes.get(int(i))
            if p and p.is_alive():p.terminate();return True
            return False
    def state(self):
        with connect(self.path) as db:
            stats={k:db.execute("SELECT COUNT(*) FROM tasks WHERE status=?",(k,)).fetchone()[0] for k in ("pending","running","done","failed")}
            logs=db.execute("SELECT at,type,detail FROM events ORDER BY id DESC LIMIT 25").fetchall()
            restarts=db.execute("SELECT COUNT(*) FROM events WHERE type='worker_restarted'").fetchone()[0]
            duplicate=db.execute("SELECT COUNT(*)-COUNT(DISTINCT id) FROM tasks WHERE status='done'").fetchone()[0]
            retries=db.execute("SELECT COUNT(*) FROM tasks WHERE attempts>1").fetchone()[0]
            latency=db.execute("SELECT AVG(finished-created) FROM tasks WHERE status='done'").fetchone()[0]
        with self.guard:
            nodes=[{"id":i,"alive":p.is_alive(),"pid":p.pid,
                    "x":POINTS[i-1][0],"y":POINTS[i-1][1]} for i,p in self.processes.items()]
        return {"stats":stats,"cells":nodes,"events":[{"at":a,"type":t,"detail":d} for a,t,d in logs],
                "throughput_tasks_per_second":round(max(0,stats["done"]-self.base_done)/max(time.monotonic()-self.started,.001),2),
                "restarts":restarts,"duplicate_completion_records":duplicate,"attempts_retried":retries,
                "average_task_latency_seconds":round(latency or 0,4)}
    def report(self):
        s=self.state()
        with connect(self.path) as db:
            s["attempts_retried"]=db.execute("SELECT COUNT(*) FROM tasks WHERE attempts>1").fetchone()[0]
            s["unique_results"]=db.execute("SELECT COUNT(DISTINCT id) FROM tasks WHERE status='done'").fetchone()[0]
        return s
    def results(self):
        with connect(self.path) as db:
            rows=db.execute("SELECT id,kind,result,status FROM tasks WHERE result IS NOT NULL ORDER BY finished DESC LIMIT 100").fetchall()
        return [{"id":i,"kind":k,"result":json.loads(r),"status":s} for i,k,r,s in rows]
    def close(self):
        self.closed=True;self.stop.set()
        with self.guard:
            for p in self.processes.values():
                p.join(timeout=1)
                if p.is_alive():p.terminate();p.join(timeout=1)
        self.supervisor.join(timeout=1)

if __name__=="__main__":
    import unittest
    print("Split Run engine ready; run python server.py")
