import tempfile, time, unittest
from pathlib import Path
from engine import Network, connect, submit, compute, POINTS
from crypto_analysis import analyze, parse_candles
from server import parse_rows

CANDLES=[
 {"start":"1700000000","open":"100","high":"105","low":"98","close":"104","volume":"50"},
 {"start":"1700003600","open":"104","high":"108","low":"103","close":"107","volume":"51"},
 {"start":"1700007200","open":"107","high":"110","low":"101","close":"102","volume":"52"}]

class GenesisTests(unittest.TestCase):
    def test_geometry(self):
        self.assertEqual(len(POINTS),8)
        self.assertEqual(POINTS,[(-3,0),(0,3),(3,3),(3,0),(3,-3),(0,-3),(-3,-3),(-3,3)])
    def test_math(self):
        self.assertEqual(compute("sum_squares",{"n":10})["sum"],385)
        self.assertEqual(compute("sha256_chain",{"n":3})["iterations"],3)
    def test_science(self):
        self.assertEqual(len(parse_rows("asteroid",{"fields":["des","dist"],"data":[["A","0.01"]]})),1)
        self.assertEqual(len(parse_rows("earthquake",{"features":[{"properties":{"place":"X","mag":3},"geometry":{"coordinates":[0,0,10]}}]})),1)
    def test_crypto_metrics(self):
        p={"product":"BTC-USD","candles":CANDLES}
        x=compute("crypto_candles",p)
        self.assertEqual(x["samples"],3)
        self.assertEqual(x["last_close_usd"],102)
        self.assertEqual(x["volume_total"],153)
        self.assertLess(x["max_close_drawdown_pct"],10)
    def test_crypto_rejects_invalid_ohlc(self):
        broken=[dict(v) for v in CANDLES]
        broken[1]["high"]="90"
        with self.assertRaises(ValueError):parse_candles({"candles":broken})
    def test_worker_recovery_and_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"test.db")
            net=Network(path,count=3)
            try:
                ids=[submit("sum_squares",{"n":1000},path) for _ in range(36)]
                net.kill(1)
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    stats=net.state()["stats"]
                    if stats["done"]==len(ids):break
                    time.sleep(.06)
                self.assertEqual(net.state()["stats"]["done"],36)
                self.assertEqual(net.report()["unique_results"],36)
                self.assertEqual(net.state()["duplicate_completion_records"],0)
            finally:net.close()
            restarted=Network(path,count=2)
            try:
                self.assertEqual(restarted.state()["stats"]["done"],36)
                self.assertEqual(restarted.state()["throughput_tasks_per_second"],0)
            finally:restarted.close()
    def test_orphaned_job_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            path=str(Path(folder)/"test.db")
            from engine import initialize
            initialize(path)
            tid=submit("sum_squares",{"n":20},path)
            with connect(path) as db:
                db.execute("UPDATE tasks SET status='running',worker=99 WHERE id=?",(tid,))
            net=Network(path,count=2)
            try:
                deadline=time.monotonic()+10
                while time.monotonic()<deadline and net.state()["stats"]["done"]<1:time.sleep(.05)
                self.assertEqual(net.state()["stats"]["done"],1)
                self.assertTrue(any(e["type"]=="restart_requeued" for e in net.state()["events"]))
            finally:net.close()

if __name__=="__main__":unittest.main()
