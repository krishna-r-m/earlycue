export default function Segmented({options,value,onchange,label}){
  return(
    <div role="group" aria-label={label} className="inline-flex border border-ink text-sm">
      {options.map((o,i)=>(
        <button
          key={String(o.value)}
          type="button"
          aria-pressed={o.value===value}
          onClick={()=>onchange(o.value)}
          className={"px-3 py-1 font-medium "+(i>0?"border-l border-ink ":"")+(o.value===value?"bg-ink text-paper":"bg-transparent text-ink hover:bg-mark hover:text-on-mark")}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
