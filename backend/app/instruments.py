import csv
import io
import json
import logging
import re
import time
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import requests
from sqlalchemy import select,func
from . import config,ingest,tickers as tk
from .models import instrument

log=logging.getLogger(__name__)
nse_url="https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
nifty_urls=[
    "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",
]
bhav_url="https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d}.csv"
nasdaq_url="https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
other_url="https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
screener_url="https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true"
yahoo_search_url="https://query2.finance.yahoo.com/v1/finance/search"
nse_series={"EQ","BE","BZ","SM","SZ","ST"}
skip_words=("warrant","rights","preferred","depositary share","units","notes due","% ","trust preferred")
state={"loaded":0.0,"skipped":0,"screener":None,"screener_at":0.0}

in_industry={
    "financial services":"Banking","information technology":"IT","healthcare":"Pharma",
    "automobile and auto components":"Auto","fast moving consumer goods":"FMCG",
    "oil gas & consumable fuels":"Energy","power":"Energy","metals & mining":"Metals",
    "telecommunication":"Telecom","construction":"Infrastructure","construction materials":"Infrastructure",
    "capital goods":"Infrastructure","realty":"Infrastructure","consumer durables":"FMCG",
    "consumer services":"FMCG","textiles":"FMCG",
}
us_sectors={
    "technology":"IT","health care":"Pharma","finance":"Banking","consumer staples":"FMCG",
    "consumer discretionary":"FMCG","energy":"Energy","basic materials":"Metals","industrials":"Infrastructure",
    "real estate":"Infrastructure","utilities":"Energy","telecommunications":"Telecom",
}
name_rules=[
    ("Banking",r"\b(bank|bancorp|finance|financial|financials|insurance|assurance|credit|lending|securities|capital|housing finance|microfin\w*)\b"),
    ("Pharma",r"\b(pharma\w*|drugs|labs|laborator\w*|health\w*|hospitals?|biotech\w*|therapeutics?|medical|life ?sciences|bio\w*)\b"),
    ("IT",r"\b(software|infotech|infosystems|technolog\w*|tech|systems|digital|data|cyber\w*|cloud|computers?|semiconductors?|networks?|internet|info)\b"),
    ("Auto",r"\b(motors?|auto\w*|tyres?|tires?|vehicles?|bikes?|scooters?|forgings?)\b"),
    ("Telecom",r"\b(telecom\w*|communications?|wireless|broadband)\b"),
    ("Metals",r"\b(steel|steels|metals?|alloys?|alumin\w+|copper|zinc|mining|minerals?|iron|ispat)\b"),
    ("Energy",r"\b(energy|power|oil|gas|petro\w*|solar|renewables?|coal|electric\w*|utilities)\b"),
    ("Infrastructure",r"\b(infra\w*|construction|cement\w*|engineering|realty|properties|developers?|housing|estate|projects?|builders?|railways?|ports?|logistics|shipping)\b"),
    ("FMCG",r"\b(foods?|consumer|beverages?|tea|sugar|agro|dairy|textiles?|apparel|retail|brands?|restaurants?|hotels?|paints?|jewel\w*)\b"),
]
name_patterns=[(s,re.compile(p,re.I)) for s,p in name_rules]

def infer_sector(name):
    for sector,pattern in name_patterns:
        if pattern.search(name or ""):
            return sector
    return "General"

def us_sector(sector,industry=""):
    if "auto" in (industry or "").lower():
        return "Auto"
    return us_sectors.get((sector or "").strip().lower())

def number(text):
    try:
        return float(str(text).replace("$","").replace(",","").replace("%","").strip())
    except ValueError:
        return None

def get_text(url,extra=None):
    headers={"User-Agent":config.user_agent,"Accept-Language":"en-US,en;q=0.9"}
    headers.update(extra or {})
    res=requests.get(url,headers=headers,timeout=30)
    res.raise_for_status()
    return res.text

def parse_nse(text):
    out={}
    for row in csv.DictReader(io.StringIO(text)):
        row={(k or "").strip().upper():(v or "").strip() for k,v in row.items()}
        symbol=row.get("SYMBOL","")
        name=row.get("NAME OF COMPANY","")
        if symbol and name and row.get("SERIES","EQ") in nse_series:
            out[symbol]=(symbol,name,"IN","NSE")
    return list(out.values())

