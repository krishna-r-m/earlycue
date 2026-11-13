import {Suspense,lazy,useEffect,useRef,useState} from "react"
import {api} from "../api.js"
import {usePrefs} from "../prefs.jsx"
import {windows,windowname,markets,timeago,sectorlabel,toneof,signed} from "../lib.js"
import Segmented from "./Segmented.jsx"
import TickerSearch from "./TickerSearch.jsx"
import TiltBar from "./TiltBar.jsx"
import SectorGrid from "./SectorGrid.jsx"
import SectorNews from "./SectorNews.jsx"
import Feed from "./Feed.jsx"
import TickerView from "./TickerView.jsx"
import Movers from "./Movers.jsx"
import Brand from "./Brand.jsx"
import Admin from "./Admin.jsx"
import ProfileMenu from "./ProfileMenu.jsx"

const ChartPanel=lazy(()=>import("./ChartPanel.jsx"))
const windowoptions=windows.map(w=>({value:w.hours,label:w.label}))
const staleminutes=30

function savedmarket(){
  try{
    return localStorage.getItem("mp_market")==="US"?"US":"IN"
  }catch{
    return "IN"
  }
}

const today=new Intl.DateTimeFormat("en-GB",{weekday:"long",day:"numeric",month:"long",year:"numeric"}).format(new Date())

