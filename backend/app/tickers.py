import re

sector_names=["Banking","IT","Auto","Energy","Pharma","FMCG","Metals","Telecom","Infrastructure","Macroeconomics"]

entities=[
    ("HDFCBANK","HDFC Bank","Banking",["hdfc bank","hdfcbank"]),
    ("ICICIBANK","ICICI Bank","Banking",["icici bank","icicibank"]),
    ("SBIN","State Bank of India","Banking",["state bank of india","sbi","sbin"]),
    ("AXISBANK","Axis Bank","Banking",["axis bank","axisbank"]),
    ("KOTAKBANK","Kotak Mahindra Bank","Banking",["kotak mahindra bank","kotak bank","kotak"]),
    ("INDUSINDBK","IndusInd Bank","Banking",["indusind bank","indusindbk"]),
    ("BANKBARODA","Bank of Baroda","Banking",["bank of baroda","bankbaroda"]),
    ("PNB","Punjab National Bank","Banking",["punjab national bank","pnb"]),
    ("CANBK","Canara Bank","Banking",["canara bank","canbk"]),
    ("YESBANK","Yes Bank","Banking",["yes bank","yesbank"]),
    ("BAJFINANCE","Bajaj Finance","Banking",["bajaj finance","bajfinance"]),
    ("BAJAJFINSV","Bajaj Finserv","Banking",["bajaj finserv","bajajfinsv"]),
    ("TCS","Tata Consultancy Services","IT",["tata consultancy services","tata consultancy","tcs"]),
    ("INFY","Infosys","IT",["infosys","infy"]),
    ("WIPRO","Wipro","IT",["wipro"]),
    ("HCLTECH","HCL Technologies","IT",["hcl technologies","hcl tech","hcltech"]),
    ("TECHM","Tech Mahindra","IT",["tech mahindra","techm"]),
    ("LTIM","LTIMindtree","IT",["ltimindtree","ltim"]),
    ("RELIANCE","Reliance Industries","Energy",["reliance industries","reliance","ril"]),
    ("ONGC","Oil and Natural Gas Corporation","Energy",["oil and natural gas corporation","ongc"]),
    ("BPCL","Bharat Petroleum","Energy",["bharat petroleum","bpcl"]),
    ("IOC","Indian Oil Corporation","Energy",["indian oil corporation","indian oil","iocl","ioc"]),
    ("NTPC","NTPC","Energy",["ntpc"]),
    ("POWERGRID","Power Grid Corporation","Energy",["power grid corporation","power grid","powergrid"]),
    ("COALINDIA","Coal India","Energy",["coal india","coalindia"]),
    ("CRUDE","Crude Oil","Energy",["brent crude","crude oil","brent"]),
    ("TATAMOTORS","Tata Motors","Auto",["tata motors","tatamotors"]),
    ("MARUTI","Maruti Suzuki","Auto",["maruti suzuki","maruti"]),
    ("M&M","Mahindra & Mahindra","Auto",["mahindra & mahindra","mahindra and mahindra","m&m"]),
    ("BAJAJ-AUTO","Bajaj Auto","Auto",["bajaj auto"]),
    ("EICHERMOT","Eicher Motors","Auto",["eicher motors","eichermot"]),
    ("HEROMOTOCO","Hero MotoCorp","Auto",["hero motocorp","heromotoco"]),
    ("SUNPHARMA","Sun Pharmaceutical","Pharma",["sun pharmaceutical","sun pharma","sunpharma"]),
    ("DRREDDY","Dr. Reddy's Laboratories","Pharma",["dr. reddy's laboratories","dr reddy's","dr reddys","dr. reddy's","drreddy"]),
    ("CIPLA","Cipla","Pharma",["cipla"]),
    ("DIVISLAB","Divi's Laboratories","Pharma",["divi's laboratories","divi's labs","divislab"]),
    ("APOLLOHOSP","Apollo Hospitals","Pharma",["apollo hospitals","apollohosp"]),
    ("HINDUNILVR","Hindustan Unilever","FMCG",["hindustan unilever","hul","hindunilvr"]),
    ("ITC","ITC","FMCG",["itc"]),
    ("NESTLEIND","Nestle India","FMCG",["nestle india","nestleind"]),
    ("BRITANNIA","Britannia Industries","FMCG",["britannia industries","britannia"]),
    ("ASIANPAINT","Asian Paints","FMCG",["asian paints","asianpaint"]),
    ("TITAN","Titan Company","FMCG",["titan company","titan"]),
    ("TATASTEEL","Tata Steel","Metals",["tata steel","tatasteel"]),
    ("JSWSTEEL","JSW Steel","Metals",["jsw steel","jswsteel"]),
    ("HINDALCO","Hindalco Industries","Metals",["hindalco industries","hindalco"]),
    ("VEDL","Vedanta","Metals",["vedanta","vedl"]),
    ("BHARTIARTL","Bharti Airtel","Telecom",["bharti airtel","airtel","bhartiartl"]),
    ("LT","Larsen & Toubro","Infrastructure",["larsen & toubro","larsen and toubro","l&t"]),
    ("ULTRACEMCO","UltraTech Cement","Infrastructure",["ultratech cement","ultratech","ultracemco"]),
    ("ADANIENT","Adani Enterprises","Infrastructure",["adani enterprises","adanient"]),
    ("ADANIPORTS","Adani Ports","Infrastructure",["adani ports","adaniports"]),
    ("NIFTY","Nifty 50","Macroeconomics",["nifty 50","nifty50","nifty"]),
    ("BANKNIFTY","Bank Nifty","Macroeconomics",["bank nifty","banknifty","nifty bank"]),
    ("SENSEX","BSE Sensex","Macroeconomics",["bse sensex","sensex"]),
    ("RBI","Reserve Bank of India","Macroeconomics",["reserve bank of india","reserve bank","rbi"]),
    ("SEBI","Securities and Exchange Board of India","Macroeconomics",["securities and exchange board of india","sebi"]),
    ("FED","US Federal Reserve","Macroeconomics",["us federal reserve","federal reserve","us fed","the fed"]),
    ("FII","Foreign Institutional Investors","Macroeconomics",["foreign institutional investors","foreign portfolio investors","fiis","fii","fpis","fpi"]),
    ("USDINR","Indian Rupee","Macroeconomics",["indian rupee","rupee","usd/inr"]),
]

