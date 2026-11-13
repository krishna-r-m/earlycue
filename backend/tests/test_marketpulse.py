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
    assert [i["symbol"] for i in us["items"]][:1]==["NVDA"]
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
    assert {i["symbol"] for i in india["items"][:3]}=={"TCS","HDFCBANK","ICICIBANK"}
    bank=client.get("/api/movers",params={"market":"IN","by":"price","sector":"Banking"}).json()
    assert [i["symbol"] for i in bank["items"]][:2]==["HDFCBANK","ICICIBANK"]
    assert bank["sector"]=="Banking" and all(i["sector"]=="Banking" for i in bank["items"])
    us=client.get("/api/movers",params={"market":"US","by":"price","sector":"Banking"}).json()
    assert [i["symbol"] for i in us["items"]][:1]==["JPM"]

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

@pytest.fixture()
def clean_registry():
    from app import tickers as tk
    yield tk
    tk.register_instruments([])

def fake_nse(n=120):
    head="SYMBOL,NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE\n"
    rows=["JIOPLATFORMS,Jio Platforms Limited,EQ,01-JAN-2026,10,1,INE000000001,10"]
    rows+= [f"SYM{i},Synthetic Company {i} Limited,EQ,01-JAN-2020,10,1,INE00000{i:04},10" for i in range(n)]
    rows.append("BONDX,Some Bond Limited,N1,01-JAN-2020,10,1,INE000000002,10")
    return head+"\n".join(rows)+"\n"

def fake_nasdaq(n=120):
    head="Symbol|Security Name|Market Category|Test Issue|Financial Status|Round Lot Size|ETF|NextShares\n"
    rows=["ZENQ|Zenith Quantum Holdings Inc. - Common Stock|Q|N|N|100|N|N","SPYX|Some ETF|Q|N|N|100|Y|N","TSTX|Test Co|Q|Y|N|100|N|N","WARX|Foo Corp - Warrant|Q|N|N|100|N|N"]
    rows+=[f"NQ{i}|Nasdaq Co {i} Inc. - Common Stock|Q|N|N|100|N|N" for i in range(n)]
    return head+"\n".join(rows)+"\nFile Creation Time: 1109202612:00|||||||\n"

def fake_other(n=10):
    head="ACT Symbol|Security Name|Exchange|CQS Symbol|ETF|Round Lot Size|Test Issue|NASDAQ Symbol\n"
    rows=["BRK.B|Berkshire Hathaway Inc. - Class B|N|BRK.B|N|100|N|BRK.B","BAC$B|BofA Preferred|N|BAC-B|N|100|N|BAC$B"]
    return head+"\n".join(rows)+"\nFile Creation Time: 1109202612:00|||||||\n"

def test_instrument_parsers_filter_junk():
    from app import instruments
    nse=instruments.parse_nse(fake_nse())
    assert ("JIOPLATFORMS","Jio Platforms Limited","IN","NSE") in nse
    assert all(r[0]!="BONDX" for r in nse)
    us=instruments.parse_trader(fake_nasdaq(),"Symbol","NASDAQ")+instruments.parse_trader(fake_other(),"ACT Symbol","NYSE")
    syms={r[0] for r in us}
    assert "ZENQ" in syms and "BRK-B" in syms
    assert not syms&{"SPYX","TSTX","WARX","BAC$B"}
    assert ("ZENQ","Zenith Quantum Holdings Inc.","US","NASDAQ") in us

def test_sync_loads_every_listed_stock_into_search(raw,monkeypatch,clean_registry):
    from app import instruments
    monkeypatch.setattr(instruments,"get_text",lambda url,extra=None:fake_nse() if "EQUITY_L" in url else fake_nasdaq() if "nasdaqlisted" in url else fake_other())
    db=sessionlocal()
    assert instruments.sync(db)>200
    assert instruments.count(db)>200
    db.close()
    raw.post("/api/auth/register",json=creds)
    hits=raw.get("/api/tickers/search",params={"q":"jioplatforms","market":"IN"}).json()
    assert hits[0]["symbol"]=="JIOPLATFORMS" and hits[0]["market"]=="IN"
    assert raw.get("/api/tickers/search",params={"q":"jio platforms"}).json()[0]["symbol"]=="JIOPLATFORMS"
    assert raw.get("/api/tickers/search",params={"q":"zenith","market":"US"}).json()[0]["symbol"]=="ZENQ"
    assert raw.get("/api/tickers/search",params={"q":"zenith","market":"IN"}).json()==[]
    assert raw.get("/api/tickers/search",params={"q":"synthetic company 7","market":"IN"}).json()
    page=raw.get("/api/ticker/JIOPLATFORMS")
    assert page.status_code==200 and page.json()["name"]=="Jio Platforms Limited"

