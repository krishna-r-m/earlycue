# earlycue

Market news, sentiment and live prices for India and the US. A Celery worker reads news feeds every 5 minutes and runs a deep crawl across trusted publishers every 15 minutes, then scores each headline with FinBERT. The API refreshes prices every minute while a market is open. A React dashboard shows it all behind a login.

Written for Windows 10 and 11. Commands are PowerShell.

## What it does

- **India and US toggle.** Everything switches together: sentiment, sectors, trend, news, search and the movers sidebar. India stocks only ever show on the India side and US stocks on the US side. News is tagged with companies from its own market only.
- **Sector click.** Click a sector card and the page focuses on it: the trend chart switches to that sector, "stocks in the news" and the Most changed sidebar show only that sector's stocks, and the news list shows only that sector's stories. Every story has a Bullish, Bearish or Neutral tag with its confidence, and the news header shows the sector's overall lean.
- **Live prices.** While a market is open, prices refresh every minute and the dashboard picks them up within about 15 seconds. Changed prices flash green or red. Outside market hours it shows the last close and checks every 30 minutes.
- **Thousands of stories.** Direct feeds plus a deep crawl that searches by trusted publisher, by sector, by company and through GDELT. Only articles from a list of trusted publishers are kept. See "News sources" below.
- **Admin and regular users.** Regular users see a clean newspaper-style dashboard with plain-language status messages. The admin also sees queue and worker status, the Refresh button, feed and crawl health, counts, and the user list.
- **Login.** Email and password, or Google. Sessions use an httpOnly cookie and passwords are hashed with bcrypt.
- **Home link.** The logo and name in the header take you back to the overview.
- **Light and dark themes.** Dark mode is a neutral dark grey (not black, not blue) with at least 5:1 text contrast.
- **Every listed stock.** The full NSE and Nasdaq Trader lists (several thousand India and US stocks) load into the database and search. Search ignores spaces, so "jioplatforms" finds "Jio Platforms Limited". Any listed stock has a page with a live price.
- **Refresh for everyone.** Any signed-in user can press Refresh (one run per minute, with a plain-language message). Only the admin sees queue details and the deep crawl button.
- **Lean storage.** Stories older than 30 days, and stories with no market link older than 2 days, are deleted automatically. Page text is dropped as soon as a story is scored.
- **Quiet newspaper styling.** Serif headlines, ruled columns, a dateline under the masthead, and one highlighter-yellow accent.

## News sources and the deep crawl

Two layers feed the database:

1. **Direct feeds** (every 5 minutes): 13 Indian and 8 US feeds, up to 300 stories each.
2. **Deep crawl** (every 15 minutes, 135 requests, at most 4 minutes): Google News searches for each of about 50 trusted publishers, for each sector, and for a rotating batch of 30 companies per run (so every company is covered within a few runs), Yahoo Finance headlines for the same companies, and GDELT global news queries for each market.

