import {toneof,tone,signed} from "../lib.js"

export default function TiltBar({title,stats}){
  const total=stats.total||1
  const parts=[["Bearish",stats.bearish],["Neutral",stats.neutral],["Bullish",stats.bullish]]
  const t=toneof(stats.leaning)
  return(
    <section className="boxed p-5">
      <h2 className="text-sm font-medium text-mute">{title}</h2>
      <div className="mt-1 flex flex-wrap items-baseline justify-between gap-x-8 gap-y-1">
        <p className={"font-serif text-5xl font-bold leading-tight tracking-tight sm:text-6xl "+t.text}>
          {stats.total?stats.leaning:"No data yet"}
          {stats.total>0&&<span className="num ml-4 text-2xl font-medium text-mute">{signed(stats.score)}</span>}
        </p>
        <p className="num text-sm text-mute">{stats.total} articles scored</p>
      </div>
      <div
        className="mt-4 flex h-3 gap-0.5"
        role="img"
        aria-label={`${stats.bearish} bearish, ${stats.neutral} neutral, ${stats.bullish} bullish`}
      >
        {stats.total===0&&<div className="h-full w-full bg-rule"/>}
        {parts.map(([k,n])=>n>0&&(
          <div key={k} className={"bar-seg h-full "+tone[k].bg} style={{width:`${n/total*100}%`}}/>
        ))}
      </div>
      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
        {parts.map(([k,n])=>(
          <div key={k} className="flex items-baseline gap-2">
            <span className={"inline-block h-2.5 w-2.5 "+tone[k].bg}/>
            <dt className="text-mute">{k}</dt>
            <dd className="num font-semibold">{n}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
