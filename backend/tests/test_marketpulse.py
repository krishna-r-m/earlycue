from datetime import datetime,timedelta,timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,text
from app import nlp,pipeline,ingest,quotes,auth,crawl,trusted,db as dbmod
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
def admin(raw):
    with TestClient(api) as c:
        r=c.post("/api/auth/login",json={"email":"admin@gmail.com","password":"admin1234"})
        assert r.status_code==200 and r.json()["role"]=="admin"
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
    for path in ["/api/articles","/api/market-pulse","/api/movers","/api/ticker/TCS","/api/tickers/search?q=a","/api/status","/api/sources","/api/admin/overview","/api/admin/users"]:
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

def test_refresh_falls_back_when_queue_down(admin,monkeypatch):
    from app import main
    called=[]
    monkeypatch.setattr(main,"run_inline",lambda:called.append(1))
    r=admin.post("/api/admin/refresh")
    assert r.status_code==200 and r.json()["mode"]=="inline" and called==[1]

def test_status_and_health(admin,client):
    assert admin.get("/api/status").json()["state"]=="down"
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

def test_sources_endpoint_reports_feed_health(admin,monkeypatch):
    from app import config
    feeds=[{"source":"Good","market":"IN","url":"https://good.test/rss"},{"source":"Bad","market":"US","url":"https://bad.test/rss"}]
    monkeypatch.setattr(config,"feeds",feeds)
    entry={"title":"Nifty ends higher as banks rally","link":"https://good.test/a","summary":"Markets closed higher on strong buying in banks today."}
    monkeypatch.setattr(ingest,"fetch_feed_status",lambda url:([entry],None) if "good" in url else ([],"HTTP 403"))
    monkeypatch.setattr(ingest,"extract_full_text",lambda url:"")
    db=sessionlocal()
    assert ingest.ingest_all(db)==1
    db.close()
    rows={r["source"]:r for r in admin.get("/api/sources").json()}
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


def test_admin_account_is_seeded_and_others_are_users(raw,admin):
    me=admin.get("/api/auth/me").json()
    assert me["email"]=="admin@gmail.com" and me["name"]=="admin" and me["role"]=="admin"
    assert raw.post("/api/auth/register",json={"email":"admin@gmail.com","password":"whatever123"}).status_code==409
    r=raw.post("/api/auth/register",json=creds)
    assert r.json()["role"]=="user"

def test_regular_users_cannot_see_admin_details(client):
    for path in ["/api/status","/api/sources","/api/admin/overview","/api/admin/users"]:
        assert client.get(path).status_code==403
    assert client.post("/api/admin/refresh").status_code==403
    assert client.get("/api/market-pulse").status_code==200

def test_admin_overview_and_users(admin,client):
    o=admin.get("/api/admin/overview").json()
    assert o["articles"]==5 and o["scored"]==5 and o["pending"]==0
    assert o["in_articles"]==3 and o["us_articles"]==2 and o["users"]==2
    users=admin.get("/api/admin/users").json()
    assert [u["role"] for u in users]==["admin","user"]

def test_google_cannot_take_over_admin(raw,monkeypatch):
    from google.oauth2 import id_token
    info={"sub":"g-evil","email":"admin@gmail.com","email_verified":True,"name":"Not Admin"}
    monkeypatch.setattr(id_token,"verify_oauth2_token",lambda cred,req,aud:info)
    assert raw.post("/api/auth/google",json={"credential":"x"}).status_code==403
    assert raw.get("/api/auth/me").status_code==401

def test_existing_user_with_admin_email_is_promoted_on_startup(raw):
    db=sessionlocal()
    from app.models import user
    from app.auth import ensure_admin,hash_password
    row=db.query(user).filter(user.email=="admin@gmail.com").first()
    row.role="user"
    row.password_hash=hash_password("someone-elses")
    db.commit()
    ensure_admin(db)
    db.refresh(row)
    assert row.role=="admin"
    db.close()
    assert raw.post("/api/auth/login",json={"email":"admin@gmail.com","password":"admin1234"}).status_code==200

def test_old_users_table_gets_role_column(tmp_path,monkeypatch):
    old=create_engine(f"sqlite:///{tmp_path}/old2.db")
    with old.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR(255), name VARCHAR(120), password_hash VARCHAR(200), google_sub VARCHAR(64), created_at DATETIME)"))
        conn.execute(text("INSERT INTO users (id,email,name) VALUES (1,'a@b.co','A')"))
    monkeypatch.setattr(dbmod,"engine",old)
    dbmod.init_db()
    with old.begin() as conn:
        assert conn.execute(text("SELECT role FROM users")).scalar()=="user"

