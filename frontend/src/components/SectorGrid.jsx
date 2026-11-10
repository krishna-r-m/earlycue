import {tone,toneof,signed,sectorlabel} from "../lib.js"

export default function SectorGrid({sectors,active,onpick,market}){
  return(
    <section aria-label="Sectors">
      <h2 className="sec">Sectors</h2>
      <p className="mt-1 text-sm text-mute">Pick a sector to focus the trend, the stocks and the news on it.</p>
      <div className="mt-3 grid border-l border-t border-rule sm:grid-cols-2 xl:grid-cols-3">
        {sectors.map(s=>{
          const t=toneof(s.leaning)
          const on=active===s.sector
          const total=s.total||1
          return(
            <button
              key={s.sector}
              type="button"
              aria-pressed={on}
              onClick={()=>onpick(on?null:s.sector)}
              className={"border-b border-r border-rule p-3.5 text-left "+(on?"bg-mark text-on-mark":"bg-surface hover:bg-paper")}
            >
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-serif text-base font-bold">{sectorlabel(market,s.sector)}</span>
                {s.total>0?(
                  <span className={"text-sm font-semibold "+(on?"":t.text)}>{s.leaning}</span>
                ):(
                  <span className={"text-sm "+(on?"":"text-mute")}>No data</span>
                )}
              </div>
              <div className="mt-2.5 flex h-1.5 gap-px bg-rule/60">
                {s.total>0&&[["Bearish",s.bearish],["Neutral",s.neutral],["Bullish",s.bullish]].map(([k,n])=>n>0&&(
                  <div key={k} className={on?"bg-on-mark":tone[k].bg} style={{width:`${n/total*100}%`,opacity:on&&k==="Neutral"?.35:1}}/>
                ))}
              </div>
              <p className={"num mt-2 text-xs "+(on?"":"text-mute")}>
                {s.total>0?`${s.total} articles, score ${signed(s.score)}`:"No articles in this window"}
              </p>
            </button>
          )
        })}
      </div>
    </section>
  )
}
