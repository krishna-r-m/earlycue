import {useState} from "react"

export default function Accordion({items}){
  const [open,setopen]=useState(null)
  return(
    <div className="divide-y divide-rule border-y border-rule">
      {items.map(([q,a],i)=>{
        const on=open===i
        return(
          <div key={q}>
            <button
              type="button"
              aria-expanded={on}
              aria-controls={`faq-${i}`}
              onClick={()=>setopen(on?null:i)}
              className="flex w-full items-center justify-between gap-4 py-3 text-left font-serif text-lg font-semibold"
            >
              {q}
              <span aria-hidden="true" className={"acc-icon "+(on?"is-open":"")}/>
            </button>
            <div id={`faq-${i}`} role="region" className={"acc-panel "+(on?"is-open":"")}>
              <div className="acc-inner">
                <p className="justify-paper max-w-prose pb-3 leading-relaxed">{a}</p>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
