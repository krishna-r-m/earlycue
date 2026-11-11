import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime,timedelta,timezone
from fastapi import FastAPI,Depends,Query,HTTPException,BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select,func,exists
from sqlalchemy.orm import Session,selectinload
from . import config,instruments,pipeline,quotes,schemas as sc,tickers as tk
from .auth import router as auth_router,current_user,require_admin,ensure_admin
from .db import init_db,get_db,sessionlocal
from .models import article,sentiment,ticker,pricequote,feedstat,user

labels=("Bullish","Bearish","Neutral")
markets=("IN","US")
log=logging.getLogger("uvicorn.error")
run_lock=threading.Lock()
auth=[Depends(current_user)]
admin=[Depends(require_admin)]

def first_sync():
    db=sessionlocal()
    try:
        instruments.sync(db)
    except Exception:
        log.exception("first stock list sync failed")
    finally:
        db.close()

def quote_loop(stop):
    while True:
        db=sessionlocal()
        try:
            if time.time()-instruments.state["loaded"]>1800:
                instruments.load(db)
            quotes.refresh_quotes(db)
            quotes.refresh_bulk(db)
        except Exception:
            db.rollback()
            log.exception("live quote refresh failed")
        finally:
            db.close()
        if stop.wait(config.quote_interval_seconds):
            return

@asynccontextmanager
async def lifespan(app):
    init_db()
    db=sessionlocal()
    try:
        ensure_admin(db)
        listed=instruments.load(db)
        if listed==0 and config.sync_instruments:
            threading.Thread(target=first_sync,daemon=True).start()
        removed=pipeline.purge_cross_market(db)
        if removed:
            log.info("removed %s cross-market ticker tags",removed)
    finally:
        db.close()
    if config.secret_key==config.default_secret:
        log.warning("SECRET_KEY is the development default, set your own before deploying")
    stop=threading.Event()
    if config.quote_interval_seconds>0:
        threading.Thread(target=quote_loop,args=(stop,),daemon=True).start()
    yield
    stop.set()

