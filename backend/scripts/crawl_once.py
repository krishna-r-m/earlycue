from app import crawl,pipeline
from app.db import init_db,sessionlocal
from app.models import feedstat,article
from sqlalchemy import select,func

def main():
    init_db()
    db=sessionlocal()
    before=db.scalar(select(func.count(article.id)))
    new=crawl.run_deep_crawl(db)
    print(f"stories before: {before}, new from this crawl: {new}")
    for row in db.execute(select(feedstat).where(feedstat.url.like("crawl:%"),feedstat.url!="crawl:cursor").order_by(feedstat.url)).scalars():
        print(f"{row.market}  {row.source:28} entries {row.last_count:5}  new {row.last_new:5}  {row.last_error or 'ok'}")
    print("scoring new stories...")
    print("scored:",pipeline.process_pending(db))

if __name__=="__main__":
    main()
