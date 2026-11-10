from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,text
from app import nlp,pipeline,ingest,quotes,auth,db as dbmod
from app.db import base,engine,sessionlocal,init_db
from app.main import api
from app.models import article,pricequote

seed=[
    ("TCS and Infosys rally as IT stocks surge after strong deal wins","Software exporters led the gains across the market today.","Economic Times","IN",1),
    ("HDFC Bank shares tumble as NPA concerns weigh on lenders","Banking stocks slid across the board on Wednesday.","Moneycontrol","IN",2),
    ("RBI keeps repo rate unchanged in policy review","The central bank held rates steady in its latest policy.","LiveMint","IN",30),
    ("Nvidia and Apple surge as chip stocks rally to record highs","Technology shares led Wall Street higher on Tuesday.","CNBC","US",1),
    ("Tesla shares plunge after weak delivery numbers","Investors fear a slowdown in electric vehicle demand.","MarketWatch","US",2),
]

creds={"email":"asha@example.com","password":"correct horse","name":"Asha"}

@pytest.fixture()
def raw():
    auth.attempts.clear()
    base.metadata.drop_all(engine)
    init_db()
    db=sessionlocal()
    now=datetime.now(timezone.utc)
    for i,(title,summary,source,market,hours_ago) in enumerate(seed):
        item=ingest.parse_entry(source,{"title":title,"link":f"https://example.com/{i}?utm_source=x","summary":summary},market)
        item["published_at"]=now-timedelta(hours=hours_ago)
        db.add(article(**item))
    db.commit()
    assert pipeline.process_pending(db)==5
    db.close()
    with TestClient(api) as c:
        yield c

@pytest.fixture()
def client(raw):
    r=raw.post("/api/auth/register",json=creds)
    assert r.status_code==201
    return raw

def test_entities_and_sector():
    out=nlp.analyse_batch([(seed[0][0],seed[0][1])])[0]
    assert {"TCS","INFY"}<={e["symbol"] for e in out["entities"]}
    assert out["sector"]=="IT"
    assert out["label"]=="Bullish"

def test_bearish_banking():
    out=nlp.analyse_batch([(seed[1][0],seed[1][1])])[0]
    assert out["label"]=="Bearish"
    assert out["sector"]=="Banking"
    assert "HDFCBANK" in {e["symbol"] for e in out["entities"]}

def test_dedupe_hash_ignores_tracking_params():
    a=ingest.parse_entry("x",{"title":"Same story","link":"https://e.com/a?utm_source=1"})
    b=ingest.parse_entry("y",{"title":"Same story","link":"https://e.com/a?from=mdr"})
    assert a["url_hash"]==b["url_hash"]

def test_data_requires_login(raw):
    for path in ["/api/articles","/api/market-pulse","/api/movers","/api/ticker/TCS","/api/tickers/search?q=a"]:
        assert raw.get(path).status_code==401
    assert raw.post("/api/admin/refresh").status_code==401
    assert raw.get("/api/health").status_code==200

def test_register_login_logout(raw):
    assert raw.post("/api/auth/register",json=creds).status_code==201
    assert raw.get("/api/auth/me").json()["email"]=="asha@example.com"
    assert raw.post("/api/auth/register",json=creds).status_code==409
    assert raw.post("/api/auth/logout").status_code==200
    assert raw.get("/api/auth/me").status_code==401
    assert raw.post("/api/auth/login",json={"email":"asha@example.com","password":"wrong password"}).status_code==401
    ok=raw.post("/api/auth/login",json={"email":"ASHA@example.com","password":creds["password"]})
    assert ok.status_code==200
    assert raw.get("/api/auth/me").status_code==200

def test_register_validation(raw):
    assert raw.post("/api/auth/register",json={"email":"nope","password":"longenough1"}).status_code==422
    assert raw.post("/api/auth/register",json={"email":"a@b.co","password":"short"}).status_code==422

def test_google_login(raw,monkeypatch):
    from google.oauth2 import id_token
    info={"sub":"g-123","email":"gina@example.com","email_verified":True,"name":"Gina"}
    monkeypatch.setattr(id_token,"verify_oauth2_token",lambda cred,req,aud:info)
    r=raw.post("/api/auth/google",json={"credential":"x"})
    assert r.status_code==200 and r.json()["name"]=="Gina"
    assert raw.get("/api/auth/me").json()["email"]=="gina@example.com"
    raw.post("/api/auth/logout")
    assert raw.post("/api/auth/login",json={"email":"gina@example.com","password":"anything1"}).status_code==401
    info["email_verified"]=False
    assert raw.post("/api/auth/google",json={"credential":"x"}).status_code==401

