import {useEffect,useState} from "react"

export default function CountUp({value,duration=900}){
  const [n,setn]=useState(0)

  useEffect(()=>{
    if(!value)return
    if(document.documentElement.dataset.motion==="off"){
      setn(value)
      return
    }
    let frame
    const start=performance.now()
    const step=now=>{
      const t=Math.min(1,(now-start)/duration)
      setn(Math.round(value*(1-Math.pow(1-t,3))))
      if(t<1)frame=requestAnimationFrame(step)
    }
    frame=requestAnimationFrame(step)
    return()=>cancelAnimationFrame(frame)
  },[value,duration])

  return <>{n.toLocaleString()}</>
}