def test_failed_instrument_sync_keeps_existing_list(raw,monkeypatch,clean_registry):
    from app import instruments
    db=sessionlocal()
    monkeypatch.setattr(instruments,"get_text",lambda url,extra=None:fake_nse() if "EQUITY_L" in url else fake_nasdaq() if "nasdaqlisted" in url else fake_other())
    instruments.sync(db)
    n=instruments.count(db)
    def boom(url,extra=None):
        raise instruments.requests.RequestException("down")
    monkeypatch.setattr(instruments,"get_text",boom)
    instruments.sync(db)
    assert instruments.count(db)==n
    from app.models import feedstat
    assert "RequestException" in db.get(feedstat,"crawl:instruments:IN").last_error
    db.close()

def test_news_is_tagged_with_newly_listed_stocks(clean_registry):
    clean_registry.register_instruments([("JIOPLATFORMS","Jio Platforms Limited","IN"),("TARGETX","Target Corporation","US")])
    out=nlp.analyse_batch([("Jio Platforms IPO draws record bids as Target shares jump","","IN")])[0]
    assert {e["symbol"] for e in out["entities"]}=={"JIOPLATFORMS"}

def test_symbol_collisions_keep_the_curated_stock(clean_registry):
    added,skipped=clean_registry.register_instruments([("TCS","Some Other TCS Limited","IN"),("NEWCO","New Co Limited","IN")])
    assert (added,skipped)==(1,1)
    assert clean_registry.by_symbol["TCS"]["name"]=="Tata Consultancy Services"

def test_on_demand_price_for_listed_stock(raw,monkeypatch,clean_registry):
    clean_registry.register_instruments([("JIOPLATFORMS","Jio Platforms Limited","IN")])
    raw.post("/api/auth/register",json=creds)
    monkeypatch.setattr(quotes,"fetch_quote",lambda s:{"symbol":s,"price":321.5,"prev_close":300.0,"change_pct":7.17,"currency":"INR"})
    q=raw.get("/api/ticker/JIOPLATFORMS").json()["quote"]
    assert q["price"]==321.5 and q["change_pct"]==7.17

def test_regular_users_can_refresh_with_a_cooldown(client,monkeypatch):
    from app import main
    called=[]
    monkeypatch.setattr(main,"run_inline",lambda:called.append(1))
    main.refresh_state["at"]=0.0
    r=client.post("/api/refresh").json()
    assert r["queued"] is True and r["mode"]=="accepted" and "worker" not in r["detail"].lower()
    again=client.post("/api/refresh").json()
    assert again["queued"] is False and again["mode"]=="busy"
    assert called==[1]
    main.refresh_state["at"]=0.0

def test_unrelated_and_old_stories_are_removed_and_storage_slimmed(raw):
    from app.models import sentiment,ticker
    db=sessionlocal()
    now=datetime.now(timezone.utc)
    def story(title,link,age_days,summary="",raw_text=""):
        it=ingest.parse_entry("T",{"title":title,"link":link,"summary":summary},"IN")
        it["published_at"]=now-timedelta(days=age_days)
        return it
    items=[story("Sunny weather forecast for the weekend","https://t.test/w1",3),
           story("Cute cat video goes viral again","https://t.test/w2",1),
           story("TCS rallies on record deal wins","https://t.test/t1",3)]
    ingest.save_items(db,items,{items[2]["url_hash"]:"x"*5000})
    pipeline.process_pending(db)
    assert db.query(article).filter(article.title.like("TCS rallies%")).first().raw_content==""
    removed=pipeline.purge_old(db,30,2)
    titles={a.title for a in db.query(article).all()}
    assert "Sunny weather forecast for the weekend" not in titles
    assert "Cute cat video goes viral again" in titles
    assert "TCS rallies on record deal wins" in titles
    assert removed==1
    db.close()


def fake_nifty():
    return "Company Name,Industry,Symbol,Series,ISIN Code\nZen Pharma Ltd,Healthcare,SYM3,EQ,INE1\nBig Bank Ltd,Financial Services,SYM4,EQ,INE2\n"

