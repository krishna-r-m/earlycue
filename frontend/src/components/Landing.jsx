import {useEffect,useState} from "react"
import {api} from "../api.js"
import Brand from "./Brand.jsx"
import ProfileMenu from "./ProfileMenu.jsx"
import TiltBar from "./TiltBar.jsx"
import Tag from "./Tag.jsx"
import Accordion from "./Accordion.jsx"
import Reveal from "./Reveal.jsx"
import CountUp from "./CountUp.jsx"
import Segmented from "./Segmented.jsx"
import {timeago} from "../lib.js"

const today=new Intl.DateTimeFormat("en-GB",{weekday:"long",day:"numeric",month:"long",year:"numeric"}).format(new Date())

const publishers=["Reuters","Bloomberg","Financial Times","Wall Street Journal","CNBC","MarketWatch","Barron's","Economic Times","Moneycontrol","LiveMint","Business Standard","Financial Express","BusinessLine","The Hindu","Hindustan Times","Times of India","Indian Express","NDTV Profit","CNBC-TV18","Nasdaq","Seeking Alpha","Yahoo Finance","Motley Fool","Forbes","Fortune","Associated Press","BBC","The Guardian","The New York Times","Morningstar","Investopedia"]

const edition=[
  ["What earlycue is","about"],
  ["How it works","how"],
  ["What you can do","features"],
  ["Where the news comes from","sources"],
  ["Reading the numbers","numbers"],
  ["Good to know","notes"],
  ["Questions","faq"]
]

const steps=[
  ["We read","Every 5 minutes earlycue checks the feeds of major business publishers. Every 15 minutes it also runs a wider sweep, searching trusted publishers, sectors and individual companies for new stories. Duplicates and untrusted sources are dropped."],
  ["We score","Each story is read by a language model trained on financial text (FinBERT). It labels the story bullish, bearish or neutral and gives a confidence between 0 and 100 percent."],
  ["We connect","Company names in the story are matched to listed stocks in the same market, and the story is filed under a sector such as banking, technology or energy."],
  ["We show","You get the mood of the market, the mood of each sector, a trend line, the stocks that moved most, and every story with its tag, next to prices that refresh every minute while the market is open."]
]

const features=[
  ["Two markets, one switch","Flip between India and the US. Everything on the page changes with it: sentiment, sectors, trend, news, search and the stock list. Indian stocks only appear on the India side and US stocks on the US side."],
  ["Every listed stock","Search any company listed on the NSE, or on the NYSE, Nasdaq and other major US exchanges. If nobody has written about a stock today you still get its page and its price, and an honest note that there is no news yet."],
  ["Market mood at a glance","One headline reading for the whole market: bullish, bearish or neutral, with the count of stories behind it and a score from -1 to +1."],
  ["Sector focus","Click a sector and the trend chart, the top stories, the stock list on the right and the news feed all narrow to that sector. Stocks with no news are still listed, roughly largest first."],
  ["Live prices","Prices for the most followed stocks refresh every minute while a market is open. Index levels sit at the top of the sidebar. Any other stock gets a fresh price the moment you open it."],
  ["News you can scan","Every story carries a tag, Bullish, Bearish or Neutral, with its confidence, the stocks it mentions, the source and how long ago it ran, with a link to read the full piece."],
  ["Most changed","A sidebar ranks stocks by price change since the previous close, or by how much their news sentiment has shifted compared with the previous period."],
  ["Made to read","Choose a newspaper layout or the original look, light or dark colours, three text sizes and calm animations you can switch off, all from the profile menu."]
]

const faqs=[
  ["Which stocks are covered?","All companies on the official NSE equity list and on the Nasdaq Trader lists of NYSE, Nasdaq and other US-listed companies. ETFs, test issues, warrants and preferred shares are left out. The lists refresh every week, and a stock missing from them can often still be found through search."],
  ["Why does a stock have no news?","Because none of the trusted publishers we read has written about it recently. Its price, sector and page are still there. The sentiment bar fills in as soon as stories appear."],
  ["How often does it update?","News every 5 minutes, with a wider sweep every 15. Prices every minute for the most followed stocks while the market is open. Smaller Indian stocks use the last official close."],
  ["How is the sentiment score worked out?","A bullish story counts as plus its confidence, a bearish story as minus its confidence and a neutral story as zero. The score for a stock, sector or market is the average. Above +0.12 it reads bullish, below -0.12 bearish, otherwise neutral."],
  ["Can I change how the site looks?","Yes. Open the profile menu in the top corner to switch between the newspaper layout and the original look, light and dark colours, text size, and animations."],
  ["Can I connect my broker account?","Not at the moment."],
  ["Is this investment advice?","No. See the notes above."]
]

