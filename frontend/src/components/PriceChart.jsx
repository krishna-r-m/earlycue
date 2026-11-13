import {useEffect,useState} from "react"
import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,Tooltip,ReferenceLine,CartesianGrid} from "recharts"
import {usePrefs} from "../prefs.jsx"
import {money} from "../lib.js"

function axisLabel(t,range){
  const d=new Date(t)
  if(range==="1D")return d.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})
  if(range==="1W")return d.toLocaleDateString([],{weekday:"short"})+" "+d.toLocaleTimeString([],{hour:"2-digit",minute:"2-digit"})
  return d.toLocaleDateString([],range==="1Y"?{day:"numeric",month:"short",year:"2-digit"}:{day:"numeric",month:"short"})
}

function fullLabel(t){
  return new Date(t).toLocaleString([],{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})
}

const compact=new Intl.NumberFormat([],{notation:"compact",maximumFractionDigits:2})

function value(v,currency){
  return currency?money(v,currency):v.toLocaleString([],{maximumFractionDigits:2})
}

export default function PriceChart({points,currency,range,up,animate,height=230}){
  const {theme,look}=usePrefs()
  const [colors,setcolors]=useState({bull:"#2a7a4f",bear:"#b3382c"})

  useEffect(()=>{
    const cs=getComputedStyle(document.documentElement)
    const get=n=>`hsl(${cs.getPropertyValue(n).trim()})`
    setcolors({bull:get("--bull"),bear:get("--bear")})
  },[theme,look])

  const rows=points.map(p=>({label:axisLabel(p.t,range),full:fullLabel(p.t),c:p.c}))

  function Tip({active,payload}){
    if(!active||!payload||!payload.length)return null
    const p=payload[0].payload
    return(
      <div className="popover px-3 py-2 text-sm">
        <p className="font-semibold">{p.full}</p>
        <p className="num">{value(p.c,currency)}</p>
      </div>
    )
  }

  return(
    <div className="panel p-4 text-ink" role="img" aria-label="Price over time">
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={rows} margin={{top:8,right:12,bottom:0,left:4}}>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false}/>
          <XAxis dataKey="label" tick={{fontSize:12,fill:"currentColor",fillOpacity:0.65}} tickLine={false} axisLine={{stroke:"currentColor",strokeOpacity:0.4}} minTickGap={40}/>
          <YAxis domain={["auto","auto"]} width={56} tickFormatter={v=>compact.format(v)} tick={{fontSize:12,fill:"currentColor",fillOpacity:0.65}} tickLine={false} axisLine={false}/>
          {!currency&&<ReferenceLine y={100} stroke="currentColor" strokeOpacity={0.5} strokeDasharray="3 3"/>}
          <Tooltip content={<Tip/>} cursor={{stroke:"currentColor",strokeOpacity:0.3}}/>
          <Line type="linear" dataKey="c" stroke={up?colors.bull:colors.bear} strokeWidth={1.9} dot={false} activeDot={{r:4}} isAnimationActive={animate} animationDuration={600}/>
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
