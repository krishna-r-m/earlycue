from urllib.parse import urlparse

trusted={
    "economictimes.indiatimes.com":("Economic Times",("IN",)),
    "moneycontrol.com":("Moneycontrol",("IN",)),
    "livemint.com":("LiveMint",("IN",)),
    "business-standard.com":("Business Standard",("IN",)),
    "financialexpress.com":("Financial Express",("IN",)),
    "thehindubusinessline.com":("BusinessLine",("IN",)),
    "thehindu.com":("The Hindu",("IN",)),
    "hindustantimes.com":("Hindustan Times",("IN",)),
    "timesofindia.indiatimes.com":("Times of India",("IN",)),
    "indianexpress.com":("Indian Express",("IN",)),
    "ndtvprofit.com":("NDTV Profit",("IN",)),
    "cnbctv18.com":("CNBC-TV18",("IN",)),
    "zeebiz.com":("Zee Business",("IN",)),
    "businesstoday.in":("Business Today",("IN",)),
    "reuters.com":("Reuters",("IN","US")),
    "bloomberg.com":("Bloomberg",("IN","US")),
    "ft.com":("Financial Times",("IN","US")),
    "apnews.com":("Associated Press",("IN","US")),
    "bbc.com":("BBC",("IN","US")),
    "forbes.com":("Forbes",("IN","US")),
    "investing.com":("Investing.com",("IN","US")),
    "finance.yahoo.com":("Yahoo Finance",("IN","US")),
    "wsj.com":("Wall Street Journal",("US",)),
    "cnbc.com":("CNBC",("US",)),
    "marketwatch.com":("MarketWatch",("US",)),
    "barrons.com":("Barron's",("US",)),
    "nasdaq.com":("Nasdaq",("US",)),
    "seekingalpha.com":("Seeking Alpha",("US",)),
    "fool.com":("Motley Fool",("US",)),
    "benzinga.com":("Benzinga",("US",)),
    "zacks.com":("Zacks",("US",)),
    "thestreet.com":("TheStreet",("US",)),
    "businessinsider.com":("Business Insider",("US",)),
    "fortune.com":("Fortune",("US",)),
    "theguardian.com":("The Guardian",("US",)),
    "nytimes.com":("New York Times",("US",)),
    "washingtonpost.com":("Washington Post",("US",)),
    "morningstar.com":("Morningstar",("US",)),
    "investopedia.com":("Investopedia",("US",)),
    "kiplinger.com":("Kiplinger",("US",)),
    "barchart.com":("Barchart",("US",)),
}

def host_of(url):
    host=urlparse(url or "").netloc.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host

def match(url):
    host=host_of(url)
    if not host:
        return None
    for domain in trusted:
        if host==domain or host.endswith("."+domain):
            return domain
    return None

def name_of(url):
    domain=match(url)
    return trusted[domain][0] if domain else None