def test_google_bad_token_and_outage(raw,monkeypatch):
    from google.oauth2 import id_token
    from google.auth.exceptions import TransportError
    def bad(cred,req,aud):
        raise ValueError("bad token")
    monkeypatch.setattr(id_token,"verify_oauth2_token",bad)
    assert raw.post("/api/auth/google",json={"credential":"garbage"}).status_code==401
    def down(cred,req,aud):
        raise TransportError("offline")
    monkeypatch.setattr(id_token,"verify_oauth2_token",down)
    assert raw.post("/api/auth/google",json={"credential":"x"}).status_code==503
    assert raw.get("/api/auth/config").json()["google_client_id"]

def test_articles_split_by_market(client):
    india=client.get("/api/articles",params={"market":"IN"}).json()
    us=client.get("/api/articles",params={"market":"US"}).json()
    assert india["total"]==3 and us["total"]==2
    assert {i["source"] for i in us["items"]}=={"CNBC","MarketWatch"}
    assert client.get("/api/articles",params={"market":"XX"}).status_code==422
    assert client.get("/api/articles",params={"sentiment":"nope"}).status_code==422
    assert client.get("/api/articles",params={"ticker":"tcs"}).json()["total"]==1

def test_market_pulse_per_market(client):
    p=client.get("/api/market-pulse",params={"hours":24,"market":"IN"}).json()
    assert p["overall"]["total"]==2
    sectors={s["sector"]:s for s in p["sectors"]}
    assert sectors["IT"]["leaning"]=="Bullish"
    assert sectors["Banking"]["leaning"]=="Bearish"
    us=client.get("/api/market-pulse",params={"hours":24,"market":"US"}).json()
    assert us["overall"]["total"]==2
    assert {t["symbol"] for t in us["top_tickers"]}>={"NVDA","AAPL","TSLA"}
    week=client.get("/api/market-pulse",params={"hours":168,"market":"IN"}).json()
    assert week["overall"]["total"]==3 and week["granularity"]=="day"

def test_movers(client):
    db=sessionlocal()
    now=datetime.now(timezone.utc)
    for sym,pct in [("TCS",1.5),("HDFCBANK",-3.2),("NVDA",4.1),("NIFTY",0.4)]:
        db.add(pricequote(symbol=sym,market="x",price=100.0,prev_close=100.0/(1+pct/100),change_pct=pct,currency="INR",updated_at=now))
    db.commit()
    db.close()
    m=client.get("/api/movers",params={"market":"IN","by":"price"}).json()
    assert m["price_available"]
    assert [i["symbol"] for i in m["items"]][:2]==["HDFCBANK","TCS"]
    assert "NVDA" not in [i["symbol"] for i in m["items"]]
    assert [i["symbol"] for i in m["indices"]]==["NIFTY"]
    s=client.get("/api/movers",params={"market":"IN","by":"sentiment"}).json()
    assert {i["symbol"] for i in s["items"]}>={"TCS","HDFCBANK"}
    us=client.get("/api/movers",params={"market":"US","by":"price"}).json()
    assert [i["symbol"] for i in us["items"]]==["NVDA"]
    assert client.get("/api/movers",params={"by":"nope"}).status_code==422

def test_ticker_endpoint_with_quote(client):
    db=sessionlocal()
    db.add(pricequote(symbol="INFY",market="IN",price=1500.0,prev_close=1490.0,change_pct=0.67,currency="INR",updated_at=datetime.now(timezone.utc)))
    db.commit()
    db.close()
    r=client.get("/api/ticker/INFY").json()
    assert r["name"]=="Infosys" and r["stats"]["total"]==1
    assert r["quote"]["change_pct"]==0.67
    assert client.get("/api/ticker/ZZZZ").status_code==404

def test_search_scoped_by_market(client):
    inr=[s["symbol"] for s in client.get("/api/tickers/search",params={"q":"a","market":"IN","limit":20}).json()]
    usd=[s["symbol"] for s in client.get("/api/tickers/search",params={"q":"appl","market":"US"}).json()]
    assert "AAPL" in usd and "AAPL" not in inr

