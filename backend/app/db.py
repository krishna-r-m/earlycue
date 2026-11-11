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
    with engine.begin() as conn:
        if "role" not in ucols:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(10) NOT NULL DEFAULT 'user'"))
        if "market" not in cols:
            conn.execute(text("ALTER TABLE articles ADD COLUMN market VARCHAR(2) NOT NULL DEFAULT 'IN'"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_articles_market ON articles (market)"))