def fake_screener():
    import json
    rows=[{"symbol":"NQ1","name":"Nasdaq Co 1","lastsale":"$12.50","pctchange":"2.5%","marketCap":"5,000,000","sector":"Health Care","industry":"Biotech"},
          {"symbol":"NQ2","name":"Nasdaq Co 2","lastsale":"$50.00","pctchange":"-4.0%","marketCap":"9,000,000","sector":"Technology","industry":"Software"},
          {"symbol":"ZENQ","name":"Zenith","lastsale":"$9.00","pctchange":"1.0%","marketCap":"1,000","sector":"Finance","industry":"Banks"}]
    return json.dumps({"data":{"rows":rows}})

def fake_source(url,extra=None):
    if "EQUITY_L" in url: return fake_nse()
    if "nifty" in url: return fake_nifty()
    if "nasdaqlisted" in url: return fake_nasdaq()
    if "otherlisted" in url: return fake_other()
    if "screener" in url: return fake_screener()
    raise instruments_mod.requests.RequestException("unexpected "+url)

from app import instruments as instruments_mod

def test_sector_and_rank_data_is_stored_for_every_stock(raw,monkeypatch,clean_registry):
    monkeypatch.setattr(instruments_mod,"get_text",fake_source)
    instruments_mod.state["screener"]=None
    db=sessionlocal()
    instruments_mod.sync(db)
    from app.models import instrument
    rows={r.symbol:r for r in db.query(instrument).all()}
    assert rows["SYM3"].sector=="Pharma" and rows["SYM4"].sector=="Banking" and rows["SYM3"].rank==0
    assert rows["SYM9"].sector=="General" and rows["JIOPLATFORMS"].sector=="General"
    assert rows["NQ1"].sector=="Pharma" and rows["NQ2"].sector=="IT" and rows["ZENQ"].sector=="Banking"
    assert rows["NQ2"].rank<rows["NQ1"].rank
    db.close()

def test_sidebar_lists_every_stock_of_a_sector_even_without_news_or_prices(raw,monkeypatch,clean_registry):
    monkeypatch.setattr(instruments_mod,"get_text",fake_source)
    instruments_mod.state["screener"]=None
    db=sessionlocal()
    instruments_mod.sync(db)
    db.close()
    raw.post("/api/auth/register",json=creds)
    pharma=raw.get("/api/movers",params={"market":"IN","by":"price","sector":"Pharma","limit":100}).json()
    syms=[i["symbol"] for i in pharma["items"]]
    assert "SYM3" in syms and "SUNPHARMA" in syms and pharma["total"]==len(syms)
    assert all(i["price"] is None for i in pharma["items"])
    assert syms.index("SUNPHARMA")<syms.index("SYM3")
    page1=raw.get("/api/movers",params={"market":"IN","by":"sentiment","limit":5}).json()
    page2=raw.get("/api/movers",params={"market":"IN","by":"sentiment","limit":5,"offset":5}).json()
    assert len(page1["items"])==5 and len(page2["items"])==5
    assert not {i["symbol"] for i in page1["items"]}&{i["symbol"] for i in page2["items"]}
    assert page1["total"]>100
    us=raw.get("/api/movers",params={"market":"US","sector":"IT","limit":100}).json()
    assert "NQ2" in [i["symbol"] for i in us["items"]]
    assert "SYM3" not in [i["symbol"] for i in us["items"]]

def test_bulk_prices_cover_every_stock_and_never_overwrite_fresher_live_prices(raw,monkeypatch,clean_registry):
    monkeypatch.setattr(instruments_mod,"get_text",fake_source)
    instruments_mod.state["screener"]=None
    db=sessionlocal()
    instruments_mod.sync(db)
    now=datetime(2026,11,9,15,0,tzinfo=timezone.utc)
    db.add(pricequote(symbol="NQ1",market="US",price=99.0,prev_close=90.0,change_pct=10.0,currency="USD",updated_at=now-timedelta(minutes=1)))
    db.commit()
    rows=instruments_mod.us_price_rows(now)
    assert {r[0] for r in rows}=={"NQ1","NQ2","ZENQ"}
    changed=quotes.bulk_upsert(db,rows)
    assert changed==2
    assert db.get(pricequote,"NQ1").price==99.0
    assert db.get(pricequote,"NQ2").price==50.0 and db.get(pricequote,"NQ2").change_pct==-4.0
    db.close()
    raw.post("/api/auth/register",json=creds)
    us=raw.get("/api/movers",params={"market":"US","by":"price","limit":3}).json()
    assert [i["symbol"] for i in us["items"]][0]=="NQ1"