api=FastAPI(title="earlycue API",version="2.0.0",lifespan=lifespan)
api.add_middleware(CORSMiddleware,allow_origins=config.cors_origins,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
api.include_router(auth_router)

def aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

def since(hours):
    return datetime.now(timezone.utc)-timedelta(hours=hours)

def check_market(market):
    m=market.upper()
    if m not in markets:
        raise HTTPException(422,"market must be IN or US")
    return m

def signed(label,conf):
    if label=="Bullish":
        return conf
    if label=="Bearish":
        return -conf
    return 0.0

def leaning(score,n):
    if n==0:
        return "Neutral"
    if score>=0.12:
        return "Bullish"
    if score<=-0.12:
        return "Bearish"
    return "Neutral"

def summarise(pairs):
    counts={k:0 for k in labels}
    total=0.0
    for label,conf in pairs:
        counts[label]+=1
        total+=signed(label,conf)
    n=len(pairs)
    score=round(total/n,3) if n else 0.0
    return {"total":n,"bullish":counts["Bullish"],"bearish":counts["Bearish"],"neutral":counts["Neutral"],"score":score,"leaning":leaning(score,n)}

def build_trend(rows,daily):
    buckets={}
    for ts,label,conf in rows:
        ts=aware(ts)
        key=ts.replace(hour=0,minute=0,second=0,microsecond=0) if daily else ts.replace(minute=0,second=0,microsecond=0)
        buckets.setdefault(key,[]).append(signed(label,conf))
    return [{"t":k,"score":round(sum(v)/len(v),3),"count":len(v)} for k,v in sorted(buckets.items())]

def art_out(a,market=None):
    s=a.sentiment
    return {
        "id":a.id,
        "title":a.title,
        "source":a.source,
        "url":a.url,
        "published_at":aware(a.published_at),
        "summary":a.summary,
        "sentiment":s.sentiment_label if s else None,
        "confidence":s.confidence_score if s else None,
        "sector":s.sector if s else None,
        "tickers":[{"symbol":t.symbol,"name":t.company_name} for t in a.tickers if tk.in_market(t.symbol,market)],
    }

@api.get("/api/health",response_model=sc.health)
def health(db:Session=Depends(get_db)):
    return {
        "status":"ok",
        "articles":db.scalar(select(func.count(article.id))),
        "scored":db.scalar(select(func.count(sentiment.id))),
        "stocks":instruments.count(db),
        "latest":aware(db.scalar(select(func.max(article.published_at)))),
        "scored_at":aware(db.scalar(select(func.max(sentiment.created_at)))),
        "quotes_at":aware(db.scalar(select(func.max(pricequote.updated_at)))),
    }

@api.get("/api/articles",response_model=sc.articlelist,dependencies=auth)
def list_articles(
    market:str|None=None,
    label:str|None=Query(None,alias="sentiment"),
    sector:str|None=None,
    source:str|None=None,
    symbol:str|None=Query(None,alias="ticker"),
    q:str|None=None,
    hours:int|None=Query(None,ge=1,le=720),
    limit:int=Query(30,ge=1,le=100),
    offset:int=Query(0,ge=0),
    db:Session=Depends(get_db),
):
    stmt=select(article).join(sentiment,sentiment.article_id==article.id)
    if market:
        stmt=stmt.where(article.market==check_market(market))
    if label:
        label=label.capitalize()
        if label not in labels:
            raise HTTPException(422,"sentiment must be bullish, bearish or neutral")
        stmt=stmt.where(sentiment.sentiment_label==label)
    if sector:
        stmt=stmt.where(sentiment.sector==sector)
    if source:
        stmt=stmt.where(article.source==source)
    if symbol:
        stmt=stmt.where(exists().where(ticker.article_id==article.id,ticker.symbol==symbol.upper()))
    if q:
        stmt=stmt.where(article.title.ilike(f"%{q}%"))
    if hours:
        stmt=stmt.where(article.published_at>=since(hours))
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows=db.execute(
        stmt.options(selectinload(article.sentiment),selectinload(article.tickers))
        .order_by(article.published_at.desc())
        .limit(limit)
        .offset(offset)
    ).scalars().all()
    return {"total":total,"items":[art_out(a,market.upper() if market else None) for a in rows]}

@api.get("/api/market-pulse",response_model=sc.marketpulse,dependencies=auth)
def market_pulse(market:str="IN",hours:int=Query(24,ge=1,le=720),sector:str|None=None,db:Session=Depends(get_db)):
    market=check_market(market)
    if sector and sector not in tk.sector_names and sector!="General":
        raise HTTPException(422,"unknown sector")
    start=since(hours)
    rows=db.execute(
        select(article.published_at,sentiment.sentiment_label,sentiment.confidence_score,sentiment.sector)
        .join(sentiment,sentiment.article_id==article.id)
        .where(article.published_at>=start,article.market==market)
    ).all()
    overall=summarise([(r[1],r[2]) for r in rows])
    by_sector={s:[] for s in tk.sector_names}
    for r in rows:
        by_sector.setdefault(r[3] or "General",[]).append((r[1],r[2]))
    sectors=[{"sector":k,**summarise(v)} for k,v in by_sector.items()]
    sectors.sort(key=lambda s:(-s["total"],s["sector"]))
    daily=hours>72
    pick=[r for r in rows if r[3]==sector] if sector else rows
    trend=build_trend([(r[0],r[1],r[2]) for r in pick],daily)
    sector_stats=summarise([(r[1],r[2]) for r in pick]) if sector else None
    trows=db.execute(
        select(ticker.symbol,ticker.company_name,sentiment.sentiment_label,sentiment.confidence_score)
        .join(article,article.id==ticker.article_id)
        .join(sentiment,sentiment.article_id==article.id)
        .where(article.published_at>=start,article.market==market)
    ).all()
    by_ticker={}
    names={}
    for sym,name,label,conf in trows:
        if not tk.in_market(sym,market):
            continue
        if sector and tk.by_symbol.get(sym,{}).get("sector")!=sector:
            continue
        by_ticker.setdefault(sym,[]).append((label,conf))
        names[sym]=name
    top=[{"symbol":k,"name":names[k],**summarise(v)} for k,v in by_ticker.items()]
    top.sort(key=lambda t:(-t["total"],t["symbol"]))
    return {
        "hours":hours,
        "generated_at":datetime.now(timezone.utc),
        "granularity":"day" if daily else "hour",
        "overall":overall,
        "sectors":sectors,
        "trend":trend,
        "top_tickers":top[:8],
        "sector":sector,
        "sector_stats":sector_stats,
    }

@api.get("/api/movers",response_model=sc.movers,dependencies=auth)
def get_movers(market:str="IN",by:str="price",hours:int=Query(24,ge=1,le=720),limit:int=Query(10,ge=1,le=100),offset:int=Query(0,ge=0),sector:str|None=None,db:Session=Depends(get_db)):
    market=check_market(market)
    if by not in ("price","sentiment"):
        raise HTTPException(422,"by must be price or sentiment")
    start=since(hours)
    prev_start=since(hours*2)
    trows=db.execute(
        select(ticker.symbol,article.published_at,sentiment.sentiment_label,sentiment.confidence_score)
        .join(article,article.id==ticker.article_id)
        .join(sentiment,sentiment.article_id==article.id)
        .where(article.published_at>=prev_start,article.market==market)
    ).all()
    now_pairs={}
    prev_pairs={}
    for sym,ts,label,conf in trows:
        bucket=now_pairs if aware(ts)>=start else prev_pairs
        bucket.setdefault(sym,[]).append((label,conf))
    qrows=db.execute(select(pricequote).where(pricequote.updated_at>=since(24*8))).scalars().all()
    quotemap={q.symbol:q for q in qrows if tk.market_of(q.symbol) in (market,"ANY")}
    universe=[sym for sym,info in tk.by_symbol.items() if tk.is_stock(sym) and tk.market_of(sym)==market and (not sector or info["sector"]==sector)]
    def rank(sym):
        return (tk.by_symbol[sym].get("rank",100000),sym)
    def shift(sym):
        cur=summarise(now_pairs.get(sym,[]))
        prev=summarise(prev_pairs.get(sym,[]))
        return cur,round(cur["score"]-prev["score"],3)
    if by=="price":
        ranked=sorted((s for s in universe if s in quotemap),key=lambda s:(-abs(quotemap[s].change_pct),)+rank(s))
        ranked+=sorted((s for s in universe if s not in quotemap),key=rank)
    else:
        scored=[(s,)+shift(s) for s in universe if s in now_pairs]
        ranked=[x[0] for x in sorted(scored,key=lambda x:(-abs(x[2]),-x[1]["total"])+rank(x[0]))]
        ranked+=sorted((s for s in universe if s not in now_pairs),key=rank)
    items=[]
    for sym in ranked[offset:offset+limit]:
        cur,sh=shift(sym)
        info=tk.by_symbol[sym]
        q=quotemap.get(sym)
        items.append({
            "symbol":sym,
            "name":info["name"],
            "sector":info["sector"],
            "price":q.price if q else None,
            "change_pct":q.change_pct if q else None,
            "currency":q.currency if q else None,
            "total":cur["total"],
            "score":cur["score"],
            "leaning":cur["leaning"],
            "shift":sh,
        })
    indices=[]
    for sym in sorted(tk.index_symbols):
        q=quotemap.get(sym)
        if q and tk.market_of(sym)==market:
            indices.append({"symbol":sym,"name":tk.by_symbol[sym]["name"],"price":q.price,"change_pct":q.change_pct,"currency":q.currency})
    stamps=[aware(q.updated_at) for q in quotemap.values()]
    return {
        "market":market,
        "by":by,
        "hours":hours,
        "price_available":bool(quotemap),
        "total":len(universe),
        "market_open":quotes.market_open(market),
        "sector":sector,
        "updated_at":max(stamps) if stamps else None,
        "items":items,
        "indices":indices,
    }

@api.get("/api/ticker/{symbol}",response_model=sc.tickerdetail,dependencies=auth)
def ticker_detail(symbol:str,days:int=Query(30,ge=1,le=365),db:Session=Depends(get_db)):
    sym=symbol.upper()
    arts=db.execute(
        select(article)
        .join(ticker,ticker.article_id==article.id)
        .join(sentiment,sentiment.article_id==article.id)
        .where(ticker.symbol==sym,article.published_at>=since(days*24))
        .options(selectinload(article.sentiment),selectinload(article.tickers))
        .order_by(article.published_at.desc())
    ).scalars().all()
    info=tk.by_symbol.get(sym)
    if info is None and not arts:
        raise HTTPException(404,f"no articles found for {sym}")
    stats=summarise([(a.sentiment.sentiment_label,a.sentiment.confidence_score) for a in arts])
    trend=build_trend([(a.published_at,a.sentiment.sentiment_label,a.sentiment.confidence_score) for a in arts],True)
    q=db.get(pricequote,sym)
    stale=q is None or datetime.now(timezone.utc)-aware(q.updated_at)>timedelta(minutes=2)
    if stale and tk.yahoo_symbol(sym) and (info is not None):
        fresh=quotes.fetch_quote(sym)
        if fresh:
            if q is None:
                q=pricequote(symbol=sym)
                db.add(q)
            q.market=tk.market_of(sym)
            q.price=fresh["price"]
            q.prev_close=fresh["prev_close"]
            q.change_pct=fresh["change_pct"]
            q.currency=fresh["currency"]
            q.updated_at=datetime.now(timezone.utc)
            db.commit()
    return {
        "symbol":sym,
        "name":info["name"] if info else None,
        "sector":info["sector"] if info else None,
        "days":days,
        "quote":{"price":q.price,"change_pct":q.change_pct,"currency":q.currency} if q else None,
        "stats":stats,
        "trend":trend,
        "articles":[art_out(a) for a in arts[:50]],
    }

@api.get("/api/tickers/search",response_model=list[sc.tickersuggestion],dependencies=auth)
def search_tickers(q:str=Query(...,min_length=1),market:str|None=None,limit:int=Query(8,ge=1,le=20),db:Session=Depends(get_db)):
    m=check_market(market) if market else None
    found=tk.search(q,limit,m)
    if len(found)<3 and len(q.strip())>=3 and config.remote_search:
        try:
            if instruments.add_remote(db,instruments.yahoo_search(q.strip(),m)):
                found=tk.search(q,limit,m)
        except Exception:
            log.warning("remote stock search failed for %r",q)
    return found

@api.get("/api/sources",response_model=list[sc.sourcestat],dependencies=admin)
def sources(db:Session=Depends(get_db)):
    rows={r.url:r for r in db.execute(select(feedstat)).scalars().all()}
    out=[]
    def add(source,market,url,r,group):
        note=(r.last_error or "") if r else ""
        partial=note.startswith("partial")
        out.append({
            "group":group,
            "partial":partial,
            "source":source,
            "market":market,
            "url":url,
            "ok":None if r is None or r.last_attempt_at is None else (not note or partial),
            "entries":(r.last_count or 0) if r else 0,
            "new":(r.last_new or 0) if r else 0,
            "last_ok_at":aware(r.last_ok_at) if r else None,
            "error":note or None,
        })
    for f in config.feeds:
        add(f["source"],f["market"],f["url"],rows.get(f["url"]),False)
    for url,r in sorted(rows.items()):
        if url.startswith("crawl:") and url!="crawl:cursor":
            add(r.source,r.market,url,r,True)
    return out

@api.get("/api/admin/overview",response_model=sc.adminoverview,dependencies=admin)
def admin_overview(db:Session=Depends(get_db)):
    scored=db.scalar(select(func.count(sentiment.id)))
    total=db.scalar(select(func.count(article.id)))
    return {
        "articles":total,
        "scored":scored,
        "pending":total-scored,
        "added_24h":db.scalar(select(func.count(article.id)).where(article.created_at>=since(24))),
        "in_articles":db.scalar(select(func.count(article.id)).where(article.market=="IN")),
        "us_articles":db.scalar(select(func.count(article.id)).where(article.market=="US")),
        "users":db.scalar(select(func.count(user.id))),
        "quotes":db.scalar(select(func.count(pricequote.symbol))),
        "instruments":instruments.count(db),
        "quote_backoff_seconds":max(0,int(quotes.state["skip_until"]-time.time())),
        "db_engine":db.bind.dialect.name,
    }

@api.post("/api/admin/cleanup",response_model=sc.cleanupresult,dependencies=admin)
def admin_cleanup(db:Session=Depends(get_db)):
    removed=pipeline.purge_old(db,config.retention_days,config.unrelated_days)
    return {"removed":removed,"articles":db.scalar(select(func.count(article.id)))}

@api.get("/api/admin/users",response_model=list[sc.adminuser],dependencies=admin)
def admin_users(db:Session=Depends(get_db)):
    rows=db.execute(select(user).order_by(user.id)).scalars().all()
    return [{"id":u.id,"email":u.email,"name":u.name,"role":u.role,"google":bool(u.google_sub),"created_at":aware(u.created_at)} for u in rows]

def queue_status():
    from .celery_app import celery
    try:
        with celery.connection_for_write() as conn:
            conn.ensure_connection(max_retries=1,interval_start=0,interval_step=0.2,interval_max=0.5,timeout=2)
    except Exception as exc:
        log.warning("broker unreachable: %s",exc)
        return {"state":"down","detail":"The task queue (Redis) is not reachable. Fetches will run inside the API instead."}
    try:
        pong=celery.control.inspect(timeout=1.0).ping()
    except Exception:
        pong=None
    if pong:
        return {"state":"ok","detail":"Worker online."}
    return {"state":"no_worker","detail":"Queue is up but the worker did not answer. It may be offline or busy with a fetch."}

def run_inline():
    if not run_lock.acquire(blocking=False):
        return
    try:
        from .tasks import refresh_news
        refresh_news()
    except Exception:
        log.exception("inline refresh failed")
    finally:
        run_lock.release()

@api.get("/api/status",response_model=sc.queuestatus,dependencies=admin)
def status():
    return queue_status()

refresh_state={"at":0.0}

def send_tasks(names):
    from .celery_app import celery
    with celery.connection_for_write() as conn:
        conn.ensure_connection(max_retries=1,interval_start=0,interval_step=0.2,interval_max=0.5,timeout=2)
    return [celery.send_task(n) for n in names]

@api.post("/api/admin/refresh",response_model=sc.refreshresult,dependencies=admin)
def refresh(background:BackgroundTasks):
    names=["app.tasks.refresh_news"]
    if config.deep_crawl:
        names.append("app.tasks.deep_crawl")
    names.append("app.tasks.sync_instruments")
    try:
        jobs=send_tasks(names)
        return {"queued":True,"mode":"worker","task_id":jobs[0].id,"detail":"Fetch, deep crawl and stock list sync queued. New articles show up as the worker finishes scoring them."}
    except Exception:
        log.exception("could not queue refresh, running inline")
    background.add_task(run_inline)
    return {"queued":True,"mode":"inline","task_id":None,"detail":"The task queue is not reachable, so the fetch is running inside the API. This can take a minute."}

@api.post("/api/refresh",response_model=sc.refreshresult,dependencies=auth)
def user_refresh(background:BackgroundTasks):
    if time.time()-refresh_state["at"]<config.user_refresh_cooldown:
        return {"queued":False,"mode":"busy","task_id":None,"detail":"We refreshed a moment ago. Please wait a little before trying again."}
    refresh_state["at"]=time.time()
    try:
        send_tasks(["app.tasks.refresh_news"])
    except Exception:
        log.exception("could not queue user refresh, running inline")
        background.add_task(run_inline)
    return {"queued":True,"mode":"accepted","task_id":None,"detail":"Refreshing now. New stories and prices will appear in a minute or two."}
