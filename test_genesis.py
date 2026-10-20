import tempfile,time,unittest
from pathlib import Path
from engine import Network,submit,compute,POINTS,connect
from server import parse_rows

class GenesisTests(unittest.TestCase):
    def test_geometry(self):
        self.assertEqual(len(POINTS),8)
        self.assertIn((-3,0),POINTS)
        self.assertIn((0,3),POINTS)
    def test_math(self):
        self.assertEqual(compute("sum_squares",{"n":10})["sum"],385)
    def test_science(self):
        self.assertEqual(len(parse_rows("asteroid",{"fields":["des","dist"],"data":[["A","0.01"]]})),1)
        self.assertEqual(len(parse_rows("earthquake",{"features":[{"properties":{"place":"X","mag":3},"geometry":{"coordinates":[0,0,10]}}]})),1)
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
            finally:net.close()
            restarted=Network(path,count=2)
            try:
                self.assertEqual(restarted.state()["stats"]["done"],36)
                with connect(path) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM tasks WHERE status='done'").fetchone()[0],36)
            finally:restarted.close()

if __name__=="__main__":unittest.main()
