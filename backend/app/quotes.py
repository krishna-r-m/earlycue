import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from urllib.parse import quote
from zoneinfo import ZoneInfo
import requests
from sqlalchemy import select,func
from . import config,instruments,tickers as tk
from .models import pricequote,ticker,article

log=logging.getLogger(__name__)
sessions={"IN":("Asia/Kolkata",(9,15),(15,30)),"US":("America/New_York",(9,30),(16,0))}
state={"fail":0,"skip_until":0.0,"us_bulk_at":0.0}

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
    since=datetime.now(timezone.utc)-timedelta(hours=48)
    counts=db.execute(
        select(ticker.symbol,func.count(ticker.id))
        .join(article,article.id==ticker.article_id)
        .where(article.published_at>=since)
        .group_by(ticker.symbol)
        .order_by(func.count(ticker.id).desc())
    ).all()
    curated=sorted(s for s in tk.by_symbol if tk.is_stock(s) and s not in tk.imported)
    indian=sorted(s for s in tk.imported if tk.by_symbol[s]["market"]=="IN")
    ordered=sorted(tk.index_symbols)+sorted(tk.any_symbols)+[c[0] for c in counts]+curated+indian
    seen=set()
    out=[]
    for sym in ordered:
        if sym not in seen and sym in tk.by_symbol and tk.yahoo_symbol(sym):
            seen.add(sym)
            out.append(sym)
    return out

def aware(dt):
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def due(symbol,row,now):
    if row is None:
        return True
    if market_open(tk.market_of(symbol),now):
        return True
    return now-aware(row.updated_at)>timedelta(minutes=config.closed_refresh_minutes)

def upsert(db,existing,r,now):
    row=existing.get(r["symbol"])
    if row is None:
        row=pricequote(symbol=r["symbol"])
        db.add(row)
        existing[r["symbol"]]=row
    row.market=tk.market_of(r["symbol"])
    row.price=r["price"]
    row.prev_close=r["prev_close"]
    row.change_pct=r["change_pct"]
    row.currency=r["currency"]
    row.updated_at=now

def refresh_us_bulk(db,now):
    if not config.us_bulk_quotes:
        return 0
    interval=300 if market_open("US",now) else 1800
    if time.time()-state["us_bulk_at"]<interval:
        return 0
    state["us_bulk_at"]=time.time()
    try:
        rows=instruments.fetch_screener(0)
    except Exception as exc:
        log.warning("us bulk quotes failed: %s",exc)
        return 0
    existing={q.symbol:q for q in db.execute(select(pricequote).where(pricequote.market=="US")).scalars().all()}
    n=0
    for r in rows:
        sym=r["symbol"]
        price,pct=r["price"],r["pct"]
        if price is None or pct is None or pct<=-100 or tk.market_of(sym)!="US" or sym not in tk.by_symbol:
            continue
        row=existing.get(sym)
        if row is not None and row.updated_at is not None and (now-aware(row.updated_at)).total_seconds()<90:
            continue
        upsert(db,existing,{"symbol":sym,"price":price,"prev_close":price/(1+pct/100),"change_pct":round(pct,2),"currency":"USD"},now)
        n+=1
    db.commit()
    log.info("bulk US quotes updated for %s stocks",n)
    return n

def refresh_quotes(db,now=None):
    now=now or datetime.now(timezone.utc)
    bulk=0
    try:
        bulk=refresh_us_bulk(db,now)
    except Exception:
        db.rollback()
        log.exception("us bulk quotes failed")
    if time.time()<state["skip_until"]:
        return bulk
    existing={r.symbol:r for r in db.execute(select(pricequote)).scalars().all()}
    symbols=tracked_symbols(db)
    top=symbols[:config.quote_top]
    rest=[s for s in symbols[config.quote_top:] if due(s,existing.get(s),now)]
    rest.sort(key=lambda s:aware(existing[s].updated_at).timestamp() if s in existing and existing[s].updated_at else 0)
    batch=[s for s in top if due(s,existing.get(s),now)]+rest[:config.quote_rolling]
    if not batch:
        return bulk
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=[r for r in pool.map(fetch_quote,batch) if r]
    if results:
        state["fail"]=0
    else:
        state["fail"]+=1
        state["skip_until"]=time.time()+min(300,30*2**state["fail"])
        log.warning("no quotes fetched, backing off for %ss",int(state["skip_until"]-time.time()))
    for r in results:
        upsert(db,existing,r,now)
    db.commit()
    log.info("refreshed %s of %s quotes",len(results),len(batch))
    return bulk+len(results)

bulk={"us":0.0,"in":0.0}

def bulk_upsert(db,rows):
    existing={r.symbol:r for r in db.execute(select(pricequote)).scalars().all()}
    changed=0
    for symbol,price,prev,pct,currency,stamp in rows:
        if symbol not in tk.by_symbol:
            continue
        row=existing.get(symbol)
        if row is None:
            row=pricequote(symbol=symbol)
            db.add(row)
        elif aware(row.updated_at)>=stamp:
            continue
        row.market=tk.market_of(symbol)
        row.price=price
        row.prev_close=prev
        row.change_pct=pct
        row.currency=currency
        row.updated_at=stamp
        changed+=1
    db.commit()
    return changed

def refresh_bulk(db,now=None):
    now=now or datetime.now(timezone.utc)
    done=0
    us_every=300 if market_open("US",now) else 3*3600
    if time.time()-bulk["us"]>us_every:
        bulk["us"]=time.time()
        try:
            done+=bulk_upsert(db,instruments.us_price_rows(now))
        except Exception as exc:
            db.rollback()
            log.warning("US bulk prices failed: %s",exc)
    if time.time()-bulk["in"]>3*3600:
        bulk["in"]=time.time()
        try:
            done+=bulk_upsert(db,instruments.in_price_rows())
        except Exception as exc:
            db.rollback()
            log.warning("India bulk prices failed: %s",exc)
    if done:
        log.info("bulk prices updated for %s stocks",done)
    return done
