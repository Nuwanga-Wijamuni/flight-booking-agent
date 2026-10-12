import { useEffect, useState, type FormEvent } from 'react'

type Leg = {origin:string;destination:string;departure:string;arrival:string;airline:string;flight_number:string}
type Offer = {id:string;airline:string;amount:string;currency:string;stops:number;duration:string;legs:Leg[];baggage:string;conditions:string;expires_at:string;mode:string}
type Quote = {id:string;offer:Offer;expires_at:string}
type Booking = {id:string;status:string;message:string}

async function api<T>(path:string, body?:unknown):Promise<T> {
  const response = await fetch(`/api/${path}`, body === undefined ? undefined : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)})
  const data = await response.json()
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Please check the route, date, and budget.')
  return data
}
const money = (o:Offer) => new Intl.NumberFormat('en-US',{style:'currency',currency:o.currency}).format(Number(o.amount))
const initialDate = new Date(Date.now()+30*86400000).toISOString().slice(0,10)
const time = (value:string) => value.slice(11,16)

export default function App() {
  const [health,setHealth] = useState<{provider:string;ai:string;ai_model:string|null}>({provider:'demo',ai:'demo',ai_model:null})
  const [message,setMessage] = useState(`Find flights from Colombo to Singapore on ${initialDate} under $400`)
  const [reply,setReply] = useState('Tell me where you want to go. I’ll help you compare the options.')
  const [origin,setOrigin] = useState('CMB')
  const [destination,setDestination] = useState('SIN')
  const [date,setDate] = useState(initialDate)
  const [budget,setBudget] = useState('400')
  const [offers,setOffers] = useState<Offer[]>([])
  const [quote,setQuote] = useState<Quote|null>(null)
  const [booking,setBooking] = useState<Booking|null>(null)
  const [confirmed,setConfirmed] = useState(false)
  const [key,setKey] = useState('')
  const [busy,setBusy] = useState(false)
  const [error,setError] = useState('')
  const [searched,setSearched] = useState(false)
  useEffect(()=>{api<typeof health>('health').then(setHealth).catch(()=>setError('Start the backend on port 8000 to connect.'))},[])

  async function run(action:()=>Promise<void>) {
    setError('');setBusy(true)
    try {await action()} catch(e) {setError(e instanceof Error ? e.message : 'Request failed. Please try again.')} finally {setBusy(false)}
  }
  function resetResults() {setQuote(null);setBooking(null);setConfirmed(false);setOffers([]);setSearched(false)}
  function chat(e:FormEvent) {e.preventDefault();void run(async()=>{
    resetResults()
    const data = await api<{reply:string;offers:Offer[];trip:{origin:string;destination:string;departure_date:string;budget_usd:string|null}|null}>('chat',{message})
    setReply(data.reply);setOffers(data.offers);setSearched(!!data.trip)
    if(data.trip){setOrigin(data.trip.origin);setDestination(data.trip.destination);setDate(data.trip.departure_date);setBudget(data.trip.budget_usd ?? '')}
  })}
  function search(e:FormEvent) {e.preventDefault();void run(async()=>{
    resetResults()
    const data = await api<{offers:Offer[]}>('search',{origin,destination,departure_date:date,budget_usd:budget || null})
    setOffers(data.offers);setSearched(true);setReply(`Found ${data.offers.length} options for ${origin} → ${destination}. Review a flight to continue. Non-USD offers are not filtered by the USD budget.`)
  })}
  function select(offer:Offer) {void run(async()=>{setBooking(null);setQuote(null);const q = await api<Quote>('quotes',{offer_id:offer.id});setQuote(q);setConfirmed(false);setKey(crypto.randomUUID())})}
  function book() {if(quote) void run(async()=>{const result = await api<Booking>('bookings',{quote_id:quote.id,confirmed,idempotency_key:key});setBooking(result);setQuote(null)})}

  return <div className="app">
    <nav><a className="brand" href="/">✈ <span>skyward<span className="dot">.</span></span></a><span className="nav-label">YOUR AI TRAVEL COMPANION</span><span className="pill">{health.provider === 'demo' ? 'Demo flights' : 'Duffel sandbox'}</span></nav>
    <main>
      <header><div className="eyebrow">LESS SEARCHING. MORE EXPLORING.</div><h1>Your next journey,<br/><span>one conversation away.</span></h1><p>Find your flight, compare the details, and explore a simpler way to book.</p></header>
      <section className="workspace">
        <aside className="assistant"><div className="assistant-title"><div className="orb">✦</div><div><h2>Travel assistant</h2><span>{health.ai === 'groq' ? `${health.ai_model?.replace('openai/', '').toUpperCase()} · Groq + LangGraph` : 'Demo assistant · LangGraph'}</span></div></div><div className="bubble">{reply}</div><form onSubmit={chat}><label htmlFor="message">Where would you like to go?</label><textarea id="message" value={message} onChange={e=>setMessage(e.target.value)} maxLength={2000} required rows={4}/><button disabled={busy} className="primary" type="submit">{busy ? 'Working…' : 'Find my flight'} <span>↗</span></button></form><p className="hint">Try: “From Colombo to Dubai on {initialDate} under $500.”</p><div className="notice"><strong>A safe place to try things</strong><p>All bookings are simulated. No payment is collected and no ticket is issued.</p></div></aside>
        <section className="results"><form className="searchbar" onSubmit={search}><label>From<input value={origin} onChange={e=>setOrigin(e.target.value.toUpperCase())} required pattern="[A-Z]{3}" maxLength={3}/></label><label>To<input value={destination} onChange={e=>setDestination(e.target.value.toUpperCase())} required pattern="[A-Z]{3}" maxLength={3}/></label><label>Departure<input type="date" value={date} min={new Date().toISOString().slice(0,10)} onChange={e=>setDate(e.target.value)} required/></label><label>Budget · USD<input type="number" min="1" step="0.01" placeholder="Any" value={budget} onChange={e=>setBudget(e.target.value)}/></label><button type="submit" disabled={busy}>Search ↗</button></form><div className="results-heading"><h2>{searched ? `${offers.length} flight options` : 'Make room for your next adventure'}</h2><span>One way · 1 adult</span></div>
        {error && <div role="alert" className="error">{error}</div>}
        {booking && <div className="success" role="status"><strong>✓ Simulation complete</strong><p>{booking.message}</p><code>{booking.id}</code></div>}
        {!offers.length && <div className="empty"><div className="globe">◎</div><h3>{searched ? 'No flights matched your search' : 'A world of possibilities'}</h3><p>{searched ? 'Try a higher budget, another date, or a different route.' : 'Tell the assistant your plans or use the search fields above.'}</p><div className="destinations"><button disabled={busy} onClick={()=>setDestination('SIN')}>Singapore · SIN</button><button disabled={busy} onClick={()=>setDestination('DXB')}>Dubai · DXB</button><button disabled={busy} onClick={()=>setDestination('LHR')}>London · LHR</button></div></div>}
        {offers.map((o,i)=><article className="flight" key={o.id}><div className="flight-top"><strong>✈ {o.airline}</strong><span className={i===0?'tag':'subtle'}>{i===0?'First option':o.mode === 'demo'?'Demo fare':'Sandbox fare'}</span></div><div className="flight-middle"><div><strong>{time(o.legs[0].departure)}</strong><span>{o.legs[0].origin}</span></div><div className="route-line"><span>{o.duration.replace('PT','').toLowerCase()}</span><div>──── ✈ ────</div><span>{o.stops ? `${o.stops} stop` : 'Nonstop'}</span></div><div><strong>{time(o.legs.at(-1)!.arrival)}</strong><span>{o.legs.at(-1)!.destination}</span></div><div className="price"><strong>{money(o)}</strong><span>Total · 1 adult</span></div></div><div className="flight-bottom"><span>{o.baggage}</span><button disabled={busy} onClick={()=>select(o)}>Review flight →</button></div></article>)}
        </section>
      </section>
      <footer>Built for thoughtful travel. <span>Demo and sandbox only · Prices shown are not real travel quotes.</span></footer>
    </main>
    {quote && <div className="overlay"><section className="modal" role="dialog" aria-modal="true" aria-labelledby="quote-title"><button aria-label="Close flight review" className="close" disabled={busy} onClick={()=>setQuote(null)}>×</button><div className="eyebrow">REVIEW YOUR JOURNEY</div><h2 id="quote-title">{quote.offer.legs[0].origin} → {quote.offer.legs.at(-1)!.destination}</h2><p>{quote.offer.airline} · {quote.offer.mode === 'demo'?'Demo itinerary':'Sandbox itinerary'}</p>{quote.offer.legs.map((leg,i)=><div className="leg" key={i}><strong>{leg.origin} → {leg.destination}</strong><span>{leg.departure.replace('T',' ').slice(0,16)} → {leg.arrival.replace('T',' ').slice(0,16)}</span><small>{leg.airline} · {leg.flight_number}</small></div>)}<p className="hint">Times follow the provider response. Demo times use UTC.</p><div className="total"><span>Reviewed total</span><strong>{money(quote.offer)}</strong></div><p>{quote.offer.baggage}</p><p className="hint">{quote.offer.conditions}</p><p className="hint">Quote expires: {new Date(quote.expires_at).toLocaleTimeString()}</p><label className="confirmation"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>I confirm this itinerary and total for a simulated booking.</label>{error && <p role="alert" className="error">{error}</p>}<button className="primary" disabled={busy || !confirmed} onClick={book}>{busy?'Processing…':'Simulate booking'} <span>→</span></button><p className="hint">No passenger details or card information required.</p></section></div>}
  </div>
}
