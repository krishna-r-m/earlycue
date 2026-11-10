from datetime import datetime,timezone
from sqlalchemy import Column,Integer,String,Text,DateTime,Float,ForeignKey,JSON,UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from .db import base

jsontype=JSON().with_variant(JSONB(),"postgresql")

def utcnow():
    return datetime.now(timezone.utc)

class article(base):
    __tablename__="articles"
    id=Column(Integer,primary_key=True)
    title=Column(String(500),nullable=False)
    source=Column(String(80),nullable=False,index=True)
    market=Column(String(2),nullable=False,default="IN",server_default="IN",index=True)
    url=Column(String(1000),nullable=False)
    url_hash=Column(String(64),nullable=False,unique=True)
    title_hash=Column(String(64),nullable=False,index=True)
    published_at=Column(DateTime(timezone=True),nullable=False,index=True)
    summary=Column(Text,default="")
    raw_content=Column(Text,default="")
    created_at=Column(DateTime(timezone=True),default=utcnow)
    sentiment=relationship("sentiment",back_populates="article",uselist=False,cascade="all,delete-orphan")
    tickers=relationship("ticker",back_populates="article",cascade="all,delete-orphan")

class sentiment(base):
    __tablename__="sentiments"
    id=Column(Integer,primary_key=True)
    article_id=Column(Integer,ForeignKey("articles.id",ondelete="CASCADE"),nullable=False,unique=True)
    sentiment_label=Column(String(10),nullable=False,index=True)
    confidence_score=Column(Float,nullable=False)
    sector=Column(String(40),index=True)
    scores=Column(jsontype)
    created_at=Column(DateTime(timezone=True),default=utcnow)
    article=relationship("article",back_populates="sentiment")

class ticker(base):
    __tablename__="tickers"
    __table_args__=(UniqueConstraint("article_id","symbol"),)
    id=Column(Integer,primary_key=True)
    article_id=Column(Integer,ForeignKey("articles.id",ondelete="CASCADE"),nullable=False,index=True)
    symbol=Column(String(20),nullable=False,index=True)
    company_name=Column(String(120))
    article=relationship("article",back_populates="tickers")

class user(base):
    __tablename__="users"
    id=Column(Integer,primary_key=True)
    email=Column(String(255),nullable=False,unique=True,index=True)
    name=Column(String(120),nullable=False,default="")
    password_hash=Column(String(200))
    google_sub=Column(String(64),unique=True)
    created_at=Column(DateTime(timezone=True),default=utcnow)

class pricequote(base):
    __tablename__="quotes"
    symbol=Column(String(20),primary_key=True)
    market=Column(String(3),nullable=False)
    price=Column(Float,nullable=False)
    prev_close=Column(Float,nullable=False)
    change_pct=Column(Float,nullable=False)
    currency=Column(String(8))
    updated_at=Column(DateTime(timezone=True),default=utcnow)

class feedstat(base):
    __tablename__="feedstats"
    url=Column(String(1000),primary_key=True)
    source=Column(String(80),nullable=False)
    market=Column(String(2),nullable=False)
    last_attempt_at=Column(DateTime(timezone=True))
    last_ok_at=Column(DateTime(timezone=True))
    last_count=Column(Integer,default=0)
    last_new=Column(Integer,default=0)
    last_error=Column(String(300))
