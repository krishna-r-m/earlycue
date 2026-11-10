import {useEffect,useLayoutEffect,useState} from "react"
import {api} from "./api.js"
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

  useEffect(()=>{
    api.me().then(setuser).catch(()=>setuser(null))
  },[])

  useLayoutEffect(()=>{
    document.documentElement.dataset.theme=theme
    document.documentElement.style.colorScheme=theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content",theme==="dark"?"#0f1112":"#eeefec")
    try{
      localStorage.setItem("mp_theme",theme)
    }catch{}
  },[theme])

  async function signout(){
    try{
      await api.logout()
    }catch{}
    setuser(null)
  }

  if(user===undefined)return <p className="p-8 text-sm text-mute">Loading...</p>
  if(user===null)return <Login onuser={setuser} theme={theme} onsettheme={settheme}/>
  return <Dashboard user={user} onsignout={signout} onexpired={()=>setuser(null)} theme={theme} onsettheme={settheme}/>
}
