import {useState} from "react"
import Segmented from "./Segmented.jsx"
import Tag from "./Tag.jsx"
import {toneof,timeago,pct,sectorlabel,signed} from "../lib.js"

const filters=[
  {value:null,label:"All"},
  {value:"bullish",label:"Bullish"},
  {value:"bearish",label:"Bearish"},
  {value:"neutral",label:"Neutral"}
]

function Row({a,on,onpick}){
  return(
    <li>
      <button
        type="button"
        aria-current={on}
        onClick={()=>onpick(a.id)}
        className={"block w-full border-l-[3px] px-4 py-3 text-left "+(on?"border-l-mark bg-surface":"border-l-transparent hover:bg-surface/70")}
      >
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <Tag label={a.sentiment} conf={a.confidence}/>
          {a.tickers.slice(0,3).map(x=>(
            <span key={x.symbol} className="num text-xs font-semibold text-mute">{x.symbol}</span>
          ))}
        </div>
        <p className="mt-1.5 font-serif text-[1.02rem] font-semibold leading-snug">{a.title}</p>
        <p className="mt-1 text-xs text-mute">{a.source}, {timeago(a.published_at)}</p>
      </button>
    </li>
  )
}

function Detail({a,onticker,market}){
  if(!a){
    return(
      <div className="panel p-5 text-sm text-mute">
        Select a headline to see its summary and score.
      </div>
    )
  }
  const t=toneof(a.sentiment)
  return(
    <article className="panel p-5">
      <div className="flex items-baseline justify-between gap-3">
        <p className={"font-serif text-3xl font-bold "+t.text}>{a.sentiment||"Unscored"}</p>
        <p className="num text-sm text-mute">{pct(a.confidence)} confidence</p>
      </div>
      <div className="mt-2 h-1.5 bg-rule">
        <div className={"h-full "+t.bg} style={{width:pct(a.confidence)||"0%"}}/>
      </div>
      <h3 className="mt-4 font-serif text-xl font-bold leading-snug">{a.title}</h3>
      <p className="mt-1 text-sm text-mute">{a.source}, {timeago(a.published_at)}{a.sector?`, ${sectorlabel(market,a.sector)}`:""}</p>
      {a.summary&&<p className="mt-3 max-w-prose leading-relaxed">{a.summary}</p>}
      {a.tickers.length>0&&(
        <div className="mt-4 flex flex-wrap gap-2">
          {a.tickers.map(x=>(
            <button
              key={x.symbol}
              type="button"
              onClick={()=>onticker(x.symbol)}
              className="num border border-ink px-2 py-0.5 text-sm font-semibold hover:bg-mark hover:text-on-mark"
              title={x.name||x.symbol}
            >
              {x.symbol}
            </button>
          ))}
        </div>
      )}
      <a href={a.url} target="_blank" rel="noopener noreferrer" className="link mt-5 inline-block text-sm font-semibold">
        Read it at {a.source}
      </a>
    </article>
  )
}

export default function Feed({items,loading,filter,onfilter,onticker,empty,market,title="Latest news",stats,feedref}){
  const [selected,setselected]=useState(null)
  const current=items.find(a=>a.id===selected)||items[0]||null
  return(
    <section aria-label={title} ref={feedref} className="scroll-mt-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h2 className="sec min-w-[10rem] flex-1">{title}</h2>
        <Segmented label="Sentiment filter" options={filters} value={filter} onchange={onfilter}/>
      </div>
      {stats&&stats.total>0&&(
        <p className="mt-2 text-sm text-mute">
          Overall <span className={"font-semibold "+toneof(stats.leaning).text}>{stats.leaning}</span>
          <span className="num"> ({signed(stats.score)})</span>: {stats.bullish} bullish, {stats.neutral} neutral, {stats.bearish} bearish.
        </p>
      )}
      {loading&&!items.length?(
        <p className="mt-4 text-sm text-mute">Loading articles...</p>
      ):!items.length?(
        <p className="panel mt-4 p-5 text-sm text-mute">
          {empty||"No stories match these filters yet. Please check back shortly, new stories arrive throughout the day."}
        </p>
      ):(
        <div className="mt-4 grid gap-5 lg:grid-cols-5">
          <ul className="max-h-[72vh] divide-y divide-rule overflow-y-auto border-y border-rule lg:col-span-3">
            {items.map(a=>(
              <Row key={a.id} a={a} on={current&&current.id===a.id} onpick={setselected}/>
            ))}
          </ul>
          <div className="lg:col-span-2">
            <div className="lg:sticky lg:top-4">
              <Detail a={current} onticker={onticker} market={market}/>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
