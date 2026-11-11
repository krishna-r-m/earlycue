import {useEffect,useRef,useState} from "react"
import {api} from "../api.js"
import Brand from "./Brand.jsx"
import Segmented from "./Segmented.jsx"
import ThemeToggle from "./ThemeToggle.jsx"

const modes=[
  {value:"login",label:"Sign in"},
  {value:"register",label:"Create account"}
]

export default function Login({onuser,theme,onsettheme}){
  const [mode,setmode]=useState("login")
  const [name,setname]=useState("")
  const [email,setemail]=useState("")
  const [password,setpassword]=useState("")
  const [busy,setbusy]=useState(false)
  const [err,seterr]=useState("")
  const [clientid,setclientid]=useState(undefined)
  const btn=useRef(null)

  useEffect(()=>{
    api.authconfig().then(c=>setclientid(c.google_client_id||null)).catch(()=>setclientid(null))
  },[])

  useEffect(()=>{
    if(!clientid)return
    function draw(){
      window.google.accounts.id.initialize({client_id:clientid,callback:res=>google(res.credential)})
      if(btn.current)window.google.accounts.id.renderButton(btn.current,{theme:theme==="dark"?"filled_black":"outline",size:"large",width:340,text:"continue_with",shape:"rectangular"})
    }
    if(window.google&&window.google.accounts){
      draw()
      return
    }
    const s=document.createElement("script")
    s.src="https://accounts.google.com/gsi/client"
    s.async=true
    s.onload=draw
    document.body.appendChild(s)
  },[clientid,theme])

  async function google(credential){
    seterr("")
    try{
      onuser(await api.google(credential))
    }catch(ex){
      seterr(ex.message)
    }
  }

  async function submit(e){
    e.preventDefault()
    setbusy(true)
    seterr("")
    try{
      const u=mode==="login"?await api.login(email,password):await api.register(email,password,name)
      onuser(u)
    }catch(ex){
      seterr(ex.message)
      setbusy(false)
    }
  }

  const field="mt-1 w-full border border-ink bg-surface px-3 py-2 text-sm"

  return(
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
      <div className="flex items-center justify-between gap-4">
        <Brand size="h-10 w-10" text="text-3xl"/>
        <ThemeToggle theme={theme} onchange={onsettheme}/>
      </div>
      <p className="mt-3 text-mute">Market news, sentiment and live prices for India and the US.</p>
      <div className="panel mt-6 p-6">
        {clientid!==null&&(
          <div>
            <div ref={btn} className="flex min-h-[44px] justify-center"/>
            <p className="my-4 flex items-center gap-3 text-xs text-mute">
              <span className="h-px flex-1 bg-rule"/>or use email<span className="h-px flex-1 bg-rule"/>
            </p>
          </div>
        )}
        {clientid===null&&(
          <div className="mb-5">
            <button type="button" disabled className="w-full border border-rule px-3 py-2.5 text-sm font-semibold text-mute">
              Continue with Google
            </button>
            <p className="mt-2 text-xs text-mute">Google sign-in is not available right now. You can still sign in with your email.</p>
          </div>
        )}
        <Segmented label="Account" options={modes} value={mode} onchange={v=>{setmode(v);seterr("")}}/>
        <form onSubmit={submit} className="mt-5 space-y-4">
          {mode==="register"&&(
            <label className="block text-sm font-medium">
              Name
              <input className={field} value={name} onChange={e=>setname(e.target.value)} autoComplete="name"/>
            </label>
          )}
          <label className="block text-sm font-medium">
            Email
            <input className={field} type="email" required value={email} onChange={e=>setemail(e.target.value)} autoComplete="email"/>
          </label>
          <label className="block text-sm font-medium">
            Password
            <input
              className={field}
              type="password"
              required
              minLength={mode==="register"?8:undefined}
              value={password}
              onChange={e=>setpassword(e.target.value)}
              autoComplete={mode==="login"?"current-password":"new-password"}
            />
            {mode==="register"&&<span className="mt-1 block text-xs font-normal text-mute">At least 8 characters.</span>}
          </label>
          {err&&<p role="alert" className="text-sm font-medium text-bear">{err}</p>}
          <button type="submit" disabled={busy} className="w-full bg-ink px-3 py-2.5 text-sm font-semibold text-paper hover:bg-mark hover:text-on-mark disabled:opacity-60">
            {busy?"Please wait...":mode==="login"?"Sign in":"Create account"}
          </button>
        </form>
      </div>
    </div>
  )
}
