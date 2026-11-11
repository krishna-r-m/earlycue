import {useEffect,useRef,useState} from "react"
import {api} from "../api.js"
import Segmented from "./Segmented.jsx"
import {toneof,money,pctchange,signed,sign,clock,sectorlabel} from "../lib.js"

const tabs=[
  {value:"price",label:"Price"},
  {value:"sentiment",label:"Sentiment"}
]

export default function Movers({market,hours,sector,qtick,onticker,onexpired,isadmin}){
  const [by,setby]=useState("price")
  const [data,setdata]=useState(null)
  const [err,seterr]=useState("")
  const [flashes,setflashes]=useState({})
  const last=useRef({})

  useEffect(()=>{
    let live=true
    api.movers({market,by,hours,sector,limit:sector?15:10}).then(d=>{
      if(!live)return
      const f={}
      d.items.concat(d.indices).forEach(i=>{
        const p=last.current[i.symbol]
        if(p!==undefined&&i.price!=null&&p!==i.price)f[i.symbol]=i.price>p?"flash-up":"flash-down"
        if(i.price!=null)last.current[i.symbol]=i.price
      })
      setflashes(f)
      setdata(d)
      seterr("")
    }).catch(e=>{
      if(!live)return
      if(e.status===401)onexpired()
      else seterr("Could not load movers.")
    })
    return()=>{live=false}
  },[market,by,hours,sector,qtick])

  return(
    <section aria-label="Most changed stocks" className="panel p-4">
      <h2 className="sec">{sector?`Most changed in ${sectorlabel(market,sector)}`:"Most changed"}</h2>
      <div className="mt-3">
        <Segmented label="Rank by" options={tabs} value={by} onchange={setby}/>
      </div>
      {err&&<p role="alert" className="mt-3 text-sm text-bear">{err}</p>}
      {data&&data.indices.length>0&&(
        <ul className="mt-4 divide-y divide-rule border-y border-rule text-sm">
          {data.indices.map(i=>(
            <li key={i.symbol} className="flex items-baseline justify-between gap-3 py-1.5">
              <span className="font-medium">{i.name}</span>
              <span className="num">
                <span key={i.price} className={flashes[i.symbol]||""}>{money(i.price,i.currency)}</span>
                <span className={"ml-2 font-semibold "+sign(i.change_pct)}>{pctchange(i.change_pct)}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
      {data&&!data.items.length&&(
        <p className="mt-4 text-sm text-mute">
          {by==="price"&&!data.price_available
            ?(isadmin?"Prices have not loaded yet. They come from Yahoo Finance and start within a minute of the API starting. If this stays empty, check the API log for rate limiting.":"Prices are loading, please wait a moment.")
            :sector?"No stocks in this sector have data in this window yet.":"No movers in this window yet."}
        </p>
      )}
      {data&&data.items.length>0&&(
        <ul className="mt-2 divide-y divide-rule">
          {data.items.map(i=>{
            const t=toneof(i.leaning)
            const main=by==="price"?i.change_pct:i.shift
            return(
              <li key={i.symbol}>
                <button type="button" onClick={()=>onticker(i.symbol)} className="flex w-full items-center justify-between gap-3 py-2.5 text-left hover:bg-paper">
                  <span className="min-w-0">
                    <span className="num block font-semibold">{i.symbol}</span>
                    <span className="block truncate text-xs text-mute">{i.name}</span>
                  </span>
                  <span className="shrink-0 text-right">
                    <span className={"num block font-semibold "+(main==null?"text-mute":sign(main))}>
                      {main==null?"n/a":by==="price"?pctchange(main):signed(main)}
                    </span>
                    <span className="num block text-xs text-mute">
                      {by==="price"
                        ?<span key={i.price} className={flashes[i.symbol]||""}>{money(i.price,i.currency)}</span>
                        :`${i.total} articles`}
                    </span>
                    <span className={"block text-xs font-semibold "+t.text}>{i.total>0?i.leaning:"No news"}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
      <p className="mt-3 flex items-center gap-2 border-t border-rule pt-3 text-xs text-mute">
        {data&&(
          <>
            <span className={"inline-block h-2 w-2 "+(data.market_open?"live-dot bg-bull":"bg-flat")}/>
            <span>
              {data.market_open?"Market open, prices refresh every minute":"Market closed, showing the last close"}
              {data.updated_at?`. Updated ${clock(data.updated_at)}.`:"."}
            </span>
          </>
        )}
      </p>
      <p className="mt-1 text-xs text-mute">
        {by==="price"?"Change since the previous close. Prices can lag by up to 15 minutes.":`Sentiment score now versus the previous ${hours} hours.`}
      </p>
    </section>
  )
}
