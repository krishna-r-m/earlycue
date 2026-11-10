export default function BrandMark({className="h-9 w-9"}){
  return(
    <svg aria-hidden="true" viewBox="0 0 32 32" fill="none" className={"shrink-0 "+className}>
      <rect width="32" height="32" rx="2" fill="hsl(var(--ink))"/>
      <path d="M9 6v20" stroke="hsl(var(--paper))" strokeWidth="3.6"/>
      <path d="M17 6v20M17 15.5h3.2a5.25 5.25 0 0 1 0 10.5H17" stroke="hsl(var(--paper))" strokeWidth="3.6" strokeLinejoin="round"/>
      <circle cx="26.4" cy="7" r="2.6" fill="hsl(var(--mark))"/>
    </svg>
  )
}
