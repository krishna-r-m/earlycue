import logging
from .celery_app import celery
from .db import sessionlocal,init_db
from . import ingest,pipeline,quotes

log=logging.getLogger(__name__)

@celery.task(name="app.tasks.refresh_news")
def refresh_news():
    init_db()
    db=sessionlocal()
    try:
        created=ingest.ingest_all(db)
        scored=pipeline.process_pending(db)
        priced=0
        try:
            priced=quotes.refresh_quotes(db)
        except Exception:
            db.rollback()
            log.exception("quote refresh failed")
        log.info("refresh done: %s new, %s scored, %s quotes",created,scored,priced)
        return {"new_articles":created,"scored":scored,"quotes":priced}
    finally:
        db.close()
