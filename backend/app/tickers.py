import re

sector_names=["Banking","IT","Auto","Energy","Pharma","FMCG","Metals","Telecom","Infrastructure","Real Estate","Utilities","Macroeconomics"]

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
    "Real Estate":["real estate","realty","housing","reit","property"],
    "Utilities":["utility","utilities","electricity","water supply"],
    "Macroeconomics":["rbi","repo rate","inflation","gdp","fiscal","budget","rate cut","rate hike","monetary policy","fii","dii","sensex","nifty","rupee","trade deficit","cpi","wpi","iip"],
}

us_start=[e[0] for e in entities].index("AAPL")
us_symbols={e[0] for e in entities[us_start:]}|{"FED"}
any_symbols={"CRUDE"}
index_symbols={"NIFTY","BANKNIFTY","SENSEX","SPX","NASDAQ","DJI"}
unpriced={"RBI","SEBI","FED","FII"}
yahoo_special={"NIFTY":"^NSEI","BANKNIFTY":"^NSEBANK","SENSEX":"^BSESN","SPX":"^GSPC","NASDAQ":"^IXIC","DJI":"^DJI","CRUDE":"BZ=F","USDINR":"INR=X"}

by_symbol={s:{"symbol":s,"name":n,"sector":sec,"market":None} for s,n,sec,_ in entities}

def market_of(symbol):
    info=by_symbol.get(symbol)
    if info and info.get("market"):
        return info["market"]
    if symbol in any_symbols:
        return "ANY"
    return "US" if symbol in us_symbols else "IN"

for _i,(_s,_e) in enumerate(by_symbol.items()):
    _e["market"]=market_of(_s)
    _e["rank"]=_i

def yahoo_symbol(symbol):
    if symbol in unpriced:
        return None
    if symbol in yahoo_special:
        return yahoo_special[symbol]
    if symbol.endswith(".BO") or symbol.endswith(".NS"):
        return symbol
    return symbol if market_of(symbol)=="US" else symbol+".NS"

def is_stock(symbol):
    info=by_symbol.get(symbol)
    return bool(info) and info["sector"]!="Macroeconomics" and symbol not in any_symbols

def norm(text):
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9&]+"," ",text.lower())).strip()

sector_rules=[
    ("Banking",("bank","finance","financial","nbfc","insurance","capital market","asset management","credit","loan","fintech","brokerage","broking","investment","lender")),
    ("Pharma",("pharma","drug","biotech","healthcare","health care","hospital","medical","life science","diagnostic","laborator","medicine")),
    ("Telecom",("telecom","communication","wireless","broadband")),
    ("IT",("=it","software","information technology","computer","semiconductor","internet","technolog","infotech","digital","data","electronic")),
    ("Auto",("auto","motor","vehicle","tyre","tire","truck","two wheeler")),
    ("Energy",("oil","gas","petrol","refiner","energy","coal","fuel","renewable","solar")),
    ("Utilities",("power","electric","utility","utilities","water")),
    ("Real Estate",("real estate","realty","reit","propert","housing")),
    ("Metals",("metal","steel","mining","alumin","copper","zinc","iron","alloy","chemical","fertili","paper","material","plastic","packaging")),
    ("Infrastructure",("construction","infrastructure","engineering","capital goods","industrial","cement","building","logistic","shipping","ports","aerospace","defen","machinery","railway","transport","equipment","airline","aviation")),
    ("FMCG",("fmcg","fast moving","consumer","food","beverage","tobacco","retail","apparel","textile","restaurant","hotel","leisure","entertainment","media","packaged","personal care","household","jewel","durable","agri")),
]

def canonical_sector(text):
    if not text:
        return None
    t=" "+norm(text)+" "
    tokens=t.split()
    for sector,words in sector_rules:
        for w in words:
            if " " in w:
                if w in t:
                    return sector
            elif w.startswith("="):
                if w[1:] in tokens:
                    return sector
            elif any(tok.startswith(w) for tok in tokens):
                return sector
    return None

suffixes={"ltd","limited","inc","corp","corporation","plc","co","company","pvt","private"}
sector_patterns={s:re.compile(r"\b(?:"+"|".join(re.escape(k) for k in kws)+r")\b") for s,kws in sector_keywords.items()}
alias_map={}
imported=set()
search_rows=[]
state={"max_tokens":1}

def clean_org(name):
    s=re.sub(r"[^a-z0-9&' ]"," ",name.lower())
    words=[w for w in s.split() if w]
    while words and words[-1] in suffixes:
        words.pop()
    return " ".join(words)