def test_fetch_quote_parsing(monkeypatch):
    class res:
        def raise_for_status(self):pass
        def json(self):
            return {"chart":{"result":[{"meta":{"regularMarketPrice":110.0,"chartPreviousClose":100.0,"currency":"USD"}}]}}
    monkeypatch.setattr(quotes.requests,"get",lambda *a,**k:res())
    q=quotes.fetch_quote("AAPL")
    assert q["change_pct"]==10.0 and q["currency"]=="USD"
    assert quotes.fetch_quote("RBI") is None

def test_fetch_quote_failure(monkeypatch):
    def boom(*a,**k):
        raise quotes.requests.RequestException("down")
    monkeypatch.setattr(quotes.requests,"get",boom)
    assert quotes.fetch_quote("TCS") is None

def test_old_database_gets_market_column(tmp_path,monkeypatch):
    old=create_engine(f"sqlite:///{tmp_path}/old.db")
    with old.begin() as conn:
        conn.execute(text("CREATE TABLE articles (id INTEGER PRIMARY KEY, title VARCHAR(500), source VARCHAR(80), url VARCHAR(1000), url_hash VARCHAR(64), title_hash VARCHAR(64), published_at DATETIME, summary TEXT, raw_content TEXT, created_at DATETIME)"))
        conn.execute(text("INSERT INTO articles (id,title,source,url,url_hash,title_hash) VALUES (1,'t','s','u','h','h')"))
    monkeypatch.setattr(dbmod,"engine",old)
    dbmod.init_db()
    with old.begin() as conn:
        assert conn.execute(text("SELECT market FROM articles")).scalar()=="IN"

def test_refresh_falls_back_when_queue_down(client,monkeypatch):
    from app import main
    called=[]
    monkeypatch.setattr(main,"run_inline",lambda:called.append(1))
    r=client.post("/api/admin/refresh")
    assert r.status_code==200 and r.json()["mode"]=="inline" and called==[1]

def test_status_and_health(client):
    assert client.get("/api/status").json()["state"]=="down"
    h=client.get("/api/health").json()
    assert h["articles"]==5 and h["scored"]==5 and h["scored_at"]

def test_sector_click_changes_trend_and_stocks(client):
    all_=client.get("/api/market-pulse",params={"market":"IN","hours":168}).json()
    bank=client.get("/api/market-pulse",params={"market":"IN","hours":168,"sector":"Banking"}).json()
    assert bank["sector"]=="Banking"
    assert bank["sector_stats"]["total"]==1 and bank["sector_stats"]["leaning"]=="Bearish"
    assert sum(p["count"] for p in bank["trend"])==1
    assert sum(p["count"] for p in all_["trend"])==3
    assert [t["symbol"] for t in bank["top_tickers"]]==["HDFCBANK"]
    assert client.get("/api/market-pulse",params={"sector":"Nope"}).status_code==422
    news=client.get("/api/articles",params={"market":"IN","sector":"Banking"}).json()
    assert news["total"]==1 and news["items"][0]["sentiment"]=="Bearish"

def test_new_articles_only_tag_their_own_market():
    text=("Indian IT rallies as TCS jumps and Apple supplier orders surge","")
    india=nlp.analyse_batch([(text[0],text[1],"IN")])[0]
    us=nlp.analyse_batch([(text[0],text[1],"US")])[0]
    assert {e["symbol"] for e in india["entities"]}=={"TCS"}
    assert {e["symbol"] for e in us["entities"]}=={"AAPL"}

def test_old_cross_market_tags_are_hidden_and_purged(client):
    from app.models import ticker
    db=sessionlocal()
    a=db.query(article).filter(article.market=="IN").first()
    db.add(ticker(article_id=a.id,symbol="AAPL",company_name="Apple"))
    db.commit()
    india=client.get("/api/articles",params={"market":"IN"}).json()["items"]
    assert all(t["symbol"]!="AAPL" for i in india for t in i["tickers"])
    pulse=client.get("/api/market-pulse",params={"market":"IN","hours":168}).json()
    assert "AAPL" not in [t["symbol"] for t in pulse["top_tickers"]]
    assert pipeline.purge_cross_market(db)==1
    assert db.query(ticker).filter(ticker.symbol=="AAPL",ticker.article_id==a.id).count()==0
    db.close()

