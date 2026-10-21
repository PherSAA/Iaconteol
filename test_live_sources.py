import unittest
from live_sources import earthquakes,asteroids,cryptos,social_posts,LiveMonitor
class SourceTests(unittest.TestCase):
 def test_usgs_timestamp(self):
  x={"features":[{"id":"eq1","properties":{"mag":4.0,"place":"Test","time":1700000000000,"url":"https://earthquake.usgs.gov/x"},"geometry":{"coordinates":[-120,40,10]}}]}
  out=earthquakes(x)
  self.assertEqual(out["count"],1)
  self.assertIn("2023-",out["recent"][0]["time"])
 def test_nasa_date(self):
  out=asteroids({"fields":["des","cd","dist"],"data":[["Object-1","2026-Oct-22","0.01"]]})
  self.assertEqual(out["count"],1)
  self.assertEqual(out["closest"][0]["date"],"2026-Oct-22")
 def test_crypto_exchanges(self):
  def sample(url):
   return [[1700000000,90,110,100,105,10],[1700003600,90,120,105,110,11],[1700007200,90,120,110,115,12]]
  out=cryptos(sample)
  self.assertEqual(len(out),4)
  self.assertEqual(out["BTC-USD"]["last_close"],115)
 def test_social_extract(self):
  def sample(url):
   return {"posts":[{"author":{"handle":"tester.bsky.social"},"uri":"at://tester.bsky.social/app.bsky.feed.post/abc","record":{"text":"test","createdAt":"2026-10-21T10:00:00Z"}}]}
  r=social_posts("bitcoin",sample)
  self.assertEqual(r["count"],1)
  self.assertTrue(r["posts"][0]["url"].startswith("https://"))
 def test_cache_no_network(self):
  called=[]
  def sample(url):
   called.append(url)
   if "earthquake" in url:return {"features":[]}
   if "jpl" in url:return {"fields":["des","dist"],"data":[]}
   return [[1700000000,90,110,100,105,10],[1700003600,90,120,105,110,11],[1700007200,90,120,110,115,12]]
  monitor=LiveMonitor(sample)
  first=monitor.refresh()
  self.assertEqual(first["sources"]["usgs"]["status"],"ok")
  monitor.refresh()
  self.assertEqual(len(called),6)
if __name__=="__main__":unittest.main()
