import {useEffect,useState} from "react"
import {api} from "../api.js"
import Segmented from "./Segmented.jsx"
import TrendChart from "./TrendChart.jsx"
import PriceChart from "./PriceChart.jsx"
import {money,pctchange,sign} from "../lib.js"

const ranges=["1D","1W","1M","3M","1Y"].map(v=>({value:v,label:v}))
const rangewords={"1D":"the day","1W":"the week","1M":"the month","3M":"3 months","1Y":"the year"}
const modes=[{value:"sentiment",label:"Sentiment"},{value:"price",label:"Price"}]

export default function ChartPanel({sentimentTitle,priceTitle,sentiment,price,animate}){
  const [range,setrange]=useState(price.defaultrange||"1M")
  const [hist,sethist]=useState(undefined)
  const [mode,setmode]=useState(null)

  useEffect(()=>{
    setrange(price.defaultrange||"1M")
  },[price.defaultrange,price.kind,price.symbol,price.sector,price.market])

  useEffect(()=>{
    let live=true
    sethist(undefined)
    const call=price.kind==="sector"?api.sectorHistory(price.sector,price.market,range):api.history(price.symbol,range)
    call.then(d=>{
      if(live)sethist(d)
    }).catch(()=>{
      if(live)sethist(null)
    })
    return()=>{live=false}
  },[price.kind,price.symbol,price.sector,price.market,range])

  const hasSent=!!sentiment.data&&sentiment.data.length>=2
  const loading=hist===undefined
  const hasPrice=!!hist&&hist.available&&hist.points.length>=2

  let shown
  if(mode==="price"&&(hasPrice||loading))shown="price"
  else if(mode==="sentiment"&&hasSent)shown="sentiment"
  else shown=hasSent?"sentiment":"price"

  const both=hasSent&&hasPrice

  return(
    <section>
      <h2 className="sec">{shown==="price"?priceTitle:sentimentTitle}</h2>
      <div className="mb-3 mt-3 flex flex-wrap items-center justify-between gap-3">
        {both?<Segmented label="Chart type" options={modes} value={shown} onchange={setmode}/>:<span/>}
        {shown==="price"&&<Segmented label="Price range" options={ranges} value={range} onchange={setrange}/>}
      </div>
      {shown==="sentiment"&&(
        <TrendChart data={sentiment.data} granularity={sentiment.granularity} label={sentimentTitle} animate={animate}/>
      )}
      {shown==="price"&&loading&&<div className="skeleton h-56 w-full"/>}
      {shown==="price"&&!loading&&hasPrice&&(
        <>
          <p className="num mb-2 text-sm">
            {hist.currency?money(hist.last,hist.currency):hist.last.toLocaleString([],{maximumFractionDigits:2})}
            {hist.change_pct!=null&&<span className={"ml-3 font-semibold "+sign(hist.change_pct)}>{pctchange(hist.change_pct)}</span>}
            <span className="ml-2 text-mute">over {rangewords[range]}</span>
          </p>
          <PriceChart points={hist.points} currency={hist.currency} range={range} up={(hist.change_pct||0)>=0} animate={animate}/>
          {price.kind==="sector"&&hist.basket.length>0&&(
            <p className="mt-2 text-xs text-mute">{price.note} Basket: {hist.basket.join(", ")}.</p>
          )}
        </>
      )}
      {shown==="price"&&!loading&&!hasPrice&&(
        <p className="panel p-5 text-sm text-mute">
          {hasSent
            ?"Price history is not available for this range right now."
            :"There is no news sentiment for this yet, and price history is not available right now. Please try again in a moment."}
        </p>
      )}
    </section>
  )
}
