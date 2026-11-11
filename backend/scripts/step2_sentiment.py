from app import config,ingest,nlp

def main():
    entries=ingest.fetch_feed(config.feeds_for("Economic Times")[0]["url"])[:10]
    items=[(ingest.clean_text(e.get("title","")),ingest.clean_text(e.get("summary",""))) for e in entries]
    results=nlp.analyse_batch(items)
    print("engine:",nlp.backend_name())
    for (title,_),r in zip(items,results):
        syms=",".join(e["symbol"] for e in r["entities"]) or "-"
        print(f"{r['label']:8} {r['confidence']:.2f}  {r['sector']:15} {syms:18} {title}")

if __name__=="__main__":
    main()
