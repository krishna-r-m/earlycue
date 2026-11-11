import Tag from "./Tag.jsx"
import {timeago} from "../lib.js"

export default function SectorNews({name,items,total,onall}){
  if(!items.length)return null
  return(
    <section aria-label={`Top ${name} stories`}>
      <h2 className="sec">Top {name} stories</h2>
      <ul className="mt-2 divide-y divide-rule border-b border-rule">
        {items.map(a=>(
          <li key={a.id} className="py-3">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <Tag label={a.sentiment} conf={a.confidence}/>
              {a.tickers.slice(0,3).map(x=>(
                <span key={x.symbol} className="num text-xs font-semibold text-mute">{x.symbol}</span>
              ))}
            </div>
            <a href={a.url} target="_blank" rel="noopener noreferrer" className="mt-1.5 block font-serif text-[1.05rem] font-semibold leading-snug hover:underline">
              {a.title}
            </a>
            <p className="mt-1 text-xs text-mute">{a.source}, {timeago(a.published_at)}</p>
          </li>
        ))}
      </ul>
      {total>items.length&&(
        <button type="button" onClick={onall} className="link mt-3 text-sm font-semibold">
          See all {total} {name} stories
        </button>
      )}
    </section>
  )
}