entities+=[
    ("AAPL","Apple","IT",["apple inc","apple"]),
    ("MSFT","Microsoft","IT",["microsoft","msft"]),
    ("NVDA","Nvidia","IT",["nvidia","nvda"]),
    ("GOOGL","Alphabet","IT",["alphabet","google","googl"]),
    ("AMZN","Amazon","IT",["amazon","amzn"]),
    ("META","Meta Platforms","IT",["meta platforms","facebook"]),
    ("NFLX","Netflix","IT",["netflix"]),
    ("INTC","Intel","IT",["intel corp","intel"]),
    ("AMD","Advanced Micro Devices","IT",["advanced micro devices","amd"]),
    ("ORCL","Oracle","IT",["oracle"]),
    ("CRM","Salesforce","IT",["salesforce"]),
    ("ADBE","Adobe","IT",["adobe"]),
    ("IBM","IBM","IT",["ibm"]),
    ("TSLA","Tesla","Auto",["tesla","tsla"]),
    ("F","Ford Motor","Auto",["ford motor","ford"]),
    ("GM","General Motors","Auto",["general motors"]),
    ("JPM","JPMorgan Chase","Banking",["jpmorgan chase","jpmorgan","jp morgan"]),
    ("BAC","Bank of America","Banking",["bank of america"]),
    ("WFC","Wells Fargo","Banking",["wells fargo"]),
    ("GS","Goldman Sachs","Banking",["goldman sachs","goldman"]),
    ("MS","Morgan Stanley","Banking",["morgan stanley"]),
    ("C","Citigroup","Banking",["citigroup","citi"]),
    ("V","Visa Inc","Banking",["visa inc"]),
    ("MA","Mastercard","Banking",["mastercard"]),
    ("BRK-B","Berkshire Hathaway","Banking",["berkshire hathaway","berkshire"]),
    ("XOM","Exxon Mobil","Energy",["exxon mobil","exxonmobil","exxon"]),
    ("CVX","Chevron","Energy",["chevron"]),
    ("NEE","NextEra Energy","Energy",["nextera energy","nextera"]),
    ("JNJ","Johnson & Johnson","Pharma",["johnson & johnson","j&j"]),
    ("PFE","Pfizer","Pharma",["pfizer"]),
    ("UNH","UnitedHealth","Pharma",["unitedhealth"]),
    ("LLY","Eli Lilly","Pharma",["eli lilly","lilly"]),
    ("MRK","Merck","Pharma",["merck"]),
    ("ABBV","AbbVie","Pharma",["abbvie"]),
    ("WMT","Walmart","FMCG",["walmart"]),
    ("COST","Costco","FMCG",["costco"]),
    ("PG","Procter & Gamble","FMCG",["procter & gamble","procter and gamble"]),
    ("KO","Coca-Cola","FMCG",["coca-cola","coca cola"]),
    ("PEP","PepsiCo","FMCG",["pepsico"]),
    ("MCD","McDonald's","FMCG",["mcdonald's","mcdonalds"]),
    ("NKE","Nike","FMCG",["nike"]),
    ("HD","Home Depot","FMCG",["home depot"]),
    ("DIS","Walt Disney","FMCG",["walt disney","disney"]),
    ("T","AT&T","Telecom",["at&t"]),
    ("VZ","Verizon","Telecom",["verizon"]),
    ("CMCSA","Comcast","Telecom",["comcast"]),
    ("BA","Boeing","Infrastructure",["boeing"]),
    ("CAT","Caterpillar","Infrastructure",["caterpillar"]),
    ("GE","GE Aerospace","Infrastructure",["ge aerospace","general electric"]),
    ("SPX","S&P 500","Macroeconomics",["s&p 500","s&p500"]),
    ("NASDAQ","Nasdaq Composite","Macroeconomics",["nasdaq composite","nasdaq"]),
    ("DJI","Dow Jones Industrial Average","Macroeconomics",["dow jones industrial average","dow jones","the dow"]),
]