def test_movers_split_and_sector_filter(client):
    db=sessionlocal()
    now=datetime.now(timezone.utc)
    for sym,pct in [("TCS",1.5),("HDFCBANK",-3.2),("ICICIBANK",2.0),("NVDA",4.1),("JPM",1.0)]:
        db.add(pricequote(symbol=sym,market="x",price=100.0,prev_close=100.0,change_pct=pct,currency="INR",updated_at=now))
    db.commit()
    db.close()
    india=client.get("/api/movers",params={"market":"IN","by":"price"}).json()
    assert {i["symbol"] for i in india["items"]}=={"TCS","HDFCBANK","ICICIBANK"}
    bank=client.get("/api/movers",params={"market":"IN","by":"price","sector":"Banking"}).json()
    assert [i["symbol"] for i in bank["items"]]==["HDFCBANK","ICICIBANK"]
    assert bank["sector"]=="Banking"
    us=client.get("/api/movers",params={"market":"US","by":"price","sector":"Banking"}).json()
    assert [i["symbol"] for i in us["items"]]==["JPM"]

def test_google_news_entry_parsing():
    entry={"title":"Sensex surges 500 points - Reuters","link":"https://news.google.com/rss/articles/abc","summary":"<a>junk</a>","source":{"title":"Reuters"}}
    item=ingest.parse_entry("Google News",entry,"IN","google")
    assert item["source"]=="Reuters" and item["title"]=="Sensex surges 500 points" and item["summary"]==""

def test_sources_endpoint_reports_feed_health(client,monkeypatch):
    from app import config
    feeds=[{"source":"Good","market":"IN","url":"https://good.test/rss"},{"source":"Bad","market":"US","url":"https://bad.test/rss"}]
    monkeypatch.setattr(config,"feeds",feeds)
    entry={"title":"Nifty ends higher as banks rally","link":"https://good.test/a","summary":"Markets closed higher on strong buying in banks today."}
    monkeypatch.setattr(ingest,"fetch_feed_status",lambda url:([entry],None) if "good" in url else ([],"HTTP 403"))
    monkeypatch.setattr(ingest,"extract_full_text",lambda url:"")
    db=sessionlocal()
    assert ingest.ingest_all(db)==1
    db.close()
    rows={r["source"]:r for r in client.get("/api/sources").json()}
    assert rows["Good"]["ok"] is True and rows["Good"]["new"]==1
    assert rows["Bad"]["ok"] is False and rows["Bad"]["error"]=="HTTP 403"

def test_market_hours():
    mon_in=datetime(2026,11,9,5,0,tzinfo=timezone.utc)
    sat=datetime(2026,11,7,5,0,tzinfo=timezone.utc)
    mon_us=datetime(2026,11,9,15,0,tzinfo=timezone.utc)
    assert quotes.market_open("IN",mon_in) and not quotes.market_open("US",mon_in)
    assert quotes.market_open("US",mon_us) and not quotes.market_open("IN",mon_us)
    assert not quotes.market_open("IN",sat) and not quotes.market_open("US",sat)

def test_live_quote_refresh_only_touches_open_markets(client,monkeypatch):
    calls=[]
    def fake(symbol):
        calls.append(symbol)
        return {"symbol":symbol,"price":10.0,"prev_close":9.0,"change_pct":11.11,"currency":"X"}
    monkeypatch.setattr(quotes,"fetch_quote",fake)
    quotes.state.update(fail=0,skip_until=0.0)
    db=sessionlocal()
    now=datetime(2026,11,9,5,0,tzinfo=timezone.utc)
    first=quotes.refresh_quotes(db,now)
    assert first>50
    calls.clear()
    later=now+timedelta(seconds=30)
    quotes.refresh_quotes(db,later)
    from app import tickers as tk
    assert calls and all(tk.market_of(s) in ("IN","ANY") for s in calls)
    assert not any(tk.market_of(s)=="US" for s in calls)
    db.close()

def test_quote_backoff_after_total_failure(client,monkeypatch):
    monkeypatch.setattr(quotes,"fetch_quote",lambda s:None)
    quotes.state.update(fail=0,skip_until=0.0)
    db=sessionlocal()
    assert quotes.refresh_quotes(db)==0
    assert quotes.state["skip_until"]>0
    monkeypatch.setattr(quotes,"fetch_quote",lambda s:(_ for _ in ()).throw(AssertionError("should be skipped")))
    assert quotes.refresh_quotes(db)==0
    quotes.state.update(fail=0,skip_until=0.0)
    db.close()