def parse_nifty(text):
    out={}
    for i,row in enumerate(csv.DictReader(io.StringIO(text))):
        row={(k or "").strip().upper():(v or "").strip() for k,v in row.items()}
        symbol=row.get("SYMBOL","")
        if symbol and symbol not in out:
            out[symbol]=(in_industry.get(row.get("INDUSTRY","").lower()),i)
    return out

def parse_trader(text,symbol_key,exchange):
    out={}
    lines=[l for l in text.splitlines() if l.strip()]
    if not lines:
        return []
    header=[h.strip() for h in lines[0].split("|")]
    for line in lines[1:]:
        if line.startswith("File Creation Time"):
            continue
        d=dict(zip(header,[p.strip() for p in line.split("|")]))
        symbol=d.get(symbol_key,"").upper()
        name=d.get("Security Name","")
        if not symbol or not name or d.get("ETF","N")!="N" or d.get("Test Issue","N")!="N":
            continue
        if any(c in symbol for c in "$^~="):
            continue
        low=name.lower()
        if any(w in low for w in skip_words):
            continue
        symbol=symbol.replace(".","-").replace("/","-")
        out[symbol]=(symbol,name.split(" - ")[0].strip(),"US",d.get("Exchange") or exchange)
    return list(out.values())

def parse_screener(text):
    data=json.loads(text).get("data") or {}
    rows=data.get("rows") or (data.get("table") or {}).get("rows") or []
    out={}
    for r in rows:
        symbol=(r.get("symbol") or "").strip().upper().replace(".","-").replace("/","-")
        if not symbol:
            continue
        out[symbol]={"sector":us_sector(r.get("sector"),r.get("industry")),"cap":number(r.get("marketCap")) or 0.0,"price":number(r.get("lastsale")),"pct":number(r.get("pctchange"))}
    return out

def parse_bhav(text):
    out={}
    for row in csv.DictReader(io.StringIO(text)):
        row={(k or "").strip().upper():(v or "").strip() for k,v in row.items()}
        if row.get("SERIES") not in nse_series:
            continue
        close=number(row.get("CLOSE_PRICE"))
        prev=number(row.get("PREV_CLOSE"))
        if close and prev and prev>0:
            out[row["SYMBOL"]]=(close,prev)
    return out

def fetch_screener():
    if state["screener"] is not None and time.time()-state["screener_at"]<240:
        return state["screener"]
    state["screener"]=parse_screener(get_text(screener_url,{"Accept":"application/json"}))
    state["screener_at"]=time.time()
    return state["screener"]

def fetch_in():
    return parse_nse(get_text(nse_url,{"Referer":"https://www.nseindia.com/"}))

def fetch_in_meta():
    meta={}
    for url in nifty_urls:
        try:
            for symbol,(sector,i) in parse_nifty(get_text(url,{"Referer":"https://www.nseindia.com/"})).items():
                meta.setdefault(symbol,(sector,i+(0 if "500" in url else 500)))
        except Exception as exc:
            log.warning("sector list %s failed: %s",url,exc)
    return meta

def fetch_us():
    rows={}
    for r in parse_trader(get_text(nasdaq_url),"Symbol","NASDAQ")+parse_trader(get_text(other_url),"ACT Symbol","NYSE"):
        rows.setdefault(r[0],r)
    return list(rows.values())

def fetch_us_meta():
    try:
        data=fetch_screener()
    except Exception as exc:
        log.warning("us screener failed: %s",exc)
        return {}
    ordered=sorted(data.items(),key=lambda kv:-kv[1]["cap"])
    return {sym:(d["sector"],i) for i,(sym,d) in enumerate(ordered)}

def in_price_rows():
    ist=ZoneInfo("Asia/Kolkata")
    today=datetime.now(ist)
    for back in range(0,7):
        day=today-timedelta(days=back)
        if day.weekday()>=5:
            continue
        try:
            text=get_text(bhav_url.format(d=day.strftime("%d%m%Y")),{"Referer":"https://www.nseindia.com/"})
        except requests.RequestException:
            continue
        data=parse_bhav(text)
        if data:
            stamp=day.replace(hour=15,minute=30,second=0,microsecond=0).astimezone(timezone.utc)
            return [(s,c,p,round((c-p)/p*100,2),"INR",stamp) for s,(c,p) in data.items()]
    return []

