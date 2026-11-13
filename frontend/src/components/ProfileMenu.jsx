import {useEffect,useRef,useState} from "react"
import Segmented from "./Segmented.jsx"
import {usePrefs} from "../prefs.jsx"

const themes=[{value:"light",label:"Light"},{value:"dark",label:"Dark"}]
const looks=[{value:"paper",label:"Newspaper"},{value:"classic",label:"Original"}]
const sizes=[{value:"small",label:"A-"},{value:"medium",label:"A"},{value:"large",label:"A+"}]
const motions=[{value:"on",label:"On"},{value:"off",label:"Off"}]
const marketopts=[{value:"IN",label:"India"},{value:"US",label:"US"}]

function initials(user){
  const base=(user.name||user.email||"?").trim()
  const parts=base.split(/\s+/)
  return ((parts[0][0]||"")+(parts.length>1?parts[parts.length-1][0]:"")).toUpperCase()
}

function Person(){
  return(
    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.6">
      <circle cx="12" cy="8.5" r="3.6"/>
      <path d="M4.5 20c.7-3.9 3.8-6 7.5-6s6.8 2.1 7.5 6"/>
    </svg>
  )
}

function Row({label,children}){
  return(
    <div className="px-4 py-2">
      <p className="mb-1 text-xs text-mute">{label}</p>
      {children}
    </div>
  )
}

const item="block w-full px-4 py-2 text-left text-sm font-medium hover:bg-mark hover:text-on-mark"

export default function ProfileMenu({user,market,onmarket,onrefresh,onhome,onsignout,onsignin,onsignup,onadmin}){
  const [open,setopen]=useState(false)
  const [broken,setbroken]=useState(false)
  const ref=useRef(null)
  const {theme,settheme,look,setlook,size,setsize,motion,setmotion}=usePrefs()

  useEffect(()=>{
    if(!open)return
    const away=e=>{
      if(ref.current&&!ref.current.contains(e.target))setopen(false)
    }
    const esc=e=>{
      if(e.key==="Escape")setopen(false)
    }
    document.addEventListener("mousedown",away)
    document.addEventListener("keydown",esc)
    return()=>{
      document.removeEventListener("mousedown",away)
      document.removeEventListener("keydown",esc)
    }
  },[open])

  function act(fn){
    return()=>{
      setopen(false)
      fn&&fn()
    }
  }

  const photo=user&&user.picture&&!broken

  return(
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label="Account and preferences"
        onClick={()=>setopen(o=>!o)}
        className={"flex h-9 w-9 items-center justify-center overflow-hidden rounded-full border border-ink "+(open?"bg-mark text-on-mark":"bg-surface hover:bg-mark hover:text-on-mark")}
      >
        {photo?(
          <img src={user.picture} alt="" referrerPolicy="no-referrer" loading="lazy" onError={()=>setbroken(true)} className="h-full w-full object-cover"/>
        ):user?(
          <span className="font-serif text-sm font-bold">{initials(user)}</span>
        ):<Person/>}
      </button>
      {open&&(
        <div role="dialog" aria-label="Account and preferences" className="menu-in popover absolute right-0 z-40 mt-2 max-h-[80vh] w-72 max-w-[calc(100vw-2rem)] overflow-y-auto py-1">
          {user?(
            <div className="border-b border-rule px-4 py-3">
              <p className="truncate font-serif text-base font-bold">{user.name||user.email}</p>
              <p className="truncate text-xs text-mute">{user.email}</p>
              {user.role==="admin"&&<span className="tag mt-1.5 text-mute">Admin</span>}
            </div>
          ):(
            <div className="border-b border-rule py-1">
              <button type="button" className={item} onClick={act(onsignin)}>Sign in</button>
              <button type="button" className={item} onClick={act(onsignup)}>Create an account</button>
            </div>
          )}
          <div className="border-b border-rule py-1">
            <Row label="Colour"><Segmented block label="Colour theme" options={themes} value={theme} onchange={settheme}/></Row>
            <Row label="Layout"><Segmented block label="Page look" options={looks} value={look} onchange={setlook}/></Row>
            <Row label="Text size"><Segmented block label="Text size" options={sizes} value={size} onchange={setsize}/></Row>
            <Row label="Animations"><Segmented block label="Animations" options={motions} value={motion} onchange={setmotion}/></Row>
          </div>
          {user&&(
            <div className="border-b border-rule py-1">
              <Row label="Market"><Segmented block label="Market" options={marketopts} value={market} onchange={onmarket}/></Row>
            </div>
          )}
          {user&&(
            <div className="py-1">
              <button type="button" className={item} onClick={act(onhome)}>Back to the overview</button>
              <button type="button" className={item} onClick={act(onrefresh)}>Refresh data</button>
              {user.role==="admin"&&<button type="button" className={item} onClick={act(onadmin)}>Admin console</button>}
              <button type="button" className={item} onClick={act(onsignout)}>Sign out</button>
            </div>
          )}
          {!user&&<p className="px-4 pb-2 pt-1 text-xs text-mute">Preferences are saved on this device.</p>}
        </div>
      )}
    </div>
  )
}
