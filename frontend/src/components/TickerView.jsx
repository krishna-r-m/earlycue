import {Suspense,lazy,useEffect,useState} from "react"
import {api} from "../api.js"
import TiltBar from "./TiltBar.jsx"
import {usePrefs} from "../prefs.jsx"
const ChartPanel=lazy(()=>import("./ChartPanel.jsx"))
import Feed from "./Feed.jsx"
import {money,pctchange,sign,sectorlabel} from "../lib.js"

export default function TickerView({symbol,market,qtick,onback,onticker,onexpired}){
  const [data,setdata]=useState(null)
  const [err,seterr]=useState("")
  const [filter,setfilter]=useState(null)
  const {motion}=usePrefs()

  function failed(e){
    if(e.status===401)onexpired()
    else seterr(e.status===404?`No stored news for ${symbol} yet. Try a company from the search suggestions.`:"Could not load this ticker.")
  }

  useEffect(()=>{
    let live=true
    setdata(null)
    seterr("")
    setfilter(null)
    api.ticker(symbol,30).then(d=>{
      if(live)setdata(d)
    }).catch(e=>{
      if(live)failed(e)
    })
    return()=>{live=false}
  },[symbol])

  useEffect(()=>{
    if(!qtick)return
    let live=true
    api.ticker(symbol,30).then(d=>{
      if(live)setdata(d)
    }).catch(()=>{})
    return()=>{live=false}
  },[qtick])

  const items=data?data.articles.filter(a=>!filter||(a.sentiment||"").toLowerCase()===filter):[]

  return(
    <main className="space-y-8">
      <button type="button" onClick={onback} className="link text-sm font-semibold">
        Back to the overview
      </button>
      {err&&<p role="alert" className="panel p-5 text-sm">{err}</p>}
      {!err&&!data&&<p className="text-sm text-mute">Loading {symbol}...</p>}
      {data&&(
        <>
          <header className="border-t-2 border-ink pt-3">
            <h2 className="num text-4xl font-semibold">{data.symbol}</h2>
            <p className="mt-1 text-mute">{data.name||"Unlisted entity"}{data.sector?`, ${sectorlabel(market,data.sector)}`:""}</p>
            {data.quote&&(
              <p className="num mt-2 text-xl">
                {money(data.quote.price,data.quote.currency)}
                <span className={"ml-3 font-semibold "+sign(data.quote.change_pct)}>{pctchange(data.quote.change_pct)}</span>
              </p>
            )}
          </header>
          <TiltBar title={`Sentiment for ${data.symbol} over the last ${data.days} days`} stats={data.stats}/>
          <Suspense fallback={<div className="skeleton h-72 w-full"/>}>
            <ChartPanel
              sentimentTitle={`${data.symbol} sentiment trend`}
              priceTitle={`${data.symbol} price`}
              sentiment={{data:data.stats.total>0?data.trend:[],granularity:"day"}}
              price={{kind:"stock",symbol:data.symbol,defaultrange:"1M"}}
              animate={motion==="on"}
            />
          </Suspense>
          <Feed
            items={items}
            loading={false}
            filter={filter}
            onfilter={setfilter}
            onticker={onticker}
            market={market}
            title={`News mentioning ${data.symbol}`}
            empty={`No ${filter||""} articles mention ${data.symbol} in this period.`}
          />
        </>
      )}
    </main>
  )
}
