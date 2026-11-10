import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo
import requests
from sqlalchemy import select
from . import config,tickers as tk
from .models import pricequote,ticker

log=logging.getLogger(__name__)
sessions={"IN":("Asia/Kolkata",(9,15),(15,30)),"US":("America/New_York",(9,30),(16,0))}
state={"fail":0,"skip_until":0.0}

def market_open(market,now=None):
    if market=="ANY":
        return market_open("IN",now) or market_open("US",now)
    tzname,start,end=sessions[market]
    local=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo(tzname))
    if local.weekday()>=5:
        return False
    return start<=(local.hour,local.minute)<end

def fetch_quote(symbol):
    ysym=tk.yahoo_symbol(symbol)
    if not ysym:
        return None
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ysym,safe='')}"
    try:
        res=requests.get(url,params={"range":"1d","interval":"1d"},headers={"User-Agent":config.user_agent},timeout=config.quote_timeout)
        res.raise_for_status()
        meta=res.json()["chart"]["result"][0]["meta"]
        price=float(meta["regularMarketPrice"])
        prev=float(meta.get("chartPreviousClose") or meta.get("previousClose"))
    except (requests.RequestException,KeyError,IndexError,TypeError,ValueError):
        return None
    if prev==0:
        return None
    return {"symbol":symbol,"price":price,"prev_close":prev,"change_pct":round((price-prev)/prev*100,2),"currency":meta.get("currency")}

def tracked_symbols(db):
    mentioned=set(db.execute(select(ticker.symbol).distinct()).scalars().all())
    stocks={s for s in tk.by_symbol if tk.is_stock(s)}
    wanted=stocks|tk.index_symbols|mentioned|tk.any_symbols
    return sorted(s for s in wanted if tk.yahoo_symbol(s))

def aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def due(symbol,row,now):
    if row is None:
        return True
    if market_open(tk.market_of(symbol),now):
        return True
    return now-aware(row.updated_at)>timedelta(minutes=config.closed_refresh_minutes)

def refresh_quotes(db,now=None):
    now=now or datetime.now(timezone.utc)
    if time.time()<state["skip_until"]:
        return 0
    existing={r.symbol:r for r in db.execute(select(pricequote)).scalars().all()}
    symbols=[s for s in tracked_symbols(db) if due(s,existing.get(s),now)][:config.max_quotes]
    if not symbols:
        return 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=[r for r in pool.map(fetch_quote,symbols) if r]
    if results:
        state["fail"]=0
    else:
        state["fail"]+=1
        state["skip_until"]=time.time()+min(300,30*2**state["fail"])
        log.warning("no quotes fetched, backing off for %ss",int(state["skip_until"]-time.time()))
    for r in results:
        row=existing.get(r["symbol"])
        if row is None:
            row=pricequote(symbol=r["symbol"])
            db.add(row)
        row.market=tk.market_of(r["symbol"])
        row.price=r["price"]
        row.prev_close=r["prev_close"]
        row.change_pct=r["change_pct"]
        row.currency=r["currency"]
        row.updated_at=now
    db.commit()
    log.info("refreshed %s of %s quotes",len(results),len(symbols))
    return len(results)
