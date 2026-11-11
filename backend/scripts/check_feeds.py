from concurrent.futures import ThreadPoolExecutor
from app import config,ingest

def check(feed):
    entries,error=ingest.fetch_feed_status(feed["url"])
    return feed,len(entries),error

def main():
    with ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(check,config.feeds))
    ok=0
    for feed,count,error in results:
        status=f"OK   {count:3} entries" if error is None else f"FAIL {error}"
        ok+=error is None
        print(f"{feed['market']}  {feed['source']:18} {status:28} {feed['url']}")
    print(f"\n{ok} of {len(results)} feeds working")

if __name__=="__main__":
    main()