sector_keywords={
    "Banking":["bank","banks","banking","nbfc","lender","lenders","loan","loans","credit growth","npa","npas","deposit","deposits"],
    "IT":["it services","it stocks","it sector","software","deal wins","digital services","cloud","artificial intelligence","outsourcing","attrition"],
    "Auto":["auto","automobile","automaker","carmaker","vehicle","vehicles","ev","evs","two-wheeler","passenger vehicle","car sales"],
    "Energy":["oil","gas","crude","refinery","refining","power","renewable","solar","petrol","diesel","fuel"],
    "Pharma":["pharma","pharmaceutical","drug","drugs","usfda","hospital","hospitals","healthcare","biotech"],
    "FMCG":["fmcg","consumer goods","rural demand","packaged food","retail"],
    "Metals":["steel","metal","metals","aluminium","copper","zinc","iron ore","mining"],
    "Telecom":["telecom","5g","spectrum","tariff hike","tariffs","arpu","subscribers"],
    "Infrastructure":["infrastructure","infra","cement","construction","capex","roads","railways","ports"],
    "Macroeconomics":["rbi","repo rate","inflation","gdp","fiscal","budget","rate cut","rate hike","monetary policy","fii","dii","sensex","nifty","rupee","trade deficit","cpi","wpi","iip"],
}

us_start=[e[0] for e in entities].index("AAPL")
us_symbols={e[0] for e in entities[us_start:]}|{"FED"}
any_symbols={"CRUDE"}
index_symbols={"NIFTY","BANKNIFTY","SENSEX","SPX","NASDAQ","DJI"}
unpriced={"RBI","SEBI","FED","FII"}
yahoo_special={"NIFTY":"^NSEI","BANKNIFTY":"^NSEBANK","SENSEX":"^BSESN","SPX":"^GSPC","NASDAQ":"^IXIC","DJI":"^DJI","CRUDE":"BZ=F","USDINR":"INR=X"}

def market_of(symbol):
    if symbol in any_symbols:
        return "ANY"
    return "US" if symbol in us_symbols else "IN"

def yahoo_symbol(symbol):
    if symbol in unpriced:
        return None
    if symbol in yahoo_special:
        return yahoo_special[symbol]
    return symbol if market_of(symbol)=="US" else symbol+".NS"

def is_stock(symbol):
    info=by_symbol.get(symbol)
    return bool(info) and info["sector"]!="Macroeconomics" and symbol not in any_symbols

by_symbol={s:{"symbol":s,"name":n,"sector":sec,"market":None} for s,n,sec,_ in entities}
alias_map={}
for symbol,name,sector,aliases in entities:
    for a in aliases+[name.lower()]:
        alias_map[a.lower()]=symbol

alias_pattern=re.compile(r"(?<![a-z0-9&])("+"|".join(re.escape(a) for a in sorted(alias_map,key=len,reverse=True))+r")(?![a-z0-9&])",re.I)
sector_patterns={s:re.compile(r"\b(?:"+"|".join(re.escape(k) for k in kws)+r")\b") for s,kws in sector_keywords.items()}
suffixes={"ltd","limited","inc","corp","corporation","plc","co","company","pvt","private"}

for _s,_e in by_symbol.items():
    _e["market"]=market_of(_s)

def clean_org(name):
    s=re.sub(r"[^a-z0-9&' ]"," ",name.lower())
    words=[w for w in s.split() if w]
    while words and words[-1] in suffixes:
        words.pop()
    return " ".join(words)

def in_market(symbol,market):
    return market is None or market_of(symbol) in (market,"ANY")

def find_entities(text,orgs=(),market=None):
    found={}
    for m in alias_pattern.finditer(text):
        sym=alias_map[m.group(1).lower()]
        if in_market(sym,market):
            found.setdefault(sym,by_symbol[sym])
    for org in orgs:
        sym=alias_map.get(clean_org(org))
        if sym and in_market(sym,market):
            found.setdefault(sym,by_symbol[sym])
    return list(found.values())

def tag_sector(text,ents):
    low=text.lower()
    scores={s:len(p.findall(low)) for s,p in sector_patterns.items()}
    for e in ents:
        weight=2 if e["sector"]=="Macroeconomics" else 3
        scores[e["sector"]]=scores.get(e["sector"],0)+weight
    best=max(scores,key=scores.get)
    return best if scores[best]>0 else "General"

def search(q,limit=8,market=None):
    ql=q.strip().lower()
    if not ql:
        return []
    hits=[]
    for symbol,name,sector,aliases in entities:
        if market and market_of(symbol) not in (market,"ANY"):
            continue
        sl=symbol.lower()
        nl=name.lower()
        if sl.startswith(ql):
            rank=0
        elif nl.startswith(ql):
            rank=1
        elif any(a.startswith(ql) for a in aliases):
            rank=2
        elif ql in nl or ql in sl:
            rank=3
        else:
            continue
        hits.append((rank,len(name),symbol,name,sector))
    hits.sort()
    return [{"symbol":h[2],"name":h[3],"sector":h[4]} for h in hits[:limit]]
