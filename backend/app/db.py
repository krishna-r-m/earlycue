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
    cols={c["name"] for c in insp.get_columns("articles")}
    ucols={c["name"] for c in insp.get_columns("users")}
    icols={c["name"] for c in insp.get_columns("instruments")}
    with engine.begin() as conn:
        for col,ddl in (("sector","VARCHAR(30)"),("industry","VARCHAR(120)"),("market_cap","FLOAT")):
            if col not in icols:
                conn.execute(text(f"ALTER TABLE instruments ADD COLUMN {col} {ddl}"))
        if "instruments" in insp.get_table_names():
            icols={c["name"] for c in insp.get_columns("instruments")}
            if "sector" not in icols:
                conn.execute(text("ALTER TABLE instruments ADD COLUMN sector VARCHAR(20)"))
            if "rank" not in icols:
                conn.execute(text("ALTER TABLE instruments ADD COLUMN rank INTEGER"))
        if "role" not in ucols:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(10) NOT NULL DEFAULT 'user'"))
        if "market" not in cols:
            conn.execute(text("ALTER TABLE articles ADD COLUMN market VARCHAR(2) NOT NULL DEFAULT 'IN'"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_articles_market ON articles (market)"))