export default function Dashboard({user,onsignout,onexpired}){
  const isadmin=user.role==="admin"
  const {motion}=usePrefs()
  const [market,setmarket]=useState(savedmarket)
  const [hours,sethours]=useState(24)
  const [sector,setsector]=useState(null)
  const [filter,setfilter]=useState(null)
  const [pulse,setpulse]=useState(null)
  const [articles,setarticles]=useState({items:[],total:0})
  const [loading,setloading]=useState(true)
  const [error,seterror]=useState("")
  const [symbol,setsymbol]=useState(null)
  const [note,setnote]=useState("")
  const [tick,settick]=useState(0)
  const [qtick,setqtick]=useState(0)
  const [qstatus,setqstatus]=useState(null)
  const [live,setlive]=useState(null)
  const seen=useRef({news:"",prices:""})
  const feedref=useRef(null)
  const graphref=useRef(null)
  const adminref=useRef(null)

  function fail(e,alive){
    if(!alive)return
    if(e.status===401)onexpired()
  }

  useEffect(()=>{
    function check(){
      if(document.hidden)return
      api.health().then(h=>{
        const news=String(h.scored_at)
        const prices=String(h.quotes_at)
        if(seen.current.news&&seen.current.news!==news)settick(t=>t+1)
        if(seen.current.prices&&seen.current.prices!==prices)setqtick(t=>t+1)
        seen.current={news,prices}
        setlive(h)
      }).catch(()=>{})
    }
    check()
    const id=setInterval(check,15000)
    document.addEventListener("visibilitychange",check)
    return()=>{
      clearInterval(id)
      document.removeEventListener("visibilitychange",check)
    }
  },[])

  useEffect(()=>{
    let alive=true
    api.pulse(market,hours,sector).then(d=>{
      if(alive){
        setpulse(d)
        seterror("")
      }
    }).catch(e=>{
      fail(e,alive)
      if(alive&&e.status!==401)seterror(isadmin?"Cannot reach the API. Check that the backend is running on port 8000.":"We could not load the latest data. Please try again in a moment.")
    })
    return()=>{alive=false}
  },[market,hours,sector,tick])

  useEffect(()=>{
    let alive=true
    api.articles({market,hours,sector,sentiment:filter,limit:50}).then(d=>{
      if(alive){
        setarticles(d)
        setloading(false)
      }
    }).catch(e=>{
      fail(e,alive)
      if(alive)setloading(false)
    })
    return()=>{alive=false}
  },[market,hours,sector,filter,tick])

  useEffect(()=>{
    if(!isadmin)return
    let alive=true
    api.status().then(d=>{
      if(alive)setqstatus(d)
    }).catch(()=>{
      if(alive)setqstatus(null)
    })
    return()=>{alive=false}
  },[tick])

  function pickmarket(m){
    setmarket(m)
    setsector(null)
    setsymbol(null)
    setpulse(null)
    setloading(true)
    try{
      localStorage.setItem("mp_market",m)
    }catch{}
  }

  function home(){
    setsymbol(null)
    setsector(null)
    setfilter(null)
    sethours(24)
    window.scrollTo({top:0})
  }

  function picksector(s){
    setsector(s)
    setfilter(null)
    if(!s)return
    setTimeout(()=>{
      const el=graphref.current
      if(!el)return
      const r=el.getBoundingClientRect()
      if(r.top>=0&&r.bottom<=window.innerHeight)return
      el.scrollIntoView({behavior:motion==="on"?"smooth":"auto",block:"start"})
    },80)
  }

  function seeall(){
    if(feedref.current)feedref.current.scrollIntoView({behavior:motion==="on"?"smooth":"auto",block:"start"})
  }

  function gotoadmin(){
    setsymbol(null)
    setTimeout(()=>adminref.current&&adminref.current.scrollIntoView({behavior:motion==="on"?"smooth":"auto",block:"start"}),60)
  }

  function openticker(s){
    setsymbol(s)
    window.scrollTo({top:0})
  }

  async function refresh(){
    setnote(isadmin?"Starting a fetch...":"Refreshing, please wait...")
    try{
      const res=isadmin?await api.refresh():await api.userRefresh()
      setnote(res.detail)
      setTimeout(()=>settick(t=>t+1),20000)
      setTimeout(()=>settick(t=>t+1),60000)
    }catch(e){
      if(e.status===401)onexpired()
      else setnote(isadmin?"Could not reach the API to start a fetch.":"We could not refresh just now. Please try again in a moment.")
    }
  }

  const sectorname=sector?sectorlabel(market,sector):null
  const stats=pulse&&pulse.sector?pulse.sector_stats:null
  const newsage=live&&live.scored_at?(Date.now()-new Date(live.scored_at).getTime())/60000:null
  const catchingup=newsage!==null&&newsage>staleminutes
  const hasright=pulse?(sector?articles.items.length>0:pulse.top_tickers.length>0):false

  const mentioned=pulse&&pulse.top_tickers.length>0&&(
    <section>
      <h2 className="sec">{sector?`${sectorname} stocks in the news`:"Most mentioned"}</h2>
      <div className="mt-3 flex flex-wrap gap-2">
        {pulse.top_tickers.map(t=>{
          const tt=toneof(t.leaning)
          return(
            <button
              key={t.symbol}
              type="button"
              onClick={()=>openticker(t.symbol)}
              className={"border border-ink px-2.5 py-1 text-sm "+(sector?"bg-mark text-on-mark":"bg-surface hover:bg-mark hover:text-on-mark")}
            >
              <span className="num font-semibold">{t.symbol}</span>
              <span className="num ml-2 opacity-70">{t.total}</span>
              <span className={"ml-2 text-xs font-semibold "+(sector?"":tt.text)}>{t.leaning}</span>
            </button>
          )
        })}
      </div>
    </section>
  )

  return(
    <div className="mx-auto max-w-[96rem] px-4 pb-16 sm:px-6 lg:px-8">
      <header className="pt-4">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-rule pb-2">
          <p className="dateline text-sm text-mute">{today}</p>
          <p className="num flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-mute" role="status">
            {live&&live.articles>0&&<span>{live.articles.toLocaleString()} stories indexed</span>}
            {live&&live.scored_at&&!catchingup&&(
              <span className="flex items-center gap-2">
                <span className="live-dot inline-block h-2 w-2 bg-bull"/>
                Updated {timeago(live.scored_at)}
              </span>
            )}
            {catchingup&&<span className="text-flat">We are catching up on the latest stories. Please wait a few minutes.</span>}
            {live&&live.quotes_at&&<span>Prices {timeago(live.quotes_at)}</span>}
            {isadmin&&qstatus&&(
              <span className="flex items-center gap-2">
                <span className={"inline-block h-2 w-2 "+(qstatus.state==="ok"?"bg-bull":qstatus.state==="down"?"bg-bear":"bg-flat")}/>
                {qstatus.detail}
              </span>
            )}
          </p>
        </div>
        <div className="flex justify-center py-4">
          <Brand onclick={home} size="h-12 w-12" text="text-5xl sm:text-6xl"/>
        </div>
        <div className="masthead-rule"/>
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-3 border-b border-rule py-3">
          <p className="dateline text-sm text-mute">{market==="IN"?"Indian":"US"} markets edition</p>
          <div className="flex flex-wrap items-center gap-3">
            <Segmented label="Market" options={markets} value={market} onchange={pickmarket}/>
            <TickerSearch onpick={openticker} market={market}/>
            <ProfileMenu user={user} market={market} onmarket={pickmarket} onrefresh={refresh} onhome={home} onsignout={onsignout} onadmin={gotoadmin}/>
          </div>
        </div>
      </header>

      {error&&<p role="alert" className="mt-6 border border-bear p-4 text-sm text-bear">{error}</p>}

      <div className="grid gap-9 pt-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div>
          {symbol?(
            <TickerView symbol={symbol} market={market} qtick={qtick} onback={()=>setsymbol(null)} onticker={openticker} onexpired={onexpired}/>
          ):(
            <main>
              <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
                <Segmented label="Time window" options={windowoptions} value={hours} onchange={sethours}/>
                <div className="flex flex-wrap items-center gap-3">
                  {note&&<p role="status" className="text-sm text-mute">{note}</p>}
                  <button type="button" onClick={refresh} className="border border-ink px-3 py-1 text-sm font-medium hover:bg-mark hover:text-on-mark">Refresh</button>
                </div>
              </div>

              <div className="articles">
                {pulse?(
                  <>
                    <div className="article wide fade-in">
                      <TiltBar title={`${market==="IN"?"Indian":"US"} market sentiment over the last ${windowname(hours)}`} stats={pulse.overall}/>
                    </div>
                    <div className="article wide fade-in">
                      <SectorGrid sectors={pulse.sectors} active={sector} onpick={picksector} market={market}/>
                    </div>
                    {sector&&(
                      <div className="article wide">
                        <p className="fade-in flex flex-wrap items-center justify-between gap-3 bg-mark px-4 py-2.5 text-sm text-on-mark">
                          <span>
                            Focused on <strong>{sectorname}</strong>
                            {stats&&stats.total>0&&<span className="num"> · {stats.leaning} {signed(stats.score)} · {stats.total} articles</span>}
                          </span>
                          <button type="button" onClick={()=>picksector(null)} className="font-semibold underline underline-offset-2">Show all sectors</button>
                        </p>
                      </div>
                    )}
                    <div ref={graphref} className={"article scroll-mt-4 "+(hasright?"left":"wide")}>
                      <Suspense fallback={<div className="skeleton h-72 w-full"/>}>
                          <ChartPanel
                            sentimentTitle={sector?`${sectorname} sentiment trend`:`${market==="IN"?"Indian":"US"} market sentiment trend`}
                            priceTitle={sector?`${sectorname} price index`:(market==="IN"?"Nifty 50":"S&P 500")}
                            sentiment={{data:pulse.trend,granularity:pulse.granularity}}
                            price={sector?{kind:"sector",market,sector,defaultrange:"1M",note:"Equal-weighted index of the sector's largest stocks, starting at 100."}:{kind:"market",symbol:market==="IN"?"NIFTY":"SPX",defaultrange:hours===24?"1D":"1W"}}
                            animate={motion==="on"}
                          />
                        </Suspense>
                    </div>
                    {hasright&&(
                      <div className="article right">
                        {sector?<SectorNews name={sectorname} items={articles.items.slice(0,5)} total={articles.total} onall={seeall}/>:mentioned}
                      </div>
                    )}
                    {sector&&mentioned&&<div className="article wide">{mentioned}</div>}
                  </>
                ):!error&&(
                  <div className="article wide space-y-4" aria-busy="true">
                    <p className="text-sm text-mute">Please wait, we are gathering today's stories...</p>
                    <div className="skeleton h-28 w-full"/>
                    <div className="skeleton h-40 w-full"/>
                  </div>
                )}
                <div className="article wide">
                  <Feed
                    items={articles.items}
                    loading={loading}
                    filter={filter}
                    onfilter={setfilter}
                    onticker={openticker}
                    market={market}
                    title={sector?`${sectorname} news`:"Latest news"}
                    stats={stats}
                    feedref={feedref}
                    empty={sector?`No ${filter||""} ${sectorname} stories in this window yet. Try a longer window.`:undefined}
                  />
                </div>
                {isadmin&&(
                  <div ref={adminref} className="article wide scroll-mt-4">
                    <Admin tick={tick} qstatus={qstatus} note={note} onrefresh={refresh}/>
                  </div>
                )}
              </div>
            </main>
          )}
        </div>
        <aside className="lg:sticky lg:top-4 lg:self-start lg:border-l lg:border-rule lg:pl-8">
          <Movers market={market} hours={hours} sector={symbol?null:sector} qtick={qtick} onticker={openticker} onexpired={onexpired} isadmin={isadmin}/>
        </aside>
      </div>
    </div>
  )
}