def clean_company(name):
    s=re.split(r" - | class [a-z]\b|,| ordinary shares| common stock| american depositary",name.lower())[0]
    words=clean_org(s).split()
    while words and words[-1] in {"holdings","holding","group"}:
        words.pop()
    return " ".join(words)

common={"national","american","general","international","industries","enterprises","holdings","financial","global","systems","technologies","services","solutions","resources","capital","energy","pharma","power","india","indian","finance","foods","motors","steel","cement","textiles","chemicals","infra","petroleum","products","trading","investments","ventures","education"}

def specific(key):
    if not key:
        return False
    if len(key.split())>=2:
        return True
    return len(key)>=7 and key not in common

def build_search():
    rows=[]
    for symbol,name,sector,aliases in entities:
        rows.append((symbol,name,sector,by_symbol[symbol]["market"],symbol.lower(),norm(name),norm(name).replace(" ",""),[norm(a) for a in aliases]))
    for symbol in sorted(imported):
        info=by_symbol[symbol]
        nn=norm(info["name"])
        rows.append((symbol,info["name"],info["sector"],info["market"],symbol.lower(),nn,nn.replace(" ",""),[]))
    search_rows[:]=rows

def rebuild_aliases():
    for k in [k for k,v in alias_map.items() if v in imported]:
        del alias_map[k]
    for symbol in imported:
        key=norm(clean_company(by_symbol[symbol]["name"]))
        if specific(key):
            alias_map.setdefault(key,symbol)
    state["max_tokens"]=max(len(k.split()) for k in alias_map)

for _symbol,_name,_sector,_aliases in entities:
    for _a in _aliases+[_name]:
        alias_map.setdefault(norm(_a),_symbol)
state["max_tokens"]=max(len(k.split()) for k in alias_map)
build_search()

def register_instruments(rows):
    for symbol in list(imported):
        by_symbol.pop(symbol,None)
    for k in [k for k,v in alias_map.items() if v in imported]:
        del alias_map[k]
    imported.clear()
    skipped=0
    for row in rows:
        symbol,name,market=row[0],row[1],row[2]
        if symbol in by_symbol:
            skipped+=1
            continue
        sector=row[3] if len(row)>3 and row[3] in sector_names else "General"
        rank=row[4] if len(row)>4 and row[4] is not None else 100000
        by_symbol[symbol]={"symbol":symbol,"name":name,"sector":sector,"market":market,"rank":200+rank}
        imported.add(symbol)
    rebuild_aliases()
    build_search()
    return len(imported),skipped

def in_market(symbol,market):
    return market is None or market_of(symbol) in (market,"ANY")

def find_entities(text,orgs=(),market=None):
    found={}
    tokens=norm(text).split()
    i=0
    top=state["max_tokens"]
    while i<len(tokens):
        hit=None
        for n in range(min(top,len(tokens)-i),0,-1):
            sym=alias_map.get(" ".join(tokens[i:i+n]))
            if sym:
                hit=(sym,n)
                break
        if hit:
            if in_market(hit[0],market):
                found.setdefault(hit[0],by_symbol[hit[0]])
            i+=hit[1]
        else:
            i+=1
    for org in orgs:
        sym=alias_map.get(norm(clean_org(org)))
        if sym and in_market(sym,market):
            found.setdefault(sym,by_symbol[sym])
    return list(found.values())

def tag_sector(text,ents):
    low=text.lower()
    scores={s:len(p.findall(low)) for s,p in sector_patterns.items()}
    for e in ents:
        if e["sector"]=="General":
            continue
        weight=2 if e["sector"]=="Macroeconomics" else 3
        scores[e["sector"]]=scores.get(e["sector"],0)+weight
    best=max(scores,key=scores.get)
    return best if scores[best]>0 else "General"

def search(q,limit=8,market=None):
    qn=norm(q)
    qs=qn.replace(" ","")
    if not qs:
        return []
    hits=[]
    for symbol,name,sector,m,sl,nn,ns,aliases in search_rows:
        if market and m not in (market,"ANY"):
            continue
        if sl==qs:
            rank=-1
        elif sl.startswith(qs):
            rank=0
        elif ns.startswith(qs):
            rank=1
        elif any(w.startswith(qn) for w in [nn]+aliases) or any(t.startswith(qs) for t in nn.split()):
            rank=2
        elif qs in ns or qs in sl:
            rank=3
        else:
            continue
        hits.append((rank,symbol in imported,len(name),symbol,name,sector,m))
    hits.sort()
    return [{"symbol":h[3],"name":h[4],"sector":h[5],"market":h[6]} for h in hits[:limit]]