const marketopts=[{value:"IN",label:"India"},{value:"US",label:"US"}]
const empty={total:0,bullish:0,bearish:0,neutral:0,score:0,leaning:"Neutral"}

function savedmarket(){
  try{
    return localStorage.getItem("mp_market")==="US"?"US":"IN"
  }catch{
    return "IN"
  }
}

function Section({id,title,letter,children}){
  return(
    <Reveal as="section" id={id} className="mt-16 scroll-mt-4">
      <h2 className="sec"><span className="num mr-3 opacity-60">{letter}</span>{title}</h2>
      <div className="mt-5">{children}</div>
    </Reveal>
  )
}

export default function Landing({onsignin,onsignup}){
  const [stats,setstats]=useState(null)
  const [front,setfront]=useState(null)
  const [market,setmarket]=useState(savedmarket)

  useEffect(()=>{
    api.health().then(setstats).catch(()=>{})
    api.frontPage().then(setfront).catch(()=>{})
  },[])

  const today24=front&&front.markets[market]
  const stories=today24?today24.stories:[]

  const button="px-5 py-2.5 text-sm font-semibold"
  const wire=publishers.map(p=>(<span key={p} className="flex items-center whitespace-nowrap font-serif text-sm italic">{p}<span aria-hidden="true" className="mx-5 not-italic opacity-50">/</span></span>))

  return(
    <div className="mx-auto max-w-5xl px-4 pb-20 sm:px-6">
      <header className="pt-4">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 border-b border-rule pb-2">
          <p className="dateline text-sm text-mute">{today}</p>
          <div className="flex items-center gap-3">
            <button type="button" onClick={onsignin} className="hidden border border-ink px-3 py-1 text-sm font-medium hover:bg-mark hover:text-on-mark sm:block">Sign in</button>
            <ProfileMenu onsignin={onsignin} onsignup={onsignup}/>
          </div>
        </div>
        <div className="flex justify-center py-6">
          <Brand onclick={()=>window.scrollTo({top:0})} size="h-14 w-14" text="text-5xl sm:text-7xl"/>
        </div>
        <div className="masthead-rule"/>
        <p className="dateline border-b border-rule py-2 text-center text-sm text-mute">News, sentiment and prices for every listed stock in India and the US</p>
        <div className="wire mt-3" aria-label="Publishers we read">
          <div className="wire-track py-1.5" aria-hidden="true">
            <div className="flex">{wire}</div>
            <div className="flex">{wire}</div>
          </div>
        </div>
      </header>

      <main>
        <section className="mt-12 grid items-start gap-10 lg:grid-cols-5">
          <div className="rise lg:col-span-3">
            <p className="dateline text-sm text-mute">Front page</p>
            <h1 className="mt-2 font-serif text-4xl font-bold leading-[1.1] tracking-tight sm:text-5xl lg:text-[3.4rem]">
              Every listed stock in India and the US, with the news behind the move.
            </h1>
            <p className="dropcap justify-paper mt-6 max-w-prose font-serif text-lg leading-relaxed">
              earlycue reads market news from trusted publishers around the clock, scores every story as bullish, bearish or neutral, ties it to the companies and sectors it is about, and sets it beside live prices. Look up any listed stock, even one nobody is writing about today.
            </p>
            <blockquote className="mt-6 border-l-4 border-ink pl-4 font-serif text-xl italic leading-snug">
              See how the news is leaning, and what the price is doing, before you read a single story.
            </blockquote>
            <div className="mt-8 flex flex-wrap gap-3">
              <button type="button" onClick={onsignup} className={button+" bg-ink text-paper hover:bg-mark hover:text-on-mark"}>Create an account</button>
              <button type="button" onClick={onsignin} className={button+" border border-ink hover:bg-mark hover:text-on-mark"}>Sign in</button>
            </div>
          </div>
          <aside className="rise border-t-2 border-ink pt-3 lg:col-span-2" style={{animationDelay:"120ms"}} aria-label="Today's market">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="dateline text-sm text-mute">{front?`Live data, updated ${timeago(front.generated_at)}`:"Loading today's data"}</p>
              <Segmented label="Market" options={marketopts} value={market} onchange={setmarket}/>
            </div>
            <div className="mt-3">
              <TiltBar title={`${market==="IN"?"Indian":"US"} market sentiment, last 24 hours`} stats={today24?today24.overall:empty}/>
            </div>
            <h3 className="mt-5 font-serif text-lg font-bold">Top stories right now</h3>
            {stories.length>0?(
              <ul className="mt-2 divide-y divide-rule border-y border-rule">
                {stories.map(a=>(
                  <li key={a.id} className="py-3">
                    <Tag label={a.sentiment} conf={a.confidence}/>
                    <a href={a.url} target="_blank" rel="noopener noreferrer" className="mt-1.5 block font-serif text-base font-semibold leading-snug hover:underline">{a.title}</a>
                    <p className="mt-1 text-xs text-mute">{a.source}, {timeago(a.published_at)}{a.tickers.length>0?`, ${a.tickers.join(" ")}`:""}</p>
                  </li>
                ))}
              </ul>
            ):(
              <p className="mt-2 text-sm text-mute">Top stories appear here once the first news run has finished.</p>
            )}
            <p className="mt-2 text-xs text-mute">Top stories are picked by the model's confidence, mentions of listed stocks and freshness, one per publisher where possible.</p>
          </aside>
        </section>

        <Reveal as="section" className="mt-12 grid grid-cols-2 border-y-2 border-ink md:grid-cols-4" aria-label="Today in numbers">
          {[
            ["Listed stocks",stats&&stats.stocks>0?<CountUp value={stats.stocks}/>:"Loading"],
            ["Stories indexed",stats&&stats.articles>0?<CountUp value={stats.articles}/>:"Loading"],
            ["News checked","Every 5 min"],
            ["Prices","Every minute"]
          ].map(([k,v],i)=>(
            <div key={k} className={"px-4 py-5 text-center "+(i>0?"md:border-l md:border-rule ":"")+(i===2?"border-t border-rule md:border-t-0 ":"")+(i===3?"border-l border-t border-rule md:border-t-0":"")}>
              <p className="num text-2xl font-semibold sm:text-3xl">{v}</p>
              <p className="mt-1 text-sm text-mute">{k}</p>
            </div>
          ))}
        </Reveal>

        <Reveal as="nav" className="mt-12" aria-label="Inside this edition">
          <h2 className="font-serif text-xl font-bold">Inside this edition</h2>
          <ul className="mt-3 grid gap-x-10 md:grid-cols-2">
            {edition.map(([title,id],i)=>(
              <li key={id}>
                <a href={"#"+id} className="flex items-baseline gap-2 py-1.5 hover:bg-mark hover:text-on-mark">
                  <span className="num w-5 text-sm opacity-60">{String.fromCharCode(65+i)}</span>
                  <span className="font-serif text-base">{title}</span>
                  <span aria-hidden="true" className="flex-1 border-b border-dotted border-rule"/>
                </a>
              </li>
            ))}
          </ul>
        </Reveal>

        <Section id="about" letter="A" title="What earlycue is">
          <div className="justify-paper font-serif text-[1.05rem] leading-relaxed md:columns-2 md:gap-10 md:[column-rule:1px_solid_hsl(var(--rule))]">
            <p>Most market sites give you prices or headlines, rarely both in one place, and rarely for the whole market. earlycue puts them side by side. For any stock, sector or market you can see how the news is leaning, how the price is moving, and which stories are behind it.</p>
            <p className="mt-4">It is a reader and a tracker. It is not a broker, it does not place trades, and it does not tell you what to buy or sell. It gives you a quicker way to see what is being said about the companies you follow, and to spot a change in tone early.</p>
          </div>
        </Section>

        <Section id="how" letter="B" title="How it works">
          <ol className="grid border-t border-rule md:grid-cols-4">
            {steps.map(([title,text],i)=>(
              <li key={title} className={"py-5 md:px-5 "+(i>0?"border-t border-rule md:border-l md:border-t-0 ":"")+(i===0?"md:pl-0":"")}>
                <p className="font-serif text-5xl font-bold leading-none opacity-30">{i+1}</p>
                <h3 className="mt-2 font-serif text-xl font-bold">{title}</h3>
                <p className="justify-paper mt-2 text-sm leading-relaxed">{text}</p>
              </li>
            ))}
          </ol>
        </Section>

        <Section id="features" letter="C" title="What you can do">
          <div className="grid border-l border-t border-rule md:grid-cols-2">
            {features.map(([title,text],i)=>(
              <Reveal key={title} delay={(i%2)*80} className="border-b border-r border-rule bg-surface p-5">
                <h3 className="font-serif text-lg font-bold">{title}</h3>
                <p className="mt-1.5 leading-relaxed">{text}</p>
              </Reveal>
            ))}
          </div>
        </Section>

        <Section id="sources" letter="D" title="Where the news comes from">
          <p className="justify-paper max-w-prose font-serif text-[1.05rem] leading-relaxed">
            earlycue only keeps stories from a fixed list of established publishers. Stories found through news search or aggregators are thrown away unless the publisher is on that list. The current list includes {publishers.join(", ")} and more.
          </p>
        </Section>

        <Section id="numbers" letter="E" title="Reading the numbers">
          <dl className="grid gap-x-8 gap-y-5 md:grid-cols-2">
            {[
              ["Tilt","The overall mood of the market over the window you pick (24 hours, 3 days or 7 days), with the count of bullish, neutral and bearish stories."],
              ["Score","From -1 to +1. Bullish stories add their confidence, bearish stories subtract it, neutral stories add nothing, and the score is the average."],
              ["Sentiment shift","How much a stock's score now differs from its score over the previous period of the same length."],
              ["Price change","The move since the previous close. Prices can run up to 15 minutes behind the exchange."]
            ].map(([k,v])=>(
              <div key={k} className="border-t border-rule pt-2">
                <dt className="font-serif text-base font-bold">{k}</dt>
                <dd className="mt-1 leading-relaxed">{v}</dd>
              </div>
            ))}
          </dl>
        </Section>

        <Section id="notes" letter="F" title="Good to know">
          <ul className="max-w-prose list-disc space-y-2 pl-5 leading-relaxed">
            <li>earlycue is for information only. Nothing on it is investment advice, and past moves say nothing certain about future ones.</li>
            <li>Sentiment is scored automatically. The model can misread sarcasm, mixed stories or unusual wording, so treat the tag as a quick guide and read the story.</li>
            <li>A stock with no recent news shows no sentiment, only its price. Silence is not a signal either way.</li>
            <li>Prices for the most followed stocks refresh every minute. Others show the last close or a recent snapshot, and a fresh price is fetched when you open a stock.</li>
            <li>Sectors for smaller stocks come from official industry lists where they exist, and are otherwise estimated from the company name, so a few may be filed under General or in the wrong sector.</li>
          </ul>
        </Section>

        <Section id="faq" letter="G" title="Questions">
          <Accordion items={faqs}/>
        </Section>

        <Reveal as="section" className="mt-16 border-y-2 border-ink py-10 text-center">
          <h2 className="font-serif text-3xl font-bold sm:text-4xl">Start reading the market.</h2>
          <p className="mx-auto mt-2 max-w-md text-mute">Make an account to see sentiment, sectors, prices and news for India and the US.</p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <button type="button" onClick={onsignup} className={button+" bg-ink text-paper hover:bg-mark hover:text-on-mark"}>Create an account</button>
            <button type="button" onClick={onsignin} className={button+" border border-ink hover:bg-mark hover:text-on-mark"}>Sign in</button>
          </div>
        </Reveal>
      </main>

      <footer className="mt-8 flex flex-wrap items-baseline justify-between gap-2 text-xs text-mute">
        <span className="dateline">earlycue. News and prices for information only, not investment advice.</span>
        <span>Prices can be delayed up to 15 minutes.</span>
      </footer>
    </div>
  )
}