def test_trusted_publisher_matching():
    assert trusted.name_of("https://www.reuters.com/markets/x")=="Reuters"
    assert trusted.name_of("https://uk.finance.yahoo.com/news/x")=="Yahoo Finance"
    assert trusted.name_of("https://reuters.com.evil.example/x") is None
    assert trusted.name_of("https://randomblog.example/post") is None

def test_deep_crawl_keeps_only_trusted_and_dedupes(raw,monkeypatch):
    def entry(title,href):
        return {"title":title,"link":"https://news.google.com/rss/articles/"+title.replace(" ","_"),"summary":"","source":{"title":"x","href":href}}
    def fake_status(url):
        if "site%3Areuters" in url:
            return [entry("Nifty climbs as banks rally - Reuters","https://www.reuters.com"),entry("Spam coin to the moon","https://spam.example"),entry("Nifty climbs as banks rally - Reuters","https://www.reuters.com")],None
        if "site%3Acnbc" in url:
            return [],"HTTP 429"
        return [],"HTTP 500"
    monkeypatch.setattr(ingest,"fetch_feed_status",fake_status)
    monkeypatch.setattr(crawl,"fetch_gdelt",lambda j:([{"title":"Wall Street rallies on tech","link":"https://www.cnbc.com/a","summary":"","published_parsed":crawl.seen_to_struct("20261109T120000Z"),"source":{"title":"CNBC","href":"https://www.cnbc.com/a"}}],None))
    monkeypatch.setattr(crawl.time,"sleep",lambda s:None)
    db=sessionlocal()
    before=db.query(article).count()
    new=crawl.run_deep_crawl(db)
    titles=[a.title for a in db.query(article).all()]
    assert "Spam coin to the moon" not in titles
    assert titles.count("Nifty climbs as banks rally")==1
    assert "Wall Street rallies on tech" in titles
    assert new==db.query(article).count()-before>=2
    from app.models import feedstat
    rows={r.url:r for r in db.query(feedstat).all()}
    assert rows["crawl:google-sites:IN"].last_new>=1
    assert rows["crawl:gdelt:IN"].last_new>=1 and rows["crawl:gdelt:US"].last_count>=1
    assert "failed" in (rows["crawl:google-sectors:IN"].last_error or "")
    db.close()

def test_bulk_save_survives_duplicates(raw):
    db=sessionlocal()
    a=ingest.parse_entry("X",{"title":"Alpha story","link":"https://x.test/a","summary":"s"},"IN")
    b=ingest.parse_entry("X",{"title":"Beta story","link":"https://x.test/b","summary":"s"},"IN")
    assert ingest.save_items(db,[a,b])==2
    assert ingest.save_items(db,[a,ingest.parse_entry("X",{"title":"Gamma story","link":"https://x.test/c","summary":"s"},"IN")])==1
    assert ingest.new_items(db,[a,b],set())==[]
    db.close()

def test_process_pending_handles_many_in_batches(raw):
    db=sessionlocal()
    now=datetime.now(timezone.utc)
    items=[]
    for i in range(150):
        it=ingest.parse_entry("Bulk",{"title":f"Stocks rally number {i}","link":f"https://bulk.test/{i}","summary":""},"IN")
        it["published_at"]=now-timedelta(minutes=i)
        items.append(it)
    ingest.save_items(db,items)
    assert pipeline.process_pending(db,batch=40)==150
    assert pipeline.process_pending(db)==0
    db.close()

def test_retention_removes_old_articles_and_children(raw):
    db=sessionlocal()
    old=ingest.parse_entry("Old",{"title":"Ancient TCS story","link":"https://old.test/1","summary":"TCS rallies strongly on record gains"},"IN")
    old["published_at"]=datetime.now(timezone.utc)-timedelta(days=45)
    ingest.save_items(db,[old])
    pipeline.process_pending(db)
    from app.models import ticker,sentiment
    before=(db.query(article).count(),db.query(sentiment).count(),db.query(ticker).count())
    assert pipeline.purge_old(db,30)==1
    after=(db.query(article).count(),db.query(sentiment).count(),db.query(ticker).count())
    assert after[0]==before[0]-1 and after[1]==before[1]-1 and after[2]<before[2]
    db.close()
