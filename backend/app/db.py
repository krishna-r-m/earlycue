from sqlalchemy import create_engine,inspect,text
from sqlalchemy.orm import sessionmaker,declarative_base
from . import config

args={"check_same_thread":False} if config.database_url.startswith("sqlite") else {}
engine=create_engine(config.database_url,pool_pre_ping=True,connect_args=args)
sessionlocal=sessionmaker(bind=engine,autoflush=False,autocommit=False)
base=declarative_base()

def get_db():
    db=sessionlocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from . import models
    base.metadata.create_all(engine)
    insp=inspect(engine)
    have={t:{c["name"] for c in insp.get_columns(t)} for t in ("articles","users","instruments")}
    adds=[
        ("articles","market","VARCHAR(2) NOT NULL DEFAULT 'IN'"),
        ("users","role","VARCHAR(10) NOT NULL DEFAULT 'user'"),
        ("users","picture","VARCHAR(500)"),
        ("instruments","sector","VARCHAR(20)"),
        ("instruments","rank","INTEGER"),
    ]
    with engine.begin() as conn:
        for table,col,ddl in adds:
            if col not in have[table]:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}"))
        for name,table,cols in (
            ("ix_articles_market","articles","market"),
            ("ix_articles_market_pub","articles","market, published_at"),
            ("ix_tickers_symbol_article","tickers","symbol, article_id"),
            ("ix_quotes_updated","quotes","updated_at"),
        ):
            conn.execute(text(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({cols})"))
