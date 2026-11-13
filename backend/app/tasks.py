import logging
from .celery_app import celery
from .db import sessionlocal,init_db
from . import config,crawl,ingest,instruments,pipeline,quotes

log=logging.getLogger(__name__)

@celery.task(name="app.tasks.refresh_news")
def refresh_news():
    init_db()
    db=sessionlocal()
    try:
        instruments.load(db)
        created=ingest.ingest_all(db)
        scored=pipeline.process_pending(db,budget=config.score_budget_seconds)
        removed=pipeline.purge_old(db,config.retention_days,config.unrelated_days)
        priced=0
        try:
            priced=quotes.refresh_quotes(db)+quotes.refresh_bulk(db)
        except Exception:
            db.rollback()
            log.exception("quote refresh failed")
        log.info("refresh done: %s new, %s scored, %s quotes, %s old removed",created,scored,priced,removed)
        return {"new_articles":created,"scored":scored,"quotes":priced,"removed":removed}
    finally:
        db.close()

@celery.task(name="app.tasks.deep_crawl")
def deep_crawl():
    init_db()
    db=sessionlocal()
    try:
        instruments.load(db)
        created=crawl.run_deep_crawl(db)
        scored=pipeline.process_pending(db,budget=config.score_budget_seconds)
        log.info("deep crawl done: %s new, %s scored",created,scored)
        return {"new_articles":created,"scored":scored}
    finally:
        db.close()

@celery.task(name="app.tasks.sync_instruments")
def sync_instruments():
    init_db()
    db=sessionlocal()
    try:
        return {"listed":instruments.sync(db)}
    finally:
        db.close()
