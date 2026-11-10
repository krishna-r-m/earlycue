import {useEffect,useState} from "react"
import {api} from "../api.js"
import {timeago} from "../lib.js"

export default function Sources({market,tick}){
  const [rows,setrows]=useState([])
  const [open,setopen]=useState(false)

  useEffect(()=>{
    if(!open)return
    let live=true
    api.sources().then(d=>{
      if(live)setrows(d)
    }).catch(()=>{})
    return()=>{live=false}
  },[open,tick])

  const mine=rows.filter(r=>r.market===market)
  const working=mine.filter(r=>r.ok).length

  return(
    <details onToggle={e=>setopen(e.target.open)} className="border-t border-rule pt-4 text-sm">
      <summary className="cursor-pointer font-semibold">News sources</summary>
      {open&&(
        <div className="mt-3 overflow-x-auto">
          <p className="mb-2 text-mute">{working} of {mine.length} {market==="IN"?"Indian":"US"} feeds answered on the last run.</p>
          <table className="w-full min-w-[34rem] border-collapse text-left">
            <thead>
              <tr className="border-b border-ink text-xs text-mute">
                <th className="py-1 pr-3 font-medium">Source</th>
                <th className="py-1 pr-3 font-medium">Status</th>
                <th className="py-1 pr-3 font-medium">Stories</th>
                <th className="py-1 pr-3 font-medium">New</th>
                <th className="py-1 font-medium">Last success</th>
              </tr>
            </thead>
            <tbody>
              {mine.map(r=>(
                <tr key={r.url} className="border-b border-rule">
                  <td className="py-1.5 pr-3 font-medium">{r.source}</td>
                  <td className={"py-1.5 pr-3 "+(r.ok===true?"text-bull":r.ok===false?"text-bear":"text-mute")}>
                    {r.ok===true?"Working":r.ok===false?(r.error||"Failed"):"Not run yet"}
                  </td>
                  <td className="num py-1.5 pr-3">{r.entries}</td>
                  <td className="num py-1.5 pr-3">{r.new}</td>
                  <td className="py-1.5 text-mute">{r.last_ok_at?timeago(r.last_ok_at):"never"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  )
}
