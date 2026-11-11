import logging
import re
import threading
from . import config
from .tickers import find_entities,tag_sector

log=logging.getLogger(__name__)
lock=threading.Lock()
state={"pipe":None,"backend":None,"spacy":None,"spacy_tried":False}
label_map={"positive":"Bullish","negative":"Bearish","neutral":"Neutral"}

positive=set("""surge surges surged rally rallies rallied gain gains gained jump jumps jumped rise rises rose soar soars soared
record beat beats strong growth upgrade upgraded bullish profit profits boost boosts optimism recovery rebound rebounds
outperform wins win orders expansion improve improves improved positive climb climbs climbed advance advances upbeat dividend""".split())

negative=set("""fall falls fell plunge plunges plunged slump slumps drop drops dropped decline declines declined slide slides slid
tumble tumbles tumbled crash loss losses weak weakness downgrade downgraded bearish selloff fear fears concern concerns
worry worries probe fraud penalty default cut cuts miss misses missed slowdown crisis risk risks pressure negative warns
warning sink sinks sank retreat retreats volatile outflow outflows""".split())

def load_sentiment():
    if state["backend"]:
        return state["backend"]
    with lock:
        if state["backend"]:
            return state["backend"]
        if config.use_finbert:
            try:
                from transformers import pipeline
                state["pipe"]=pipeline("text-classification",model=config.finbert_model,top_k=None)
                state["backend"]="finbert"
                return "finbert"
            except Exception as exc:
                log.warning("finbert unavailable (%s), using lexicon fallback",exc)
        state["backend"]="lexicon"
        return "lexicon"

def load_spacy():
    if state["spacy_tried"]:
        return state["spacy"]
    with lock:
        if state["spacy_tried"]:
            return state["spacy"]
        state["spacy_tried"]=True
        try:
            import spacy
            state["spacy"]=spacy.load(config.spacy_model,disable=["parser","lemmatizer"])
        except Exception as exc:
            log.warning("spacy model unavailable (%s), using gazetteer only",exc)
        return state["spacy"]

def lexicon_score(text):
    words=re.findall(r"[a-z']+",text.lower())
    p=sum(w in positive for w in words)
    n=sum(w in negative for w in words)
    total=p+n
    if p>n:
        lead="Bullish"
    elif n>p:
        lead="Bearish"
    else:
        lead="Neutral"
    strength=abs(p-n)/(total+1) if total else 0
    top=0.7 if lead=="Neutral" else 0.55+0.4*strength
    rest=(1-top)/2
    probs={"Bullish":rest,"Bearish":rest,"Neutral":rest}
    probs[lead]=top
    return {"label":lead,"confidence":round(top,4),"scores":probs}

def score_texts(texts):
    if not texts:
        return []
    if load_sentiment()=="finbert":
        outs=state["pipe"]([t[:1500] for t in texts],batch_size=16,truncation=True,max_length=512)
        results=[]
        for out in outs:
            probs={label_map[o["label"].lower()]:float(o["score"]) for o in out}
            label=max(probs,key=probs.get)
            results.append({"label":label,"confidence":round(probs[label],4),"scores":probs})
        return results
    return [lexicon_score(t) for t in texts]

def spacy_orgs(text):
    model=load_spacy()
    if model is None:
        return []
    return [e.text for e in model(text).ents if e.label_=="ORG"]

def build_text(title,summary):
    s=(summary or "").strip()
    return f"{title}. {s[:600]}" if s else title

def analyse_batch(items):
    texts=[build_text(i[0],i[1]) for i in items]
    markets=[i[2] if len(i)>2 else None for i in items]
    scored=score_texts(texts)
    out=[]
    for text,sc,market in zip(texts,scored,markets):
        ents=find_entities(text,spacy_orgs(text),market)
        out.append({**sc,"entities":ents,"sector":tag_sector(text,ents)})
    return out

def backend_name():
    return load_sentiment()
