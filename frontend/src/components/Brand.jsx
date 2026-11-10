import BrandMark from "./BrandMark.jsx"

export default function Brand({onclick,size="h-9 w-9",text="text-2xl"}){
  const inner=(
    <>
      <BrandMark className={size}/>
      <span className={"font-serif font-bold leading-none tracking-tight "+text}>livebarter</span>
    </>
  )
  if(!onclick)return <span className="inline-flex items-center gap-2.5">{inner}</span>
  return(
    <a
      href="/"
      aria-label="livebarter home"
      title="Back to the homepage"
      onClick={e=>{
        if(e.metaKey||e.ctrlKey||e.shiftKey||e.button===1)return
        e.preventDefault()
        onclick()
      }}
      className="inline-flex items-center gap-2.5 text-ink no-underline hover:opacity-80"
    >
      {inner}
    </a>
  )
}
