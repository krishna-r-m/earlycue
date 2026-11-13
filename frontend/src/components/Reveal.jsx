import {useEffect,useRef,useState} from "react"

export default function Reveal({children,className="",as:Tag="div",delay=0,...rest}){
  const ref=useRef(null)
  const [shown,setshown]=useState(()=>document.documentElement.dataset.motion==="off"||!("IntersectionObserver" in window))

  useEffect(()=>{
    if(shown)return
    const el=ref.current
    const io=new IntersectionObserver(([e])=>{
      if(e.isIntersecting){
        setshown(true)
        io.disconnect()
      }
    },{rootMargin:"0px 0px -6% 0px",threshold:0.04})
    io.observe(el)
    return()=>io.disconnect()
  },[shown])

  return(
    <Tag ref={ref} {...rest} style={delay?{transitionDelay:`${delay}ms`}:undefined} className={"reveal "+(shown?"is-in ":"")+className}>
      {children}
    </Tag>
  )
}
