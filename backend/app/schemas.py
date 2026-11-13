from datetime import datetime
from pydantic import BaseModel

class tickerref(BaseModel):
    symbol:str
    name:str|None=None

class articleout(BaseModel):
    id:int
    title:str
    source:str
    url:str
    published_at:datetime|None=None
    summary:str|None=None
    sentiment:str|None=None
    confidence:float|None=None
    sector:str|None=None
    tickers:list[tickerref]=[]

class articlelist(BaseModel):
    total:int
    items:list[articleout]

class statblock(BaseModel):
    total:int
    bullish:int
    bearish:int
    neutral:int
    score:float
    leaning:str

class sectorpulse(statblock):
    sector:str

class tickerpulse(statblock):
    symbol:str
    name:str|None=None

class trendpoint(BaseModel):
    t:datetime
    score:float
    count:int

class marketpulse(BaseModel):
    hours:int
    generated_at:datetime
    granularity:str
    overall:statblock
    sectors:list[sectorpulse]
    trend:list[trendpoint]
    top_tickers:list[tickerpulse]
    sector:str|None=None
    sector_stats:statblock|None=None

class quoteout(BaseModel):
    price:float
    change_pct:float
    currency:str|None=None

class tickerdetail(BaseModel):
    quote:quoteout|None=None
    symbol:str
    name:str|None=None
    sector:str|None=None
    days:int
    stats:statblock
    trend:list[trendpoint]
    articles:list[articleout]

class tickersuggestion(BaseModel):
    symbol:str
    name:str
    sector:str
    market:str=""

class health(BaseModel):
    status:str
    articles:int
    scored:int
    latest:datetime|None=None
    stocks:int=0
    scored_at:datetime|None=None
    quotes_at:datetime|None=None

class refreshresult(BaseModel):
    queued:bool
    mode:str
    task_id:str|None=None
    detail:str

class queuestatus(BaseModel):
    state:str
    detail:str

class moveritem(BaseModel):
    symbol:str
    name:str|None=None
    sector:str|None=None
    price:float|None=None
    change_pct:float|None=None
    currency:str|None=None
    total:int
    score:float
    leaning:str
    shift:float

class indexquote(BaseModel):
    symbol:str
    name:str
    price:float
    change_pct:float
    currency:str|None=None

class movers(BaseModel):
    market:str
    by:str
    hours:int
    price_available:bool
    total:int=0
    total:int=0
    market_open:bool=False
    sector:str|None=None
    updated_at:datetime|None=None
    items:list[moveritem]
    indices:list[indexquote]

class sourcestat(BaseModel):
    group:bool=False
    partial:bool=False
    source:str
    market:str
    url:str
    ok:bool|None=None
    entries:int=0
    new:int=0
    last_ok_at:datetime|None=None
    error:str|None=None

class adminuser(BaseModel):
    id:int
    email:str
    name:str
    role:str
    google:bool
    created_at:datetime|None=None

class adminoverview(BaseModel):
    articles:int
    scored:int
    pending:int
    added_24h:int
    in_articles:int
    us_articles:int
    users:int
    quotes:int
    instruments:int=0
    instruments_sectored:int=0
    quote_backoff_seconds:int
    db_engine:str

class cleanupresult(BaseModel):
    removed:int
    articles:int

class historypoint(BaseModel):
    t:datetime
    c:float

class history(BaseModel):
    symbol:str
    range:str
    currency:str|None=None
    change_pct:float|None=None
    points:list[historypoint]

class pricepoint(BaseModel):
    t:datetime
    c:float

class history(BaseModel):
    symbol:str
    range:str
    currency:str|None=None
    available:bool=False
    points:list[pricepoint]=[]
    last:float|None=None
    change_pct:float|None=None
    basket:list[str]=[]

class frontstory(BaseModel):
    id:int
    title:str
    source:str
    url:str
    published_at:datetime|None=None
    sentiment:str
    confidence:float
    tickers:list[str]=[]

class frontmarket(BaseModel):
    overall:statblock
    stories:list[frontstory]

class frontpage(BaseModel):
    generated_at:datetime
    markets:dict[str,frontmarket]
