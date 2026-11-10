from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from . import nlp,tickers as tk
from .models import article,sentiment,ticker

def body(row):
    if len(row.summary or "")>=60:
        return row.summary
    return row.raw_content or row.summary or ""

def process_pending(db,limit=200):
    rows=db.execute(
        select(article)
        .outerjoin(sentiment,sentiment.article_id==article.id)
        .where(sentiment.id.is_(None))
        .order_by(article.published_at.desc())
        .limit(limit)
    ).scalars().all()
    if not rows:
        return 0
    results=nlp.analyse_batch([(r.title,body(r),r.market) for r in rows])
    for row,res in zip(rows,results):
        db.add(sentiment(article_id=row.id,sentiment_label=res["label"],confidence_score=res["confidence"],sector=res["sector"],scores=res["scores"]))
        for ent in res["entities"]:
            db.add(ticker(article_id=row.id,symbol=ent["symbol"],company_name=ent["name"]))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return 0
    return len(rows)

def purge_cross_market(db):
    rows=db.execute(select(ticker.id,ticker.symbol,article.market).join(article,article.id==ticker.article_id)).all()
    bad=[r[0] for r in rows if not tk.in_market(r[1],r[2])]
    for i in range(0,len(bad),500):
        chunk=bad[i:i+500]
        db.query(ticker).filter(ticker.id.in_(chunk)).delete(synchronize_session=False)
    db.commit()
    return len(bad)
