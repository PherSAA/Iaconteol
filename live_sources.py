"""Consultas públicas para panel vivo. Datos con fecha, procedencia y errores explícitos."""
import datetime as dt
import json, math, threading, time, urllib.parse, urllib.request

URL_USGS="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
URL_NASA="https://ssd-api.jpl.nasa.gov/cad.api?date-min=now&date-max=%2B30&dist-max=10LD"
URL_COINBASE="https://api.exchange.coinbase.com/products/{product}/candles?granularity=3600"
URL_BLUESKY="https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
MARKETS=("BTC-USD","ETH-USD","SOL-USD","XRP-USD")
def iso(unix=None):
    return dt.datetime.fromtimestamp(time.time() if unix is None else unix,dt.timezone.utc).isoformat(timespec="seconds")
def get_json(url,timeout=9,cap=1400000):
    request=urllib.request.Request(url,headers={"User-Agent":"SplitRunGenesis/1.2 (+educational research)","Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        raw=response.read(cap+1)
    if len(raw)>cap:raise ValueError("La respuesta supera el límite permitido")
    return json.loads(raw)
def earthquakes(obj):
    features=obj.get("features",[])
    if not isinstance(features,list):raise ValueError("Respuesta USGS inválida")
    rows=[]
    for x in features[:500]:
        p=x.get("properties") or {}
        coords=(x.get("geometry") or {}).get("coordinates") or []
        if p.get("mag") is None or len(coords)<3:continue
        rows.append({"id":str(x.get("id","")),"place":str(p.get("place") or "Sin ubicación")[:110],
           "magnitude":round(float(p["mag"]),2),"depth_km":round(float(coords[2]),2),
           "time":iso(float(p["time"])/1000) if p.get("time") else None,
           "url":str(p.get("url") or "")[:240]})
    rows.sort(key=lambda x:x["time"] or "",reverse=True)
    return {"count":len(rows),"largest_magnitude":max((r["magnitude"] for r in rows),default=None),
      "recent":rows[:15],"note":"Eventos observados; no predicción de terremotos."}
def asteroids(obj):
    from engine import AU_KM,LD_KM
    fields=obj.get("fields") or []
    idx={v:i for i,v in enumerate(fields)}
    if "dist" not in idx or not (("des" in idx) or ("desig" in idx)):raise ValueError("Respuesta NASA inválida")
    name=idx.get("des",idx.get("desig"))
    when=idx.get("cd")
    rows=[]
    for x in obj.get("data",[])[:350]:
        try:
            km=float(x[idx["dist"]])*AU_KM
            rows.append({"designation":str(x[name]),"date":str(x[when]) if when is not None else "N/D",
              "distance_km":round(km),"lunar_distances":round(km/LD_KM,3)})
        except (ValueError,IndexError,TypeError):continue
    rows.sort(key=lambda x:x["distance_km"])
    return {"count":len(rows),"closest":rows[:12],"note":"Acercamiento estimado; no implica impacto."}
def cryptos(fetcher=get_json):
    data={}
    for product in MARKETS:
        try:
            url=URL_COINBASE.format(product=urllib.parse.quote(product))
            obj=fetcher(url)
            if not isinstance(obj,list) or len(obj)<3:raise ValueError("Sin velas suficientes")
            # Coinbase Exchange: [time, low, high, open, close, volume]
            arr=sorted(obj,key=lambda x:float(x[0]))
            closes=[float(row[4]) for row in arr if len(row)>=6]
            if not closes or any(not math.isfinite(v) or v<=0 for v in closes):raise ValueError("Cierres inválidos")
            last=closes[-1];prev=closes[-2];base=closes[max(0,len(closes)-25)]
            recent=closes[-20:]
            data[product]={"last_close":round(last,8),"last_candle":iso(float(arr[-1][0])),
              "change_last_candle_pct":round((last/prev-1)*100,3),
              "change_24_candles_pct":round((last/base-1)*100,3),
              "sma20":round(sum(recent)/len(recent),8),"sample_count":len(closes),
              "note":"Precio histórico por vela, no cotización tick a tick ni señal de compra."}
        except Exception as ex:data[product]={"error":str(ex)[:200]}
    return data
def social_posts(query,fetcher=get_json):
    q=str(query).strip()
    if not 2<=len(q)<=70:raise ValueError("Tema entre 2 y 70 caracteres")
    url=URL_BLUESKY+"?"+urllib.parse.urlencode({"q":q,"limit":20,"sort":"latest"})
    obj=fetcher(url)
    out=[]
    for p in obj.get("posts",[])[:20]:
        record=p.get("record") or {}
        author=p.get("author") or {}
        handle=author.get("handle","")
        uri=p.get("uri","")
        post_id=uri.rsplit("/",1)[-1] if isinstance(uri,str) else ""
        out.append({"text":str(record.get("text",""))[:450],
          "author":str(handle)[:100],"published":str(record.get("createdAt","")),
          "url":("https://bsky.app/profile/"+urllib.parse.quote(handle)+"/post/"+urllib.parse.quote(post_id))
                    if handle and post_id else None})
    return {"query":q,"posts":out,"count":len(out),"source":URL_BLUESKY,
      "note":"Opiniones públicas sin verificar; no representan hechos confirmados ni todo el mercado."}

class LiveMonitor:
    def __init__(self,fetcher=get_json):
        self.fetcher=fetcher
        self.lock=threading.Lock()
        self.snapshot={"updated_at":None,"sources":{}}
        self.updated={}
        self.intervals={"usgs":75,"nasa":3600,"crypto":120}
    def refresh(self,force=False):
        now=time.monotonic()
        with self.lock:
            pending=[k for k in self.intervals if force or now-self.updated.get(k,-1e10)>=self.intervals[k]]
        for key in pending:
            try:
                if key=="usgs": 
                    source=URL_USGS;value=earthquakes(self.fetcher(source))
                elif key=="nasa":
                    source=URL_NASA;value=asteroids(self.fetcher(source))
                else:
                    source="https://api.exchange.coinbase.com"
                    value=cryptos(self.fetcher)
                    if all("error" in x for x in value.values()):raise ValueError("No se pudieron obtener datos de Coinbase")
                row={"status":"ok","source":source,"retrieved_at":iso(),"data":value}
            except Exception as ex:
                with self.lock:previous=self.snapshot["sources"].get(key,{})
                row={"status":"error","source":previous.get("source",{"usgs":URL_USGS,"nasa":URL_NASA,"crypto":"https://api.exchange.coinbase.com"}[key]),
                    "retrieved_at":iso(),"error":str(ex)[:240],
                    "stale_data":previous.get("data") or previous.get("stale_data"),
                    "last_success":previous.get("retrieved_at") if previous.get("status")=="ok" else previous.get("last_success")}
            with self.lock:
                self.snapshot["sources"][key]=row
                self.snapshot["updated_at"]=iso()
                self.updated[key]=time.monotonic()
        with self.lock:return json.loads(json.dumps(self.snapshot))
    def current(self):
        with self.lock:return json.loads(json.dumps(self.snapshot))