Aggregated results are kept only if the publisher is on the trusted list in `backend\app\trusted.py` (Reuters, Bloomberg, Financial Times, WSJ, CNBC, MarketWatch, Barron's, Economic Times, Moneycontrol, LiveMint, Business Standard, Financial Express, BusinessLine, The Hindu, Hindustan Times, Times of India, Indian Express, NDTV Profit, Nasdaq, Seeking Alpha, Motley Fool, Forbes, Fortune, AP, BBC, Guardian, New York Times and others). Add or remove domains there. Articles are de-duplicated by link and by headline, scored in batches, and removed after 30 days (`RETENTION_DAYS`, plus `UNRELATED_DAYS` for stories with no market link).

How many stories you get depends on what those sites return when you run it. I could not reach them from where I built this, so I cannot promise a number. Check from your machine:

```powershell
cd backend
.venv\Scripts\Activate.ps1
python -m scripts.check_feeds     # status of every direct feed
python -m scripts.crawl_once      # runs one deep crawl and prints entries and new stories per group
```

The first crawl of a fresh database is the biggest. After that most results are duplicates, so "new" per run is smaller. The admin console shows the same numbers live. Scoring thousands of headlines with FinBERT on a CPU takes a few minutes per batch, and the dashboard fills in as scoring proceeds.

Prices come from Yahoo Finance's free chart endpoint (NSE symbols for India). It is unofficial and can rate-limit or change. If it refuses requests, earlycue backs off for up to 5 minutes and keeps showing the last prices. Yahoo's data can lag by up to 15 minutes. Market hours: Monday to Friday, 9:15 to 15:30 IST for India and 9:30 to 16:00 ET for the US. Exchange holidays are not modelled.

## Every listed stock

**Where the list comes from.** On first start (and weekly after that) earlycue downloads the official lists: NSE's equity list for India, and Nasdaq Trader's two lists (Nasdaq plus NYSE and other exchanges) for the US. ETFs, test issues, warrants and preferred shares are skipped. The result is every listed company, several thousand per market, in the database.

**Sectors for all of them.** India uses NSE's Nifty 500 and Microcap 250 industry lists, and the US uses the Nasdaq screener's sector field. Anything not on those (mostly small Indian companies) is filed by keywords in its company name, and stays under General if nothing matches. Sectors map onto earlycue's ten (Banking, IT, Auto, Energy, Pharma, FMCG, Metals, Telecom, Infrastructure, Macroeconomics).

**Prices for all of them, in tiers.**

| Tier | Stocks | Source | Freshness |
| --- | --- | --- | --- |
| Live | indices, the most mentioned stocks, the main large caps (about 150) | Yahoo Finance chart endpoint | every minute while the market is open |
| All US stocks | every listed US stock | Nasdaq screener, one request | every 5 minutes while open, every 3 hours otherwise |
| All Indian stocks | every NSE stock | NSE end-of-day file (`sec_bhavdata_full`) | after each trading day |
| On demand | any stock you open | Yahoo Finance | when you open its page, if older than 2 minutes |

A newer live price is never overwritten by a bulk one.

**In the sidebar and search.** Every stock appears in search, and in the sidebar even with no news. Click a sector and the sidebar lists that sector's stocks: those with price data first, ranked by move, then the rest, largest first. "Show more" loads up to 100 at a time, and search finds the rest. Stocks without news show "No news" instead of a sentiment.

**Stocks that are not on the lists.** If a search finds fewer than 3 matches, earlycue asks Yahoo Finance's search for NSE, BSE and US listings, adds what it finds to the database, and remembers it. That is how newly listed companies, BSE-only companies and anything missing from the weekly lists become searchable.

**Limits.**

- If a company such as Jio Platforms is not listed on an exchange yet, it will not be found anywhere. It appears once the NSE list or Yahoo includes it.
- If the same ticker exists in both markets, the curated or first-loaded one wins.
- I could not reach NSE, Nasdaq or Yahoo from where I built this, so the downloads are tested against sample files only. Sign in as admin and open the Admin console: the "Listed stocks (NSE)" and "Listed stocks (Nasdaq Trader)" rows show whether each download worked and how many stocks it found.

## Storage cleanup

- Stories older than 30 days (`RETENTION_DAYS`) are deleted.
- Stories with no company, sector keyword or market term, older than 2 days (`UNRELATED_DAYS`), are deleted.
- Page text is dropped as soon as a story is scored.
- Cleanup runs with every news refresh. The admin can also run it from the Admin console ("Clean up storage") and sees how many stories were removed.

## Charts: sentiment and price

Every chart can show sentiment or the actual price:

- **Stock pages (every listed stock):** a Sentiment / Price toggle. If a stock has no news sentiment yet, only the price shows. If price history can't be loaded, only sentiment shows. The toggle appears when both exist. Price ranges: 1D, 1W, 1M, 3M, 1Y, with the last price and the change over the range.
- **Market graph:** sentiment for the market, or the market index (Nifty 50 for India, S&P 500 for the US). The default price range follows the time window you picked.
- **Sector graph:** sentiment for the sector, or a sector price index. There is no official index for each of earlycue's sectors, so this is an equal-weighted index of the sector's 8 largest stocks, starting at 100, and the stocks used are listed under the chart.

Price history comes from Yahoo Finance's free chart endpoint and is cached for 1 to 30 minutes depending on the range. I could not reach Yahoo from where I built this, so the price charts are tested against sample data only.

The overall market sentiment on the main page sits in a framed box.

## Looks and the profile menu

Click the round profile picture in the top corner (your Google photo if you signed in with Google, your initials otherwise, a person icon when signed out). The menu holds:

- **Colour:** light or dark.
- **Layout:** Newspaper (default) or Original. Newspaper uses a greyer palette in both colour modes and lays the dashboard out as articles divided by column rules, with banner section headings and justified text. Original is the earlier look.
- **Text size:** small, medium or large.
- **Animations:** on or off. The default is off on devices that look slow (two or fewer CPU cores, 2 GB or less memory) or that ask for reduced motion.
- **Market:** India or US.
- **Actions:** back to the overview, refresh data, the admin console (admin only), sign out. Signed-out visitors see Sign in and Create an account instead.

All choices are saved in the browser. Animations only use fades and slides, which are cheap for the browser, plus a smooth accordion on the landing page, scroll reveals, and a slow publisher ticker. Turning animations off disables all of them.

## Performance

- Pages are split into separate downloads. A visitor to the landing page does not download the dashboard, and the chart library (the largest piece, about 110 KB compressed) only loads when a chart is shown. The main bundle is about 48 KB compressed.
- The API compresses large responses (gzip), keeps short-lived caches (15 seconds, `CACHE_SECONDS`) for the busiest endpoints, remembers the sorted stock list per market and sector, and has extra database indexes for the common queries.
- The browser deduplicates identical requests that happen at the same moment, pauses its polling while the tab is hidden, and fetches fonts with fewer weights.
- Loading states use lightweight placeholders instead of spinners.

## Landing page

Signed-out visitors see a front-page style landing page with a publisher ticker, the real overall sentiment for India and the US (switchable) and today's top 3 stories, live counts, an "Inside this edition" index and smooth animated sections. It explains what earlycue does, how it works step by step, what you can do, where the news comes from, how to read the numbers, what to be careful about, and common questions, with live counts of stocks and stories. Sign in and Create an account lead to the login screen. Clicking the logo returns to the landing page when signed out and to the overview when signed in.

## Accounts: admin and users

On first start earlycue creates one admin account:

| Email | Name | Password |
| --- | --- | --- |
| admin@gmail.com | admin | admin1234 |

Everyone else who registers is a regular user. Change the admin details with `ADMIN_EMAIL`, `ADMIN_NAME` and `ADMIN_PASSWORD` in `backend\.env` (or the root `.env` for Docker). These defaults are public in this README, so change the password before anyone else can reach the app. Notes:

- If a regular account already exists with the admin email, it is promoted to admin on startup and its password is reset to the configured one.
- The admin account cannot sign in with Google, and Google sign-in can never link to it. `admin@gmail.com` is a real Gmail address that someone else may own, so this stops them taking over the admin account.
- Regular users get HTTP 403 from every admin endpoint, not just a hidden button.

## Architecture

```
direct feeds + deep crawl (crawl.py: trusted publishers via Google News, Yahoo, GDELT)
           -> ingest.py (feedparser, page scraping, bulk dedupe, per-feed health)
           -> pipeline.py -> nlp.py (FinBERT, spaCy + company list, sector tagging, market-aware)
PostgreSQL (articles, sentiments, tickers, quotes, feedstats, users)
FastAPI (/api/*, cookie auth, admin role) -> live price loop (60s) -> React + Tailwind + Recharts
Celery beat runs app.tasks.refresh_news every 5 minutes and app.tasks.deep_crawl every 15. Redis is the broker.
```

## Install these first

| Tool | Notes |
| --- | --- |
| Docker Desktop | Use the WSL 2 backend (default). Start it and wait for "Engine running". |
| Python 3.12 (3.10 or 3.11 also work) | From python.org. Tick "Add python.exe to PATH" and keep the "py launcher" option. Python 3.13 is not supported yet. |
| Node.js 20 LTS | From nodejs.org. |

## Google sign-in (free)

Without this the Google button is greyed out and email login still works.

1. Open console.cloud.google.com and create a project (free).
2. APIs & Services, then OAuth consent screen: choose External, fill in the app name and your email, and add yourself as a test user.
3. Credentials, then Create credentials, then OAuth client ID, type Web application.
4. Under Authorized JavaScript origins add `http://localhost:5173`. Leave redirect URIs empty.
5. Copy the client ID (it ends in `.apps.googleusercontent.com`).
6. Give it to earlycue:
   - Native: `.\setup.ps1` asks for it, or set `GOOGLE_CLIENT_ID=...` in `backend\.env`.
   - Docker: copy `.env.example` to `.env` in the project root and set `GOOGLE_CLIENT_ID=...`.
7. Restart the API.

While the consent screen is in "Testing", only the test users you added can sign in. An account created with Google can sign in again with Google. If someone already registered with the same email, Google sign-in links to that account.

### Syncing with Groww and other demat apps

Google sign-in only proves who someone is. It cannot read anyone's holdings. To my knowledge no broker exposes portfolio data through Google login: each one needs its own connection (its own login or API key, and some charge for API access). Check each broker's current terms before planning around it. Nothing for this is built yet. The user table already stores the Google account ID, so a "connected brokers" table can be added later without changing login.

## Option A: one command, everything in Docker

```powershell
copy .env.example .env
notepad .env
docker compose up --build
```

Set `SECRET_KEY` in `.env` to a long random string first (it signs login cookies). Then open http://localhost:5173 (API docs at http://localhost:8000/docs) and create an account.

The worker fetches news as soon as it starts. The first run downloads FinBERT (about 440 MB, cached in a Docker volume), so the dashboard stays empty for a few minutes the first time. Watch with `docker compose logs -f worker`. Prices start within a minute.

`docker compose down` stops everything and keeps your data. `docker compose down -v` also wipes the database.

Upgrading an existing install: your data is kept. On startup the API adds new columns and removes old ticker tags that crossed markets.

## Option B: native development (hot reload)

Postgres and Redis run in Docker. The API, worker, scheduler and frontend run on your machine.

First time only:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\setup.ps1
```

`setup.ps1` creates the virtual environment, installs CPU PyTorch and the backend packages, downloads the spaCy model, creates `backend\.env` with a random `SECRET_KEY`, and runs `npm install`.

Every time after that:

```powershell
.\start.ps1
```

This starts Postgres and Redis in Docker, opens four PowerShell windows (api, worker, beat, frontend), and opens http://localhost:5173. Stop with `.\stop.ps1` and close the four windows.

Postgres is on port 5433 and Redis on 6380, so they will not clash with ones you already run.

### By hand instead of the scripts

```powershell
docker compose up -d db redis
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
python -m spacy download en_core_web_sm
copy .env.example .env
uvicorn app.main:api --reload
```

In two more terminals (venv activated, inside `backend`):

```powershell
celery -A app.celery_app:celery worker --loglevel=info --pool=solo
celery -A app.celery_app:celery beat --loglevel=info
```

`--pool=solo` is required on Windows. Then in `frontend`: `npm install` and `npm run dev`.

## How "Refresh data" behaves (admin)

Only the admin sees the Refresh button and the queue state. Regular users just see when the news last updated, or a "please wait, we are catching up" message if it has been more than 30 minutes. The admin header shows the queue state:

- **Worker online:** the button queues a fetch on the worker.
- **Worker did not answer:** Redis is up but the worker is offline, or busy (the Windows solo worker cannot answer while it works). A queued fetch is picked up when it is free.
- **Task queue not reachable:** Redis is down. The button still works because the API runs the fetch itself. Prices keep updating either way, because the API refreshes them.

## Quick start without Docker

SQLite and the built-in keyword scorer, no Redis or Postgres:

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./dev.db"
$env:USE_FINBERT="false"
uvicorn app.main:api --reload
```

Create an account, then click "Refresh data".

## API

All endpoints except `/api/health` and `/api/auth/*` need a signed-in session. Rows marked admin return 403 for regular users.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/auth/register`, `/login`, `/google`, `/logout` | Account and session |
| `GET /api/auth/me`, `/api/auth/config` | Current user, Google client ID |
| `GET /api/articles` | Filters: `market`, `sentiment`, `sector`, `source`, `ticker`, `q`, `hours`, `limit`, `offset` |
| `GET /api/market-pulse?market=IN&hours=24&sector=Banking` | Overall tilt, sectors, trend, most mentioned stocks. With `sector`, the trend, stats and stocks are for that sector |
| `GET /api/movers?market=US&by=price&sector=IT` | Most changed stocks (`by=price` or `sentiment`), index levels, market open flag |
| `GET /api/history/{symbol}?range=1M` | Price history for any listed stock or index (1D, 1W, 1M, 3M, 1Y) |
| `GET /api/history/sector/{sector}?market=IN&range=1M` | Equal-weighted price index of a sector's largest stocks |
| `GET /api/public/front-page` | Public: overall sentiment and top 3 stories per market for the landing page |
| `GET /api/ticker/{symbol}` | Price, stats, daily trend and articles for one company or index |
| `GET /api/tickers/search?q=inf&market=IN` | Autocomplete |
| `GET /api/sources` (admin) | Health of every direct feed and crawl group on its last run |
| `GET /api/admin/overview`, `/api/admin/users` (admin) | Counts, backlog, price backoff, user list |
| `GET /api/status` (admin) | Queue and worker state |
| `GET /api/health` | Story count and last news and price times |
| `POST /api/admin/refresh` (admin) | Start a fetch and a deep crawl now |

## Tests

```powershell
cd backend
.venv\Scripts\Activate.ps1
pytest
```

Uses SQLite and the keyword scorer. No network, Docker or model download needed.

## Troubleshooting on Windows

| Problem | Fix |
| --- | --- |
| `docker compose` says the engine is not running | Start Docker Desktop and wait for "Engine running" |
| `.\setup.ps1 cannot be loaded because running scripts is disabled` | Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again |
| Setup says Python was not found | Install Python 3.12 with the py launcher, then reopen PowerShell |
| Worker crashes with `ValueError: not enough values to unpack` | The worker was started without `--pool=solo` |
| Dashboard is empty after start | Normal for a few minutes while FinBERT downloads. Check the worker window or `docker compose logs -f worker` |
| Few stories after the first run | Sign in as admin and open the Admin console, or run `python -m scripts.check_feeds` and `python -m scripts.crawl_once`. Google News or GDELT may be rate-limiting you (the console shows the error) |
| Prices do not load | Yahoo may be blocking or rate-limiting. Look for "refreshed N of M quotes" or "backing off" in the API log |
| Google button is greyed out | `GOOGLE_CLIENT_ID` is not set, or the API was not restarted |
| Google says "Access blocked" or origin mismatch | Add `http://localhost:5173` under Authorized JavaScript origins and add your account as a test user |
| Signed out after restarting | `SECRET_KEY` changed. Keep it fixed in `.env` |
| Port 5173 or 8000 already in use | `netstat -ano \| findstr :8000`, then `taskkill /PID <pid> /F` |
| `pip install` fails on psycopg2 | You are on Python 3.13. Use 3.12 |

## Where to extend

- Companies, sectors and market membership: `backend\app\tickers.py`.
- Trusted publishers: `backend\app\trusted.py`. Feeds and timing: `backend\app\config.py` (`QUOTE_INTERVAL_SECONDS`, `FETCH_INTERVAL_MINUTES`, `CRAWL_INTERVAL_MINUTES`, `RETENTION_DAYS`, plus `UNRELATED_DAYS` for stories with no market link).
- Before deploying publicly: set `COOKIE_SECURE=true` behind HTTPS, set a strong `SECRET_KEY`, and add Alembic migrations.
