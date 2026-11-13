const base=import.meta.env.VITE_API_URL||""
const inflight=new Map()
const recent=new Map()

async function request(method,path,opts={}){
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

function get(path,params){
  const key=path+"?"+JSON.stringify(params||{})
  const hit=recent.get(key)
  if(hit&&Date.now()-hit.at<2000)return Promise.resolve(hit.data)
  if(inflight.has(key))return inflight.get(key)
  const p=request("GET",path,{params}).then(data=>{
    recent.set(key,{at:Date.now(),data})
    if(recent.size>60)recent.clear()
    return data
  }).finally(()=>inflight.delete(key))
  inflight.set(key,p)
  return p
}

function post(path,body){
  recent.clear()
  return request("POST",path,{body})
}

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
  history:(symbol,range)=>get(`/history/${encodeURIComponent(symbol)}`,{range}),
  sectorHistory:(sector,market,range)=>get(`/history/sector/${encodeURIComponent(sector)}`,{market,range}),
  frontPage:()=>get("/public/front-page"),
  refresh:()=>post("/admin/refresh"),
  userRefresh:()=>post("/refresh"),
  cleanup:()=>post("/admin/cleanup")
}
