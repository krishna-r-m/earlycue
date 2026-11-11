const base=import.meta.env.VITE_API_URL||""

async function call(method,path,opts={}){
  const qs=new URLSearchParams()
  Object.entries(opts.params||{}).forEach(([k,v])=>{
    if(v!==undefined&&v!==null&&v!=="")qs.set(k,v)
  })
  const query=qs.toString()
  const res=await fetch(`${base}/api${path}${query?"?"+query:""}`,{
    method,
    credentials:"include",
    headers:opts.body?{"Content-Type":"application/json"}:undefined,
    body:opts.body?JSON.stringify(opts.body):undefined
  })
  if(!res.ok){
    let detail=`request failed (${res.status})`
    try{
      const j=await res.json()
      if(typeof j.detail==="string")detail=j.detail
      else if(Array.isArray(j.detail)&&j.detail[0]&&j.detail[0].msg)detail=j.detail[0].msg
    }catch{}
    const err=new Error(detail)
    err.status=res.status
    throw err
  }
  return res.json()
}

const get=(path,params)=>call("GET",path,{params})
const post=(path,body)=>call("POST",path,{body})

export const api={
  me:()=>get("/auth/me"),
  authconfig:()=>get("/auth/config"),
  login:(email,password)=>post("/auth/login",{email,password}),
  register:(email,password,name)=>post("/auth/register",{email,password,name}),
  google:credential=>post("/auth/google",{credential}),
  logout:()=>post("/auth/logout"),
  pulse:(market,hours,sector)=>get("/market-pulse",{market,hours,sector}),
  articles:params=>get("/articles",params),
  movers:params=>get("/movers",params),
  ticker:(symbol,days)=>get(`/ticker/${encodeURIComponent(symbol)}`,{days}),
  search:(q,market)=>get("/tickers/search",{q,market}),
  status:()=>get("/status"),
  sources:()=>get("/sources"),
  adminOverview:()=>get("/admin/overview"),
  adminUsers:()=>get("/admin/users"),
  health:()=>get("/health"),
  refresh:()=>call("POST","/admin/refresh"),
  userRefresh:()=>call("POST","/refresh"),
  cleanup:()=>call("POST","/admin/cleanup")
}
