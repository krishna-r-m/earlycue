import {useEffect,useRef,useState} from "react"
import {api} from "../api.js"

export default function TickerSearch({onpick,market}){
  const [q,setq]=useState("")
  const [opts,setopts]=useState([])
  const [open,setopen]=useState(false)
  const [idx,setidx]=useState(-1)
  const [done,setdone]=useState("")
  const box=useRef(null)

  useEffect(()=>{
    const term=q.trim()
    if(!term){
      setopts([])
      setdone("")
      return
    }
    const id=setTimeout(()=>{
      api.search(term,market).then(r=>{
        setopts(r)
        setidx(-1)
        setdone(term)
      }).catch(()=>{
        setopts([])
        setdone(term)
      })
    },180)
    return()=>clearTimeout(id)
  },[q,market])

  useEffect(()=>{
    const close=e=>{
      if(box.current&&!box.current.contains(e.target))setopen(false)
    }
    document.addEventListener("mousedown",close)
    return()=>document.removeEventListener("mousedown",close)
  },[])

  function choose(symbol){
    setq("")
    setopts([])
    setopen(false)
    onpick(symbol)
  }

  function onkey(e){
    if(e.key==="ArrowDown"){
      e.preventDefault()
      setidx(i=>Math.min(i+1,opts.length-1))
    }else if(e.key==="ArrowUp"){
      e.preventDefault()
      setidx(i=>Math.max(i-1,0))
    }else if(e.key==="Enter"){
      const pick=opts[idx]||opts[0]
      if(pick)choose(pick.symbol)
      else if(q.trim())choose(q.trim().toUpperCase())
    }else if(e.key==="Escape"){
      setopen(false)
    }
  }

  const showlist=open&&opts.length>0
  const nomatch=open&&opts.length===0&&done!==""&&done===q.trim()

  return(
    <div ref={box} className="relative w-full sm:w-72">
      <input
        type="search"
        value={q}
        onChange={e=>{setq(e.target.value);setopen(true)}}
        onFocus={()=>setopen(true)}
        onKeyDown={onkey}
        placeholder={market==="US"?"Search a US company or ticker":"Search an Indian company or ticker"}
        aria-label="Search a company or ticker"
        role="combobox"
        aria-expanded={showlist}
        aria-controls="ticker-options"
        aria-autocomplete="list"
        className="w-full border border-ink bg-surface px-3 py-1.5 text-sm placeholder:text-mute"
      />
      {nomatch&&(
        <p className="panel absolute z-20 mt-1 w-full px-3 py-2 text-sm text-mute">
          No listed company matches. Press Enter to look up {q.trim().toUpperCase()} directly.
        </p>
      )}
      {showlist&&(
        <ul id="ticker-options" role="listbox" className="panel absolute z-20 mt-1 w-full divide-y divide-rule">
          {opts.map((o,i)=>(
            <li
              key={o.symbol}
              role="option"
              aria-selected={i===idx}
              onMouseDown={()=>choose(o.symbol)}
              className={"flex cursor-pointer items-baseline justify-between gap-3 px-3 py-2 text-sm "+(i===idx?"bg-mark text-on-mark":"hover:bg-paper")}
            >
              <span className="num font-semibold">{o.symbol}</span>
              <span className="flex min-w-0 items-baseline gap-2">
                <span className="truncate">{o.name}</span>
                <span className="num shrink-0 text-xs opacity-70">{o.market==="US"?"US":"IN"}</span>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
