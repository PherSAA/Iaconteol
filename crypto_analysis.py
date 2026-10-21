"""Análisis descriptivo de velas históricas de criptomonedas. Sin trading."""
import math, statistics

ALLOWED_PRODUCTS = ("BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD")
GRANULARITIES = ("ONE_HOUR", "SIX_HOUR", "ONE_DAY")

def parse_candles(payload):
    raw=payload.get("candles", [])
    if not isinstance(raw,list) or not 2<=len(raw)<=300:raise ValueError("Se requieren entre 2 y 300 velas")
    candles=[]
    for item in raw:
        x={k:float(item[k]) for k in ("open","high","low","close","volume")}
        x["start"]=int(item["start"])
        if any(not math.isfinite(v) for v in x.values()):raise ValueError("Valores no finitos")
        if min(x["open"],x["low"],x["close"],x["high"])<=0 or x["volume"]<0:raise ValueError("Precios o volumen inválidos")
        if x["high"]<max(x["open"],x["close"],x["low"]) or x["low"]>min(x["open"],x["close"],x["high"]):raise ValueError("OHLC inconsistente")
        candles.append(x)
    candles.sort(key=lambda x:x["start"])
    if len({x["start"] for x in candles})!=len(candles):raise ValueError("Tiempos duplicados")
    return candles

def analyze(p):
    candles=parse_candles(p)
    closes=[x["close"] for x in candles]
    changes=[math.log(closes[i]/closes[i-1]) for i in range(1,len(closes))]
    peak=closes[0];max_dd=0
    for v in closes:
        peak=max(peak,v)
        max_dd=max(max_dd,(peak-v)/peak)
    n=min(20,len(closes))
    mean=sum(closes[-n:])/n
    stdev=statistics.stdev(changes) if len(changes)>1 else 0.0
    return {
        "product":str(p.get("product","unknown"))[:20],
        "samples":len(closes),
        "first_timestamp":candles[0]["start"],"last_timestamp":candles[-1]["start"],
        "last_close_usd":round(closes[-1],8),
        "change_pct":round((closes[-1]/closes[0]-1)*100,4),
        "sma_20_or_available":round(mean,8),
        "volatility_log_return_std_pct":round(stdev*100,4),
        "max_close_drawdown_pct":round(max_dd*100,4),
        "volume_total":round(sum(x["volume"] for x in candles),4),
        "last_close_above_sma":closes[-1]>mean,
        "note":"Análisis descriptivo histórico, no predicción, recomendación ni garantía de rendimiento."
    }