def us_price_rows(now=None):
    now=now or datetime.now(timezone.utc)
    stamp=now-timedelta(minutes=10)
    rows=[]
    for sym,d in fetch_screener().items():
        if d["price"] and d["pct"] is not None and d["pct"]>-100:
            rows.append((sym,d["price"],round(d["price"]/(1+d["pct"]/100),4),d["pct"],"USD",stamp))
    return rows

def replace_market(db,market,rows,meta=None):
    meta=meta or {}
    existing={r.symbol:r for r in db.execute(select(instrument).where(instrument.market==market)).scalars().all()}
    fresh={r[0]:r for r in rows}
    for symbol,(sym,name,mk,exchange) in fresh.items():
        sector,rank=meta.get(symbol,(None,None))
        sector=sector or infer_sector(name)
        rank=rank if rank is not None else 100000
        row=existing.get(symbol)
        if row is None:
            db.add(instrument(symbol=sym,name=name[:200],market=mk,exchange=exchange,sector=sector,rank=rank))
        else:
            row.name=name[:200]
            row.sector=sector
            row.rank=rank
    for symbol,row in existing.items():
        if symbol not in fresh and not (row.exchange or "").startswith("REMOTE"):
            db.delete(row)
    db.commit()

def load(db):
    rows=db.execute(select(instrument.symbol,instrument.name,instrument.market,instrument.sector,instrument.rank).order_by(instrument.market,instrument.symbol)).all()
    count,skipped=tk.register_instruments([tuple(r) for r in rows])
    state["loaded"]=time.time()
    state["skipped"]=skipped
    return count

def count(db):
    return db.scalar(select(func.count(instrument.id)))

def sync(db):
    total=0
    plan=(
        ("IN","Listed stocks (NSE)",fetch_in,fetch_in_meta),
        ("US","Listed stocks (Nasdaq Trader)",fetch_us,fetch_us_meta),
    )
    for market,source,fetcher,metafetcher in plan:
        feed={"url":f"crawl:instruments:{market}","source":source,"market":market}
        try:
            rows=fetcher()
            if len(rows)<100:
                raise ValueError(f"only {len(rows)} rows, ignoring")
        except Exception as exc:
            log.warning("instrument sync %s failed: %s",market,exc)
            ingest.record_feed(db,feed,0,0,f"{type(exc).__name__}: {str(exc)[:120]}")
            continue
        before=db.scalar(select(func.count(instrument.id)).where(instrument.market==market))
        replace_market(db,market,rows,metafetcher())
        after=db.scalar(select(func.count(instrument.id)).where(instrument.market==market))
        ingest.record_feed(db,feed,len(rows),max(0,after-before),None)
        total+=len(rows)
    load(db)
    log.info("instrument sync done, %s stocks listed",total)
    return total

def yahoo_search(q,market=None):
    res=requests.get(yahoo_search_url,params={"q":q,"quotesCount":8,"newsCount":0,"listsCount":0},headers={"User-Agent":config.user_agent},timeout=6)
    res.raise_for_status()
    out=[]
    for it in res.json().get("quotes",[]):
        if it.get("quoteType")!="EQUITY":
            continue
        sym=(it.get("symbol") or "").upper()
        name=it.get("longname") or it.get("shortname") or sym
        exch=(it.get("exchange") or "").upper()
        if sym.endswith(".NS"):
            hit=(sym[:-3],name,"IN","REMOTE-NSE")
        elif sym.endswith(".BO"):
            hit=(sym,name,"IN","REMOTE-BSE")
        elif exch in {"NMS","NYQ","NGM","NCM","ASE","PCX","BTS"} and "." not in sym:
            hit=(sym,name,"US","REMOTE-"+exch)
        else:
            continue
        if market is None or hit[2]==market:
            out.append(hit)
    return out

def add_remote(db,hits):
    added=0
    for symbol,name,market,exchange in hits:
        if symbol in tk.by_symbol:
            continue
        exists=db.scalar(select(instrument.id).where(instrument.symbol==symbol,instrument.market==market))
        if exists:
            continue
        db.add(instrument(symbol=symbol,name=name[:200],market=market,exchange=exchange,sector=infer_sector(name),rank=900000))
        added+=1
    if added:
        db.commit()
        load(db)
    return added
