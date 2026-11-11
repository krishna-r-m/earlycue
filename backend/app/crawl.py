import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import quote_plus
import requests
from sqlalchemy import select
from . import config,ingest,tickers as tk,trusted
from .models import feedstat

log=logging.getLogger(__name__)

terms={
    "IN":'(sensex OR nifty OR "indian stocks" OR NSE OR BSE)',
    "US":'("wall street" OR nasdaq OR "s&p 500" OR "dow jones" OR stocks)',
}
locale={"IN":("en-IN","IN","IN:en"),"US":("en-US","US","US:en")}
group_names={
    "google-sites":"Google News by publisher",
    "google-sectors":"Google News by sector",
    "google-companies":"Google News by company",
    "yahoo-tickers":"Yahoo Finance by ticker",
    "gdelt":"GDELT global news",
}
gdelt_queries={
    "IN":[
        "(sensex OR nifty OR \"stock market\" OR shares) sourcecountry:IN sourcelang:english",
        "theme:ECON_STOCKMARKET sourcecountry:IN sourcelang:english",
        "(earnings OR results OR IPO) (india OR indian) sourcelang:english",
    ],
    "US":[
        "(stocks OR \"wall street\" OR nasdaq OR \"s&p 500\") sourcecountry:US sourcelang:english",
        "theme:ECON_STOCKMARKET sourcecountry:US sourcelang:english",
        "(earnings OR \"federal reserve\") sourcecountry:US sourcelang:english",
    ],
}

def job(group,market,url,kind,query=None):
    return {"group":group,"market":market,"url":url,"kind":kind,"query":query}

def gnews_url(query,market):
    hl,gl,ceid=locale[market]
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={ceid}"

def company_batch(db):
    stocks=sorted(s for s in tk.by_symbol if tk.is_stock(s))
    row=db.get(feedstat,"crawl:cursor")
    cursor=(row.last_count or 0) if row else 0
    n=min(config.crawl_company_batch,len(stocks))
    batch=[stocks[(cursor+i)%len(stocks)] for i in range(n)]
    if row is None:
        row=feedstat(url="crawl:cursor",source="cursor",market="IN")
        db.add(row)
    row.last_count=(cursor+n)%len(stocks)
    db.commit()
    return batch

def plan(db):
    jobs=[]
    for domain,(name,markets) in trusted.trusted.items():
        for m in markets:
            jobs.append(job("google-sites",m,gnews_url(f"site:{domain} {terms[m]} when:2d",m),"gnews"))
    for m in ("IN","US"):
        for sector in tk.sector_names:
            if m=="US" and sector=="Macroeconomics":
                kw='"federal reserve" OR inflation OR "interest rates" OR GDP'
            else:
                kw=" OR ".join(f'"{k}"' for k in tk.sector_keywords[sector][:4])
            place="india" if m=="IN" else "us"
            jobs.append(job("google-sectors",m,gnews_url(f"({kw}) {place} stocks when:1d",m),"gnews"))
    for sym in company_batch(db):
        info=tk.by_symbol[sym]
        m=info["market"]
        jobs.append(job("google-companies",m,gnews_url(f'"{info["name"]}" (shares OR stock) when:2d',m),"gnews"))
        ysym=tk.yahoo_symbol(sym)
        if ysym:
            url=f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={quote_plus(ysym)}&region={m}&lang=en-{m}"
            jobs.append(job("yahoo-tickers",m,url,"yahoo"))
    for m,queries in gdelt_queries.items():
        for q in queries:
            jobs.append(job("gdelt",m,"https://api.gdeltproject.org/api/v2/doc/doc","gdelt",q))
    return jobs

def seen_to_struct(text):
    try:
        return datetime.strptime(text,"%Y%m%dT%H%M%SZ").timetuple()
    except (TypeError,ValueError):
        return None

def fetch_gdelt(j):
    params={"query":j["query"],"mode":"artlist","maxrecords":250,"format":"json","sort":"datedesc","timespan":"24h"}
    try:
        res=requests.get(j["url"],params=params,headers=ingest.headers,timeout=config.http_timeout*2)
    except requests.RequestException as exc:
        return [],type(exc).__name__
    if res.status_code!=200:
        return [],f"HTTP {res.status_code}"
    try:
        arts=res.json().get("articles") or []
    except ValueError:
        return [],"not JSON (rate limited?)"
    entries=[]
    for a in arts:
        url=a.get("url","")
        entries.append({"title":a.get("title",""),"link":url,"summary":"","published_parsed":seen_to_struct(a.get("seendate")),"source":{"title":trusted.name_of(url) or "","href":url}})
    return entries,(None if entries else "no articles")

def run_job(j):
    time.sleep(random.uniform(0,0.4))
    return ingest.fetch_feed_status(j["url"])

def to_items(j,entries):
    items=[]
    for e in entries:
        href=(e.get("source") or {}).get("href") or e.get("link","")
        domain=trusted.match(href) or trusted.match(e.get("link",""))
        if not domain:
            continue
        item=ingest.parse_entry(trusted.trusted[domain][0],e,j["market"],"google" if j["kind"]=="gnews" else None)
        if item is None:
            continue
        item["source"]=trusted.trusted[domain][0]
        items.append(item)
    return items

def handle(db,j,entries,error,seen,stats):
    key=(j["group"],j["market"])
    st=stats.setdefault(key,{"jobs":0,"failed":0,"entries":0,"new":0,"errors":{}})
    st["jobs"]+=1
    if error and not entries:
        st["failed"]+=1
        st["errors"][error]=st["errors"].get(error,0)+1
        return
    fresh=ingest.new_items(db,to_items(j,entries),seen)
    st["entries"]+=len(entries)
    st["new"]+=ingest.save_items(db,fresh)

def record_stats(db,stats):
    for (group,market),st in stats.items():
        feed={"url":f"crawl:{group}:{market}","source":group_names[group],"market":market}
        failed=st["failed"]
        top=max(st["errors"],key=st["errors"].get) if st["errors"] else None
        if failed==st["jobs"] and st["jobs"]>0:
            ingest.record_feed(db,feed,0,0,f"all {failed} requests failed ({top})")
        else:
            note=f"partial: {failed} of {st['jobs']} requests failed ({top})" if failed else None
            ingest.record_feed(db,feed,st["entries"],st["new"],None,note)

def run_deep_crawl(db,budget=None):
    budget=budget or config.crawl_budget_seconds
    start=time.time()
    jobs=plan(db)
    web=[j for j in jobs if j["kind"]!="gdelt"]
    slow=[j for j in jobs if j["kind"]=="gdelt"]
    seen=set()
    stats={}
    with ThreadPoolExecutor(max_workers=config.crawl_workers) as pool:
        for part in ingest.chunks(web,24):
            if time.time()-start>budget:
                log.warning("crawl budget reached, skipping the rest")
                break
            for j,(entries,error) in zip(part,pool.map(run_job,part)):
                handle(db,j,entries,error,seen,stats)
    for j in slow:
        if time.time()-start>budget:
            break
        entries,error=fetch_gdelt(j)
        handle(db,j,entries,error,seen,stats)
        time.sleep(config.gdelt_delay_seconds)
    record_stats(db,stats)
    new=sum(st["new"] for st in stats.values())
    log.info("deep crawl: %s requests, %s new articles in %ss",sum(st["jobs"] for st in stats.values()),new,int(time.time()-start))
    return new