def test_india_end_of_day_prices_use_the_latest_trading_day(monkeypatch):
    calls=[]
    def fake(url,extra=None):
        calls.append(url)
        if len(calls)<3:
            raise instruments_mod.requests.RequestException("404")
        return "SYMBOL, SERIES, PREV_CLOSE, CLOSE_PRICE\nTCS, EQ, 100, 103\nJUNK, XX, 1, 2\n"
    monkeypatch.setattr(instruments_mod,"get_text",fake)
    rows=instruments_mod.in_price_rows()
    assert rows and rows[0][0]=="TCS" and rows[0][3]==3.0 and rows[0][4]=="INR"
    assert rows[0][5].hour in (9,10)

def test_search_finds_stocks_missing_from_the_lists_and_remembers_them(raw,monkeypatch,clean_registry):
    from app import config
    raw.post("/api/auth/register",json=creds)
    monkeypatch.setattr(config,"remote_search",True)
    monkeypatch.setattr(instruments_mod,"yahoo_search",lambda q,m=None:[("JIOPLATFORMS","Jio Platforms Limited","IN","REMOTE-NSE")])
    hits=raw.get("/api/tickers/search",params={"q":"jioplatforms","market":"IN"}).json()
    assert hits and hits[0]["symbol"]=="JIOPLATFORMS"
    monkeypatch.setattr(instruments_mod,"yahoo_search",lambda q,m=None:(_ for _ in ()).throw(AssertionError("should be remembered")))
    assert raw.get("/api/tickers/search",params={"q":"jioplatforms","market":"IN"}).json()[0]["symbol"]=="JIOPLATFORMS"
    assert raw.get("/api/ticker/JIOPLATFORMS").status_code==200

def test_yahoo_search_parsing(monkeypatch):
    class res:
        def raise_for_status(self):pass
        def json(self):
            return {"quotes":[{"symbol":"JIOFIN.NS","quoteType":"EQUITY","exchange":"NSI","longname":"Jio Financial Services Limited"},{"symbol":"500209.BO","quoteType":"EQUITY","exchange":"BSE","shortname":"INFOSYS"},{"symbol":"AAPL","quoteType":"EQUITY","exchange":"NMS","shortname":"Apple"},{"symbol":"SPY","quoteType":"ETF","exchange":"PCX"}]}
    monkeypatch.setattr(instruments_mod.requests,"get",lambda *a,**k:res())
    out=instruments_mod.yahoo_search("jio")
    assert ("JIOFIN","Jio Financial Services Limited","IN","REMOTE-NSE") in out
    assert any(r[0]=="500209.BO" for r in out) and any(r[0]=="AAPL" for r in out)
    assert not any(r[0]=="SPY" for r in out)
    assert [r[2] for r in instruments_mod.yahoo_search("jio","US")]==["US"]

def test_health_shows_stock_count_and_cleanup_is_admin_only(raw,admin,client,monkeypatch,clean_registry):
    monkeypatch.setattr(instruments_mod,"get_text",fake_source)
    instruments_mod.state["screener"]=None
    db=sessionlocal()
    instruments_mod.sync(db)
    db.close()
    assert client.get("/api/health").json()["stocks"]>200
    assert client.post("/api/admin/cleanup").status_code==403
    r=admin.post("/api/admin/cleanup").json()
    assert r["removed"]==0 and r["articles"]==5

def test_large_responses_are_gzip_compressed(client):
    r=client.get("/api/movers",params={"market":"IN","limit":100},headers={"Accept-Encoding":"gzip"})
    assert r.status_code==200 and r.headers.get("content-encoding")=="gzip"
    assert len(r.json()["items"])>20

def test_short_cache_serves_repeat_requests_and_can_be_cleared(client,monkeypatch):
    from app import main,config
    monkeypatch.setattr(config,"cache_seconds",30)
    main.cache_clear()
    first=client.get("/api/health").json()["articles"]
    db=sessionlocal()
    db.add(article(**ingest.parse_entry("T",{"title":"Fresh cached story","link":"https://t.test/fresh","summary":"s"},"IN")))
    db.commit()
    db.close()
    assert client.get("/api/health").json()["articles"]==first
    main.cache_clear()
    assert client.get("/api/health").json()["articles"]==first+1
    main.cache_clear()

def test_stock_universe_is_cached_but_refreshes_when_the_list_changes(clean_registry):
    before=len(clean_registry.universe("IN"))
    assert clean_registry.universe("IN") is clean_registry.universe("IN")
    clean_registry.register_instruments([("NEWLISTED","New Listed Limited","IN","Banking",1)])
    assert len(clean_registry.universe("IN"))==before+1
    assert "NEWLISTED" in clean_registry.universe("IN","Banking")

