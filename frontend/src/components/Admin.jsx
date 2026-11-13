import {useEffect,useState} from "react"
import {api} from "../api.js"
import {timeago} from "../lib.js"

function Status({r}){
  if(r.ok===null)return <span className="text-mute">Not run yet</span>
  if(r.ok&&!r.partial)return <span className="text-bull">Working</span>
  if(r.ok&&r.partial)return <span className="text-flat">{r.error}</span>
  return <span className="text-bear">{r.error||"Failed"}</span>
}

function SourceTable({rows,title}){
  if(!rows.length)return null
  return(
    <div className="mt-5 overflow-x-auto">
      <h3 className="font-serif text-base font-bold">{title}</h3>
      <table className="mt-1 w-full min-w-[40rem] border-collapse text-left text-sm">
        <thead>
          <tr className="border-b border-ink text-xs text-mute">
            <th className="py-1 pr-3 font-medium">Source</th>
            <th className="py-1 pr-3 font-medium">Market</th>
            <th className="py-1 pr-3 font-medium">Status</th>
            <th className="py-1 pr-3 font-medium">Stories</th>
            <th className="py-1 pr-3 font-medium">New</th>
            <th className="py-1 font-medium">Last success</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r=>(
            <tr key={r.url} className="border-b border-rule align-top">
              <td className="py-1.5 pr-3 font-medium">{r.source}</td>
              <td className="py-1.5 pr-3">{r.market}</td>
              <td className="py-1.5 pr-3"><Status r={r}/></td>
              <td className="num py-1.5 pr-3">{r.entries}</td>
              <td className="num py-1.5 pr-3">{r.new}</td>
              <td className="py-1.5 text-mute">{r.last_ok_at?timeago(r.last_ok_at):"never"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Admin({tick,qstatus,note,onrefresh}){
  const [ov,setov]=useState(null)
  const [src,setsrc]=useState([])
  const [users,setusers]=useState([])
  const [beat,setbeat]=useState(0)
  const [cleaned,setcleaned]=useState("")

  useEffect(()=>{
    const id=setInterval(()=>setbeat(b=>b+1),30000)
    return()=>clearInterval(id)
  },[])

  useEffect(()=>{
    let live=true
    Promise.all([api.adminOverview(),api.sources(),api.adminUsers()]).then(([a,b,c])=>{
      if(live){
        setov(a)
        setsrc(b)
        setusers(c)
      }
    }).catch(()=>{})
    return()=>{live=false}
  },[tick,beat])

  async function cleanup(){
    setcleaned("Cleaning up...")
    try{
      const r=await api.cleanup()
      setcleaned(`Removed ${r.removed.toLocaleString()} old or unrelated stories. ${r.articles.toLocaleString()} remain.`)
      setbeat(b=>b+1)
    }catch{
      setcleaned("Cleanup failed.")
    }
  }

  const stats=ov?[
    ["Stories stored",ov.articles],
    ["Scored",ov.scored],
    ["Waiting to be scored",ov.pending],
    ["Added in 24 hours",ov.added_24h],
    ["India stories",ov.in_articles],
    ["US stories",ov.us_articles],
    ["Users",ov.users],
    ["Price quotes",ov.quotes],
    ["Listed stocks",ov.instruments]
  ]:[]
  const working=src.filter(r=>!r.group&&r.ok).length
  const feeds=src.filter(r=>!r.group)

  return(
    <section aria-label="Admin console" className="border-t-2 border-ink pt-3">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="font-serif text-xl font-bold">Admin console</h2>
        <div className="flex flex-wrap items-center gap-3">
          {note&&<p role="status" className="text-sm text-mute">{note}</p>}
          <button type="button" onClick={onrefresh} className="bg-ink px-3.5 py-1.5 text-sm font-semibold text-paper hover:bg-mark hover:text-on-mark">
            Refresh data and deep crawl
          </button>
          <button type="button" onClick={cleanup} className="border border-ink px-3.5 py-1.5 text-sm font-medium hover:bg-mark hover:text-on-mark">
            Clean up storage
          </button>
        </div>
      </div>
      {cleaned&&<p role="status" className="mt-2 text-sm text-mute">{cleaned}</p>}
      <p className="mt-2 flex items-center gap-2 text-sm text-mute">
        {qstatus&&(
          <>
            <span className={"inline-block h-2 w-2 "+(qstatus.state==="ok"?"bg-bull":qstatus.state==="down"?"bg-bear":"bg-flat")}/>
            {qstatus.detail}
          </>
        )}
      </p>
      {ov&&(
        <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
          {stats.map(([k,v])=>(
            <div key={k} className="border-t border-rule pt-1.5">
              <dt className="text-xs text-mute">{k}</dt>
              <dd className="num text-xl font-semibold">{v.toLocaleString()}</dd>
            </div>
          ))}
        </dl>
      )}
      {ov&&(
        <p className="num mt-3 text-xs text-mute">
          Database: {ov.db_engine}. {working} of {feeds.length} direct feeds answered on the last run.
          {ov.quote_backoff_seconds>0?` Price fetching is backing off for ${ov.quote_backoff_seconds}s.`:""}
        </p>
      )}
      <SourceTable rows={src.filter(r=>r.group)} title="Deep crawl groups"/>
      <SourceTable rows={feeds} title="Direct feeds"/>
      {users.length>0&&(
        <div className="mt-5 overflow-x-auto">
          <h3 className="font-serif text-base font-bold">Users</h3>
          <table className="mt-1 w-full min-w-[34rem] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-ink text-xs text-mute">
                <th className="py-1 pr-3 font-medium">Email</th>
                <th className="py-1 pr-3 font-medium">Name</th>
                <th className="py-1 pr-3 font-medium">Role</th>
                <th className="py-1 pr-3 font-medium">Google</th>
                <th className="py-1 font-medium">Joined</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u=>(
                <tr key={u.id} className="border-b border-rule">
                  <td className="py-1.5 pr-3">{u.email}</td>
                  <td className="py-1.5 pr-3">{u.name}</td>
                  <td className="py-1.5 pr-3 font-medium">{u.role}</td>
                  <td className="py-1.5 pr-3">{u.google?"yes":"no"}</td>
                  <td className="py-1.5 text-mute">{u.created_at?timeago(u.created_at):""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
