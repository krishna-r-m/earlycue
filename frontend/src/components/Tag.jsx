import {toneof,pct} from "../lib.js"

export default function Tag({label,conf}){
  const t=toneof(label)
  return(
    <span className={"tag "+t.tag}>
      {label||"Unscored"}{conf!=null&&<span className="ml-1.5 opacity-80">{pct(conf)}</span>}
    </span>
  )
}
