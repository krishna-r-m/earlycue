import {useEffect,useLayoutEffect,useState} from "react"
import {api} from "./api.js"
import Landing from "./components/Landing.jsx"
import Login from "./components/Login.jsx"
import Dashboard from "./components/Dashboard.jsx"

function savedtheme(){
  try{
    const saved=localStorage.getItem("mp_theme")
    if(saved==="light"||saved==="dark")return saved
  }catch{}
  return window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"
}

export default function App(){
  const [user,setuser]=useState(undefined)
  const [theme,settheme]=useState(savedtheme)
  const [route,setroute]=useState(window.location.hash)

  useEffect(()=>{
    api.me().then(setuser).catch(()=>setuser(null))
  },[])

  useEffect(()=>{
    const onhash=()=>setroute(window.location.hash)
    window.addEventListener("hashchange",onhash)
    return()=>window.removeEventListener("hashchange",onhash)
  },[])

  useLayoutEffect(()=>{
    document.documentElement.dataset.theme=theme
    document.documentElement.style.colorScheme=theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content",theme==="dark"?"#1c1c1c":"#edebe7")
    try{
      localStorage.setItem("mp_theme",theme)
    }catch{}
  },[theme])

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

  if(user===undefined)return <p className="p-8 text-sm text-mute">Loading...</p>
  if(user===null){
    if(route==="#signin"||route==="#signup"){
      return <Login onuser={signedin} theme={theme} onsettheme={settheme} initialmode={route==="#signup"?"register":"login"} onhome={()=>go("")}/>
    }
    return <Landing theme={theme} onsettheme={settheme} onsignin={()=>go("#signin")} onsignup={()=>go("#signup")}/>
  }
  return <Dashboard user={user} onsignout={signout} onexpired={()=>setuser(null)} theme={theme} onsettheme={settheme}/>
}
