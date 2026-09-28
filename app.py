import os, math, statistics
from datetime import datetime, timedelta
from typing import Optional
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()
API_KEY=os.getenv("FMP_API_KEY","").strip()
BASE="https://financialmodelingprep.com/stable"
app=FastAPI(title="US Stock Momentum Scanner")
app.mount("/static",StaticFiles(directory="static"),name="static")

def get(path, params=None):
    if not API_KEY:
        raise HTTPException(400,"Configurează FMP_API_KEY în variabilele de mediu ale serverului.")
    p=dict(params or {}); p["apikey"]=API_KEY
    r=requests.get(f"{BASE}/{path}",params=p,timeout=25)
    if r.status_code>=400: raise HTTPException(502,f"FMP a returnat HTTP {r.status_code}. Verifică cheia și planul API.")
    return r.json()

def sma(vals,n):
    return sum(vals[-n:])/n if len(vals)>=n else None
def rsi(vals,n=14):
    if len(vals)<n+1:return None
    changes=[vals[i]-vals[i-1] for i in range(len(vals)-n,len(vals))]
    gains=sum(max(x,0) for x in changes)/n; losses=sum(max(-x,0) for x in changes)/n
    return 100 if losses==0 else 100-100/(1+gains/losses)
def atr(rows,n=14):
    if len(rows)<n+1:return None
    trs=[]
    for i in range(1,len(rows)):
        h,l,c=rows[i]["high"],rows[i]["low"],rows[i-1]["close"]
        trs.append(max(h-l,abs(h-c),abs(l-c)))
    return sum(trs[-n:])/n
@app.get("/",response_class=HTMLResponse)
def home():
    return open("static/index.html",encoding="utf-8").read()
@app.get("/api/health")
def health(): return {"ok":True,"api_key_configured":bool(API_KEY)}
@app.get("/api/scan")
def scan(limit:int=100, min_price:float=5, min_volume:int=300000):
    # FMP screener universe is limited by the selected provider plan.
    symbols=get("company-screener",{"marketCapMoreThan":300_000_000,"priceMoreThan":min_price,
        "volumeMoreThan":min_volume,"isActivelyTrading":"true","limit":min(500,max(1,limit))})
    if not isinstance(symbols,list): raise HTTPException(502,"Răspuns neașteptat de la FMP.")
    results=[]
    for item in symbols:
        sym=item.get("symbol")
        if not sym: continue
        try:
            hist=get("historical-price-eod/full",{"symbol":sym,"from":(datetime.utcnow()-timedelta(days=120)).date().isoformat(),
                                                   "to":datetime.utcnow().date().isoformat()})
            if not isinstance(hist,list) or len(hist)<30: continue
            hist=sorted(hist,key=lambda x:x.get("date",""))
            closes=[float(x["close"]) for x in hist if x.get("close") is not None]
            if len(closes)<30: continue
            last=closes[-1]; s20=sma(closes,20); s50=sma(closes,50); rv=rsi(closes)
            a=atr(hist)
            if not s20 or not s50 or a is None: continue
            # Strictly require core market and financial data; omit incomplete rows.
            profile=get("profile",{"symbol":sym})
            income=get("income-statement",{"symbol":sym,"limit":1})
            prof=profile[0] if isinstance(profile,list) and profile else {}
            fin=income[0] if isinstance(income,list) and income else {}
            required=["companyName","exchangeShortName"]
            if any(not prof.get(k) for k in required): continue
            if fin.get("revenue") is None or fin.get("netIncome") is None: continue
            news=get("news/stock",{"symbols":sym,"limit":5})
            news=news if isinstance(news,list) else []
            change=(last/closes[-6]-1)*100 if len(closes)>=6 and closes[-6] else 0
            score=0
            score+=25 if last>s20 else 0
            score+=20 if s20>s50 else 0
            score+=20 if 50<=rv<=70 else 0
            score+=20 if change>0 else 0
            score+=15 if fin.get("netIncome",0)>0 else 0
            results.append({"symbol":sym,"name":prof.get("companyName"),"exchange":prof.get("exchangeShortName"),
                "price":round(last,2),"change5d":round(change,2),"rsi":round(rv,1),"atrPct":round(a/last*100,2),
                "score":score,"revenue":fin.get("revenue"),"netIncome":fin.get("netIncome"),
                "news":[{"title":n.get("title"),"url":n.get("url"),"date":n.get("publishedDate")} for n in news[:3]]})
        except Exception:
            # In strict mode, any symbol with missing/failed data is excluded.
            continue
    results.sort(key=lambda x:x["score"],reverse=True)
    return {"count":len(results),"results":results,"note":"MVP: limite de simboli, date daily; verifică acoperirea și termenii planului FMP."}
