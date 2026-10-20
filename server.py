"""Servidor de desarrollo Split Run Genesis. Mantener puerto privado."""
import json, os, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from engine import Network, submit
ROOT=Path(__file__).resolve().parent
NASA_EXAMPLE={"fields":["des","dist"],"data":[["2015 AB","0.003"],["2010 XY","0.007"],["2020 AC","0.014"]]}
def parse_rows(kind,obj):
    if kind=="earthquake":
        features=obj.get("features",[])
        if not isinstance(features,list):raise ValueError("GeoJSON inválido")
        return [{"place":x.get("properties",{}).get("place","Desconocido"),
                 "magnitude":x.get("properties",{}).get("mag"),
                 "depth_km":(x.get("geometry",{}).get("coordinates") or [0,0,0])[2]} for x in features[:300]
                 if x.get("properties",{}).get("mag") is not None and len(x.get("geometry",{}).get("coordinates") or [])>=3]
    fields=obj.get("fields",[])
    des=fields.index("des") if "des" in fields else fields.index("desig") if "desig" in fields else None
    dist=fields.index("dist") if "dist" in fields else None
    if des is None or dist is None:raise ValueError("Formato NASA inválido")
    return [{"designation":str(r[des]),"distance_au":float(r[dist])} for r in obj.get("data",[])[:300]]
class Handler(BaseHTTPRequestHandler):
    def reply(self,data,status=200):
        body=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        n=self.server.network
        if self.path=="/api/state":return self.reply(n.state())
        if self.path=="/api/report":return self.reply(n.report())
        if self.path=="/api/results":return self.reply(n.results())
        if self.path in ("/","/index.html"):
            data=(ROOT/"index.html").read_bytes()
            self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
            return
        return self.reply({"error":"No encontrado"},404)
    def do_POST(self):
        try:
            size=int(self.headers.get("Content-Length","0"))
            if size<0 or size>1500000:raise ValueError("Tamaño de petición inválido")
            data=json.loads(self.rfile.read(size)) if size else {}
            n=self.server.network
            if self.path=="/api/batch":
                count=int(data.get("count",100))
                if not 1<=count<=1000:raise ValueError("count debe ser 1..1000")
                for _ in range(count):submit(data.get("kind","sum_squares"),{"n":int(data.get("n",200))},n.path)
                return self.reply({"submitted":count})
            if self.path=="/api/tasks":
                return self.reply({"id":submit(data["kind"],{"n":int(data.get("n",1000))},n.path)})
            if self.path=="/api/kill":
                return self.reply({"ok":n.kill(int(data["id"]))})
            if self.path=="/api/public/example":
                feed="asteroid";obj=NASA_EXAMPLE;source="Ejemplo ilustrativo; no es consulta NASA en vivo"
            elif self.path=="/api/public/import":
                feed=data["kind"];obj=data["data"];source="Datos proporcionados por usuario"
            elif self.path=="/api/public/live":
                feed=data.get("feed","earthquake")
                urls={"earthquake":"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson",
                      "asteroid":"https://ssd-api.jpl.nasa.gov/cad.api?date-min=2026-10-20&date-max=2026-11-20&dist-max=10LD&limit=100"}
                if feed not in urls:raise ValueError("Fuente no permitida")
                req=urllib.request.Request(urls[feed],headers={"User-Agent":"SplitRunGenesisResearch/1.0"})
                with urllib.request.urlopen(req,timeout=12) as r:
                    raw=r.read(1500001)
                if len(raw)>1500000:raise ValueError("Respuesta demasiado grande")
                obj=json.loads(raw);source=urls[feed]
            else:return self.reply({"error":"No encontrado"},404)
            if feed not in ("earthquake","asteroid"):raise ValueError("Tipo inválido")
            rows=parse_rows(feed,obj)
            for row in rows:submit(feed,row,n.path)
            return self.reply({"submitted":len(rows),"source":source})
        except Exception as exc:
            return self.reply({"error":str(exc)},400)
    def log_message(self,*args):pass
if __name__=="__main__":
    n=Network(os.getenv("SPLIT_DB",str(ROOT/"genesis.sqlite3")))
    host=os.getenv("SPLIT_HOST","127.0.0.1");port=int(os.getenv("SPLIT_PORT","8765"))
    http=ThreadingHTTPServer((host,port),Handler);http.network=n
    print(f"Split Run Genesis: http://{host}:{port}",flush=True)
    try:http.serve_forever()
    except KeyboardInterrupt:pass
    finally:http.server_close();n.close()
