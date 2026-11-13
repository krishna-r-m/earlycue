export const tone={
  Bullish:{text:"text-bull",bg:"bg-bull",tag:"text-bull"},
  Bearish:{text:"text-bear",bg:"bg-bear",tag:"text-bear"},
  Neutral:{text:"text-flat",bg:"bg-flat",tag:"text-flat"}
}

export const toneof=label=>tone[label]||tone.Neutral

export const windows=[
  {label:"24h",hours:24},
  {label:"3d",hours:72},
  {label:"7d",hours:168}
]

export const windowname=h=>h===24?"24 hours":h===72?"3 days":"7 days"

export function timeago(iso){
  if(!iso)return ""
  const s=Math.max(0,Math.floor((Date.now()-new Date(iso).getTime())/1000))
  if(s<45)return "just now"
  if(s<3600)return Math.max(1,Math.floor(s/60))+"m ago"
  if(s<86400)return Math.floor(s/3600)+"h ago"
  return Math.floor(s/86400)+"d ago"
}

export const clock=iso=>iso?new Date(iso).toLocaleTimeString([],{hour:"2-digit",minute:"2-digit",second:"2-digit"}):""

export const pct=v=>v==null?"":Math.round(v*100)+"%"

export const signed=v=>(v>0?"+":"")+v.toFixed(2)

export const markets=[
  {value:"IN",label:"India"},
  {value:"US",label:"US"}
]

const usnames={IT:"Technology",Banking:"Financials",Pharma:"Healthcare",FMCG:"Consumer",Infrastructure:"Industrials"}

export const sectorlabel=(market,s)=>market==="US"&&usnames[s]?usnames[s]:s

const marks={INR:"₹",USD:"$"}

export function money(v,cur){
  if(v==null)return ""
  const text=new Intl.NumberFormat(cur==="INR"?"en-IN":"en-US",{maximumFractionDigits:2}).format(v)
  return (marks[cur]||"")+text
}

export const pctchange=v=>(v>0?"+":"")+v.toFixed(2)+"%"

export const sign=v=>v>0?"text-bull":v<0?"text-bear":"text-flat"
