import calendar
import hashlib
import logging
import re
from datetime import datetime,timezone
from urllib.parse import urlparse,urlunparse,parse_qsl,urlencode
import feedparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select,or_
from sqlalchemy.exc import IntegrityError
from concurrent.futures import ThreadPoolExecutor
from . import config,trusted
from .models import article,feedstat

log=logging.getLogger(__name__)
headers={"User-Agent":config.user_agent,"Accept":"application/rss+xml,application/xml,text/xml,*/*","Accept-Language":"en-US,en;q=0.9"}
junk_params={"from","ref","source","utm_source","utm_medium","utm_campaign","utm_content","utm_term"}

def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def norm_title(title):
    return re.sub(r"[^a-z0-9]+"," ",title.lower()).strip()

def clean_text(html):
    text=BeautifulSoup(html or "","html.parser").get_text(" ",strip=True)
    return re.sub(r"\s+"," ",text).strip()

def canonical_url(url):
    parts=urlparse(url.strip())
    query=[(k,v) for k,v in parse_qsl(parts.query) if k.lower() not in junk_params]
    return urlunparse((parts.scheme,parts.netloc.lower(),parts.path,"",urlencode(query),""))

def fetch_feed_status(url):
    try:
        res=requests.get(url,headers=headers,timeout=config.http_timeout)
        if res.status_code!=200:
            return [],f"HTTP {res.status_code}"
        parsed=feedparser.parse(res.content)
    except requests.RequestException as exc:
        return [],type(exc).__name__
    if not parsed.entries:
        reason=str(parsed.get("bozo_exception") or "no entries")
        return [],reason[:200]
    return parsed.entries,None

def fetch_feed(url):
    return fetch_feed_status(url)[0]

def extract_full_text(url):
    try:
        res=requests.get(url,headers=headers,timeout=config.http_timeout)
        res.raise_for_status()
    except requests.RequestException:
        return ""
    soup=BeautifulSoup(res.text,"html.parser")
    for tag in soup(["script","style","nav","footer","aside","form"]):
        tag.decompose()
    root=soup.find("article") or soup.find("main") or soup
    paras=[p.get_text(" ",strip=True) for p in root.find_all("p")]
    return " ".join(p for p in paras if len(p)>40)[:8000]

def parse_entry(source,entry,market="IN",kind=None):
    title=clean_text(entry.get("title",""))[:500]
    link=entry.get("link","").strip()
    if not title or not link:
        return None
    summary=clean_text(entry.get("summary") or entry.get("description") or "")
    if kind=="google":
        src=entry.get("source") or {}
        publisher=clean_text(src.get("title",""))
        known=trusted.name_of(src.get("href",""))
        for name in (publisher,known):
            suffix=" - "+name if name else ""
            if suffix and title.endswith(suffix):
                title=title[:-len(suffix)].strip()
                break
        source=publisher or known or source
        summary=""
    stamp=entry.get("published_parsed") or entry.get("updated_parsed")
    now=datetime.now(timezone.utc)
    published=datetime.fromtimestamp(calendar.timegm(stamp),tz=timezone.utc) if stamp else now
    if published>now:
        published=now
    link=canonical_url(link)
    return {
        "source":source,
        "market":market,
        "title":title,
        "url":link[:1000],
        "summary":summary,
        "published_at":published,
        "url_hash":sha(link),
        "title_hash":sha(norm_title(title)),
    }

def is_duplicate(db,item,seen):
    if item["url_hash"] in seen or item["title_hash"] in seen:
        return True
    hit=db.execute(select(article.id).where(or_(article.url_hash==item["url_hash"],article.title_hash==item["title_hash"])).limit(1)).first()
    return hit is not None

def record_feed(db,feed,count,new,error,note=None):
    now=datetime.now(timezone.utc)
    row=db.get(feedstat,feed["url"])
    if row is None:
        row=feedstat(url=feed["url"])
        db.add(row)
    row.source=feed["source"]
    row.market=feed["market"]
    row.last_attempt_at=now
    row.last_count=count
    row.last_new=new
    row.last_error=error or note
    if error is None:
        row.last_ok_at=now
    db.commit()

def chunks(seq,n):
    for i in range(0,len(seq),n):
        yield seq[i:i+n]

def new_items(db,items,seen):
    fresh=[]
    for it in items:
        if it["url_hash"] in seen or it["title_hash"] in seen:
            continue
        seen.add(it["url_hash"])
        seen.add(it["title_hash"])
        fresh.append(it)
    if not fresh:
        return []
    found=set()
    for part in chunks([i["url_hash"] for i in fresh],500):
        found|=set(db.execute(select(article.url_hash).where(article.url_hash.in_(part))).scalars())
    for part in chunks([i["title_hash"] for i in fresh],500):
        found|=set(db.execute(select(article.title_hash).where(article.title_hash.in_(part))).scalars())
    return [i for i in fresh if i["url_hash"] not in found and i["title_hash"] not in found]

def save_items(db,items,raws=None):
    raws=raws or {}
    def build(i):
        return article(raw_content=raws.get(i["url_hash"],""),**i)
    if not items:
        return 0
    try:
        db.add_all([build(i) for i in items])
        db.commit()
        return len(items)
    except IntegrityError:
        db.rollback()
    saved=0
    for i in items:
        try:
            db.add(build(i))
            db.commit()
            saved+=1
        except IntegrityError:
            db.rollback()
    return saved

def scrape_texts(items,limit):
    chosen=items[:max(0,limit)]
    if not chosen:
        return {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        texts=list(pool.map(lambda i:extract_full_text(i["url"]),chosen))
    return {i["url_hash"]:t for i,t in zip(chosen,texts)}

def trusted_source(entry):
    href=(entry.get("source") or {}).get("href") or entry.get("link","")
    return trusted.name_of(href)

def ingest_all(db):
    created=0
    scraped=0
    seen=set()
    for feed in config.feeds:
        try:
            entries,error=fetch_feed_status(feed["url"])
        except Exception as exc:
            log.warning("feed failed %s: %s",feed["url"],exc)
            record_feed(db,feed,0,0,type(exc).__name__)
            continue
        entries=entries[:config.max_entries_per_feed]
        items=[]
        for entry in entries:
            if feed.get("kind")=="google":
                name=trusted_source(entry)
                if not name:
                    continue
            item=parse_entry(feed["source"],entry,feed["market"],feed.get("kind"))
            if item is None:
                continue
            if feed.get("kind")=="google":
                item["source"]=name
            items.append(item)
        fresh=new_items(db,items,seen)
        raws={}
        if feed.get("scrape",True):
            wanted=[i for i in fresh if config.fetch_full_text or len(i["summary"])<60]
            raws=scrape_texts(wanted,config.max_scrape_per_run-scraped)
            scraped+=len(raws)
        saved=save_items(db,fresh,raws)
        created+=saved
        record_feed(db,feed,len(entries),saved,error)
    log.info("ingested %s new articles, scraped %s pages",created,scraped)
    return created
