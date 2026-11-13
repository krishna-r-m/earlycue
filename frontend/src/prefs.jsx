import {createContext,useContext,useLayoutEffect,useMemo,useState} from "react"

const Ctx=createContext(null)

export const usePrefs=()=>useContext(Ctx)

function read(key,allowed,fallback){
  try{
    const v=localStorage.getItem(key)
    return allowed.includes(v)?v:fallback
  }catch{
    return fallback
  }
}

function lowend(){
  const reduce=window.matchMedia("(prefers-reduced-motion: reduce)").matches
  const cores=navigator.hardwareConcurrency||8
  const mem=navigator.deviceMemory||8
  return reduce||cores<=2||mem<=2
}

export function PrefsProvider({children}){
  const [theme,settheme]=useState(()=>read("mp_theme",["light","dark"],window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"))
  const [look,setlook]=useState(()=>read("mp_look2",["paper","classic"],"paper"))
  const [size,setsize]=useState(()=>read("mp_size",["small","medium","large"],"medium"))
  const [motion,setmotion]=useState(()=>read("mp_motion",["on","off"],lowend()?"off":"on"))

  useLayoutEffect(()=>{
    const root=document.documentElement
    root.dataset.theme=theme
    root.dataset.look=look
    root.dataset.size=size
    root.dataset.motion=motion
    root.style.colorScheme=theme
    const paper=getComputedStyle(root).getPropertyValue("--paper").trim()
    if(paper)document.querySelector('meta[name="theme-color"]')?.setAttribute("content",`hsl(${paper})`)
    try{
      localStorage.setItem("mp_theme",theme)
      localStorage.setItem("mp_look2",look)
      localStorage.setItem("mp_size",size)
      localStorage.setItem("mp_motion",motion)
    }catch{}
  },[theme,look,size,motion])

  const value=useMemo(()=>({theme,settheme,look,setlook,size,setsize,motion,setmotion}),[theme,look,size,motion])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
