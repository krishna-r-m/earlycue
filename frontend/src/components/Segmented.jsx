export default function Segmented({options,value,onchange,label,block}){
  return(
    <div role="group" aria-label={label} className={(block?"flex w-full":"inline-flex")+" border border-ink text-sm"}>
      {options.map((o,i)=>(
        <button
          key={String(o.value)}
          type="button"
          aria-pressed={o.value===value}
          onClick={()=>onchange(o.value)}
          className={(block?"flex-1 ":"")+"px-3 py-1 font-medium "+(i>0?"border-l border-ink ":"")+(o.value===value?"bg-ink text-paper":"bg-transparent text-ink hover:bg-mark hover:text-on-mark")}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
