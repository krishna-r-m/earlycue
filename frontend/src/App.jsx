import {Suspense,lazy,useEffect,useState} from "react"
import {api} from "./api.js"
import {PrefsProvider} from "./prefs.jsx"

const Landing=lazy(()=>import("./components/Landing.jsx"))
const Login=lazy(()=>import("./components/Login.jsx"))
const Dashboard=lazy(()=>import("./components/Dashboard.jsx"))

function Fallback(){
  return(
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-10" aria-busy="true">
      <div className="skeleton mx-auto h-10 w-56"/>
      <div className="skeleton h-3 w-full"/>
      <div className="skeleton h-40 w-full"/>
    </div>
  )
}

function Shell(){
  const [user,setuser]=useState(undefined)
  const [route,setroute]=useState(window.location.hash)

  useEffect(()=>{
    api.me().then(setuser).catch(()=>setuser(null))
  },[])

  useEffect(()=>{
    const onhash=()=>setroute(window.location.hash)
    window.addEventListener("hashchange",onhash)
    return()=>window.removeEventListener("hashchange",onhash)
  },[])

  useEffect(()=>{
    if(user===null&&(route==="#signin"||route==="#signup"))import("./components/Dashboard.jsx")
  },[user,route])

  function go(hash){
    if(hash){
      window.location.hash=hash
    }else{
      window.history.pushState(null,"",window.location.pathname+window.location.search)
      setroute("")
    }
    window.scrollTo({top:0})
  }

  function signedin(u){
    go("")
    setuser(u)
  }

  async function signout(){
    try{
      await api.logout()
    }catch{}
    go("")
    setuser(null)
  }

  if(user===undefined)return <Fallback/>
  let page
  if(user===null){
    if(route==="#signin"||route==="#signup"){
      page=<Login key="login" onuser={signedin} initialmode={route==="#signup"?"register":"login"} onhome={()=>go("")} onsignin={()=>go("#signin")} onsignup={()=>go("#signup")}/>
    }else{
      page=<Landing key="landing" onsignin={()=>go("#signin")} onsignup={()=>go("#signup")}/>
    }
  }else{
    page=<Dashboard key="dash" user={user} onsignout={signout} onexpired={()=>setuser(null)}/>
  }
  return <Suspense fallback={<Fallback/>}><div className="fade-in">{page}</div></Suspense>
}

export default function App(){
  return <PrefsProvider><Shell/></PrefsProvider>
}