def test_google_profile_photo_is_stored(raw,monkeypatch):
    from google.oauth2 import id_token
    info={"sub":"g-pic","email":"pic@example.com","email_verified":True,"name":"Pic","picture":"https://lh3.googleusercontent.com/a/photo"}
    monkeypatch.setattr(id_token,"verify_oauth2_token",lambda cred,req,aud:info)
    r=raw.post("/api/auth/google",json={"credential":"x"})
    assert r.json()["picture"]=="https://lh3.googleusercontent.com/a/photo"
    assert raw.get("/api/auth/me").json()["picture"].endswith("/photo")
    raw.post("/api/auth/register",json=creds)
    assert raw.get("/api/auth/me").json()["picture"] is None

def test_composite_article_index_exists(raw):
    from sqlalchemy import inspect
    names={i["name"] for i in inspect(engine).get_indexes("articles")}
    assert "ix_articles_market_pub" in names

def fake_chart(closes,prev=None,currency="USD"):
    class res:
        def raise_for_status(self):pass
        def json(self):
            stamps=[1700000000+i*86400 for i in range(len(closes))]
            meta={"currency":currency}
            if prev is not None:
                meta["chartPreviousClose"]=prev
            return {"chart":{"result":[{"timestamp":stamps,"meta":meta,"indicators":{"quote":[{"close":closes}]}}]}}
    return lambda *a,**k:res()

def test_price_history_for_any_stock(client,monkeypatch):
    monkeypatch.setattr(quotes.requests,"get",fake_chart([100.0,None,110.0,121.0]))
    h=client.get("/api/history/AAPL",params={"range":"1M"}).json()
    assert h["available"] and len(h["points"])==3 and h["last"]==121.0
    assert h["change_pct"]==21.0 and h["currency"]=="USD"
    monkeypatch.setattr(quotes.requests,"get",fake_chart([105.0,110.0],prev=100.0))
    day=client.get("/api/history/AAPL",params={"range":"1d"}).json()
    assert day["range"]=="1D" and day["change_pct"]==10.0

def test_price_history_degrades_gracefully_and_validates(client,monkeypatch):
    def down(*a,**k):
        raise quotes.requests.RequestException("down")
    monkeypatch.setattr(quotes.requests,"get",down)
    h=client.get("/api/history/AAPL").json()
    assert h["available"] is False and h["points"]==[]
    assert client.get("/api/history/AAPL",params={"range":"2Y"}).status_code==422
    assert client.get("/api/history/NOTASTOCK").status_code==404
    assert client.get("/api/history/sector/Nope").status_code==422

def test_history_requires_login(raw):
    assert raw.get("/api/history/AAPL").status_code==401
    assert raw.get("/api/history/sector/Banking").status_code==401

def test_nifty_index_history_for_the_market_graph(client,monkeypatch):
    monkeypatch.setattr(quotes.requests,"get",fake_chart([22000.0,22110.0],currency="INR"))
    h=client.get("/api/history/NIFTY",params={"range":"1W"}).json()
    assert h["available"] and h["currency"]=="INR"

def test_sector_price_index_is_an_equal_weight_basket_starting_at_100(client,monkeypatch):
    series={"HDFCBANK":[100.0,110.0,121.0],"ICICIBANK":[50.0,50.0,60.0]}
    def fake(symbol,rng):
        if symbol in series:
            return {"currency":"INR","prev_close":None,"points":[(1700000000+i*86400,c) for i,c in enumerate(series[symbol])]}
        return None
    monkeypatch.setattr(quotes,"fetch_history",fake)
    h=client.get("/api/history/sector/Banking",params={"market":"IN","range":"1M"}).json()
    assert set(h["basket"])=={"HDFCBANK","ICICIBANK"}
    assert [p["c"] for p in h["points"]]==[100.0,105.0,120.5]
    assert h["change_pct"]==20.5

def test_front_page_is_public_and_shows_real_sentiment_and_top_stories(raw):
    r=raw.get("/api/public/front-page")
    assert r.status_code==200
    m=r.json()["markets"]
    assert m["IN"]["overall"]["total"]==2 and m["US"]["overall"]["total"]==2
    assert 1<=len(m["IN"]["stories"])<=3
    titles={s["title"] for s in m["IN"]["stories"]}
    assert not any("RBI keeps repo rate" in t for t in titles)
    assert {s["source"] for s in m["US"]["stories"]}=={"CNBC","MarketWatch"}
    assert all(s["sentiment"] in ("Bullish","Bearish","Neutral") and s["url"].startswith("https://") for s in m["US"]["stories"])
