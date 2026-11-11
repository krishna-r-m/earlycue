export default function BrandMark({className="h-9 w-9"}){
  return(
    <svg aria-hidden="true" viewBox="0 0 32 32" fill="none" className={"shrink-0 "+className}>
      <rect width="32" height="32" rx="2" fill="hsl(var(--ink))"/>
      <path d="M6.3 17H14.7A4.2 4.2 0 1 0 13.5 20" stroke="hsl(var(--paper))" strokeWidth="3" strokeLinejoin="round"/>
      <path d="M25 14.3A4.2 4.2 0 1 0 25 19.7" stroke="hsl(var(--paper))" strokeWidth="3"/>
      <circle cx="26.4" cy="7" r="2.6" fill="hsl(var(--mark))"/>
    </svg>
  )
}
