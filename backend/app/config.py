import os
from dotenv import load_dotenv

load_dotenv()

def flag(name,default):
    return os.getenv(name,default).strip().lower() in ("1","true","yes","on")

database_url=os.getenv("DATABASE_URL","postgresql+psycopg2://pulse:pulse@localhost:5433/pulse")
redis_url=os.getenv("REDIS_URL","redis://localhost:6380/0")
fetch_interval_minutes=int(os.getenv("FETCH_INTERVAL_MINUTES","5"))
use_finbert=flag("USE_FINBERT","true")
finbert_model=os.getenv("FINBERT_MODEL","ProsusAI/finbert")
spacy_model=os.getenv("SPACY_MODEL","en_core_web_sm")
fetch_full_text=flag("FETCH_FULL_TEXT","true")
max_scrape_per_run=int(os.getenv("MAX_SCRAPE_PER_RUN","40"))
http_timeout=int(os.getenv("HTTP_TIMEOUT","10"))
quote_timeout=int(os.getenv("QUOTE_TIMEOUT","6"))
max_quotes=int(os.getenv("MAX_QUOTES","150"))
quote_top=int(os.getenv("QUOTE_TOP","100"))
quote_rolling=int(os.getenv("QUOTE_ROLLING","60"))
us_bulk_quotes=flag("US_BULK_QUOTES","true")
quote_interval_seconds=int(os.getenv("QUOTE_INTERVAL_SECONDS","60"))
closed_refresh_minutes=int(os.getenv("CLOSED_REFRESH_MINUTES","30"))
max_entries_per_feed=int(os.getenv("MAX_ENTRIES_PER_FEED","300"))
user_agent=os.getenv("USER_AGENT","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
cors_origins=[o.strip() for o in os.getenv("CORS_ORIGINS","http://localhost:5173").split(",") if o.strip()]

default_secret="dev-only-change-me"
secret_key=os.getenv("SECRET_KEY",default_secret)
google_client_id=os.getenv("GOOGLE_CLIENT_ID","").strip()
cookie_secure=flag("COOKIE_SECURE","false")
session_days=int(os.getenv("SESSION_DAYS","7"))

def feed(source,market,url,**extra):
    return {"source":source,"market":market,"url":url,**extra}

gnews_in="https://news.google.com/rss/search?q=sensex+OR+nifty+OR+%22indian+stocks%22+when:1d&hl=en-IN&gl=IN&ceid=IN:en"
gnews_us="https://news.google.com/rss/search?q=%22stock+market%22+OR+nasdaq+OR+%22wall+street%22+when:1d&hl=en-US&gl=US&ceid=US:en"

deep_crawl=flag("DEEP_CRAWL","true")
crawl_interval_minutes=int(os.getenv("CRAWL_INTERVAL_MINUTES","15"))
crawl_budget_seconds=int(os.getenv("CRAWL_BUDGET_SECONDS","240"))
crawl_workers=int(os.getenv("CRAWL_WORKERS","6"))
crawl_company_batch=int(os.getenv("CRAWL_COMPANY_BATCH","30"))
gdelt_delay_seconds=float(os.getenv("GDELT_DELAY_SECONDS","5"))
score_budget_seconds=int(os.getenv("SCORE_BUDGET_SECONDS","240"))
retention_days=int(os.getenv("RETENTION_DAYS","30"))
unrelated_days=int(os.getenv("UNRELATED_DAYS","2"))
sync_instruments=flag("SYNC_INSTRUMENTS","true")
remote_search=flag("REMOTE_SEARCH","true")
user_refresh_cooldown=int(os.getenv("USER_REFRESH_COOLDOWN","60"))

admin_email=os.getenv("ADMIN_EMAIL","admin@gmail.com").strip().lower()
admin_name=os.getenv("ADMIN_NAME","admin")
admin_password=os.getenv("ADMIN_PASSWORD","admin1234")

feeds=[
    feed("Economic Times","IN","https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"),
    feed("Economic Times","IN","https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"),
    feed("Moneycontrol","IN","https://www.moneycontrol.com/rss/marketreports.xml"),
    feed("Moneycontrol","IN","https://www.moneycontrol.com/rss/business.xml"),
    feed("LiveMint","IN","https://www.livemint.com/rss/markets"),
    feed("LiveMint","IN","https://www.livemint.com/rss/companies"),
    feed("Business Standard","IN","https://www.business-standard.com/rss/markets-106.rss"),
    feed("Business Standard","IN","https://www.business-standard.com/rss/companies-101.rss"),
    feed("Financial Express","IN","https://www.financialexpress.com/market/feed/"),
    feed("BusinessLine","IN","https://www.thehindubusinessline.com/markets/feeder/default.rss"),
    feed("Hindustan Times","IN","https://www.hindustantimes.com/feeds/rss/business/rssfeed.xml"),
    feed("Times of India","IN","https://timesofindia.indiatimes.com/rssfeeds/1898055.cms"),
    feed("Google News","IN",gnews_in,kind="google",scrape=False),
    feed("CNBC","US","https://www.cnbc.com/id/15839069/device/rss/rss.html"),
    feed("CNBC","US","https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    feed("MarketWatch","US","https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines"),
    feed("Yahoo Finance","US","https://finance.yahoo.com/news/rssindex"),
    feed("Nasdaq","US","https://www.nasdaq.com/feed/rssoutbound?category=Markets"),
    feed("Seeking Alpha","US","https://seekingalpha.com/market_currents.xml"),
    feed("Investing.com","US","https://www.investing.com/rss/news_25.rss"),
    feed("Google News","US",gnews_us,kind="google",scrape=False),
]

def feeds_for(source):
    return [f for f in feeds if f["source"]==source]
