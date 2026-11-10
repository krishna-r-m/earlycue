from app import config,ingest

def main():
    entries=ingest.fetch_feed(config.feeds_for("Economic Times")[0]["url"])
    for e in entries[:10]:
        print("-",e.get("title"))

if __name__=="__main__":
    main()
