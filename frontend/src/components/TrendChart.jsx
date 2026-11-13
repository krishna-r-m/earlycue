import {ResponsiveContainer,LineChart,Line,XAxis,YAxis,Tooltip,ReferenceLine,CartesianGrid} from "recharts"
import {signed} from "../lib.js"

function fmt(t,granularity){
  const opts=granularity==="day"?{day:"numeric",month:"short"}:{hour:"numeric"}
  return new Date(t).toLocaleString([],opts)
}

function Tip({active,payload}){
  if(!active||!payload||!payload.length)return null
  const p=payload[0].payload
  return(
    <div className="popover px-3 py-2 text-sm">
      <p className="font-semibold">{p.label}</p>
      <p className="num">Score {signed(p.score)}</p>
      <p className="num text-mute">{p.count} articles</p>
    </div>
  )
}

function Dot({cx,cy,payload}){
  if(cx==null||cy==null)return null
  const v=payload.score
  const color=v>0.05?"hsl(var(--bull))":v<-0.05?"hsl(var(--bear))":"hsl(var(--flat))"
  return <circle cx={cx} cy={cy} r={4} style={{fill:color,stroke:"hsl(var(--surface))",strokeWidth:1.5}}/>
}

export default function TrendChart({data,granularity,height=230,label,animate=false}){
  if(!data||data.length<2){
    return(
      <p className="panel p-5 text-sm text-mute">
        {label||"The trend"} needs articles from at least two {granularity==="day"?"days":"hours"}. It fills in as new stories arrive.
      </p>
    )
  }
  const rows=data.map(d=>({...d,label:fmt(d.t,granularity)}))
  return(
    <div className="panel p-4 text-ink" role="img" aria-label={`${label||"Average sentiment"} score over time`}>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={rows} margin={{top:8,right:12,bottom:0,left:-12}}>
          <CartesianGrid stroke="currentColor" strokeOpacity={0.12} vertical={false}/>
          <XAxis dataKey="label" tick={{fontSize:12,fill:"currentColor",fillOpacity:0.65}} tickLine={false} axisLine={{stroke:"currentColor",strokeOpacity:0.4}} minTickGap={24}/>
          <YAxis domain={[-1,1]} ticks={[-1,0,1]} tick={{fontSize:12,fill:"currentColor",fillOpacity:0.65}} tickLine={false} axisLine={false}/>
          <ReferenceLine y={0} stroke="currentColor" strokeOpacity={0.5} strokeDasharray="3 3"/>
          <Tooltip content={<Tip/>} cursor={{stroke:"currentColor",strokeOpacity:0.3}}/>
          <Line type="linear" dataKey="score" stroke="currentColor" strokeWidth={1.75} dot={<Dot/>} activeDot={{r:5}} isAnimationActive={animate} animationDuration={600}/>
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
