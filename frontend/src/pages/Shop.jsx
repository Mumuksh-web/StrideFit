import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import Logo from '../components/Logo'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import { getReviewList, subscribeReviewList, toggleReviewItem } from '../lib/reviewList'

const API_BASE = 'http://127.0.0.1:8000'
const SESSION_STORAGE_KEY = 'stridefit-shop-session-id'
const GREETING = { role: 'agent', text: 'Hi! Main StrideFit catalog mein aapki perfect pair dhoondne mein help karunga.' }

function createSessionId() {
  return `shop-${crypto.randomUUID()}`
}
function getOrCreateSessionId() {
  try {
    const existing = localStorage.getItem(SESSION_STORAGE_KEY)
    if (existing) return existing
    const created = createSessionId()
    localStorage.setItem(SESSION_STORAGE_KEY, created)
    return created
  } catch {
    return createSessionId()
  }
}
// `let`, not `const`: "New Chat" reassigns this so every subsequent call (chat,
// checkout, etc.) picks up the new session — every function below reads this
// variable by name, so a reassignment is visible to all of them immediately.
let sessionId = getOrCreateSessionId()

function formatMoney(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 2 }).format(Number(value || 0))
}

function AppStatus({ children, variant = 'neutral' }) {
  return <Badge variant={variant}>{children}</Badge>
}

function RemoveIcon() {
  return <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" /></svg>
}

function NewChatIcon() {
  return <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" strokeLinecap="round" /></svg>
}

function SavedForReview() {
  const [items, setItems] = useState(() => getReviewList())
  const navigate = useNavigate()
  useEffect(() => subscribeReviewList(setItems), [])

  return <Card className="mt-5 p-5"><div className="flex items-center justify-between"><h3 className="font-heading text-lg font-bold">🔖 Saved for Review</h3><span className="text-xs text-text-muted">{items.length} saved</span></div>{items.length ? <div className="mt-4 space-y-2">{items.map((item) => <div className="flex cursor-pointer items-center justify-between gap-3 rounded-lg border border-border bg-background/40 px-3 py-2.5 transition hover:border-accent-start/70" key={item.id} onClick={() => navigate(`/product/${item.id}`)} role="button" tabIndex={0}><div className="min-w-0"><p className="truncate text-sm font-semibold">{item.name}</p><div className="mt-1 flex items-center gap-2"><Badge variant="neutral">{item.category}</Badge><span className="text-xs text-text-muted">{formatMoney(item.price)}</span></div></div><button className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-text-muted transition hover:text-text-primary" onClick={(event) => { event.stopPropagation(); toggleReviewItem(item) }} type="button" aria-label="Remove from review list" title="Remove from review list"><RemoveIcon /></button></div>)}</div> : <p className="mt-3 text-sm leading-6 text-text-muted">Products you mark for review will appear here.</p>}</Card>
}

function Message({ role, children }) {
  return <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}><div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${role === 'user' ? 'rounded-br-sm bg-accent-gradient text-white' : 'rounded-bl-sm border border-border bg-surface text-text-primary'}`}>{children}</div></div>
}

function ProductCard({ product, onSelect, selecting }) {
  return <Card className="flex h-full flex-col bg-surface/90 p-5"><div className="flex items-start justify-between gap-3"><AppStatus variant="neutral">{product.category}</AppStatus><span className="font-heading text-xl font-bold">{formatMoney(product.price)}</span></div><h3 className="mt-5 font-heading text-lg font-bold">{product.name}</h3><p className="mt-2 flex-1 text-sm leading-6 text-text-muted">{product.description}</p><p className="mt-5 text-xs text-text-muted">{product.checkout_hint}</p><Button className="mt-4 w-full" onClick={() => onSelect(product.id)} disabled={selecting}> {selecting ? 'Preparing checkout…' : 'Select'} </Button></Card>
}

export default function Shop() {
  const location = useLocation()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [name, setName] = useState('')
  const [needsName, setNeedsName] = useState(false)
  const [products, setProducts] = useState([])
  const [checkout, setCheckout] = useState(null)
  const [crossSell, setCrossSell] = useState([])
  const [crossSellLoading, setCrossSellLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [naming, setNaming] = useState(false)
  const [selecting, setSelecting] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const autoSentRef = useRef(false)

  // "New Chat": points the browser at a brand-new session_id and resets the UI
  // to a clean slate. The OLD session_id is only overwritten in localStorage —
  // its conversation row in the DB is never touched, so /buyer/chat-history
  // for it still returns the full old transcript.
  function startNewChat() {
    const freshSessionId = createSessionId()
    try {
      localStorage.setItem(SESSION_STORAGE_KEY, freshSessionId)
    } catch {
      // localStorage unavailable (private mode, etc.) — sessionId still updates
      // in memory below, so the new chat works for the rest of this page load.
    }
    sessionId = freshSessionId
    setMessages([GREETING])
    setNeedsName(false)
    setName('')
    setProducts([])
    setCrossSell([])
    setCrossSellLoading(false)
    setCheckout(null) // an open checkout belongs to the old session's buyer_id resolution — drop it rather than leave it orphaned
    setResult(null)
    setError('')
  }

  async function sendChatMessage(text) {
    setMessages((current) => [...current, { role: 'user', text }])
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE}/buyer/chat`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId, message: text, buyer_id: 'guest' }) })
      if (!response.ok) throw new Error('Chat service unavailable. Please try again.')
      const data = await response.json()
      setMessages((current) => [...current, { role: 'agent', text: data.message }])
      setProducts(data.recommendations || [])
      setNeedsName(Boolean(data.needs_name))
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetch(`${API_BASE}/buyer/chat-history/${sessionId}`)
      .then((response) => { if (!response.ok) throw new Error('History unavailable'); return response.json() })
      .then((data) => {
        if (data.messages && data.messages.length) {
          setMessages(data.messages.map((entry) => ({ role: entry.role === 'assistant' ? 'agent' : 'user', text: entry.message })))
        } else {
          setMessages([GREETING])
        }
      })
      .catch((historyError) => {
        console.error('Could not load chat history:', historyError)
        setMessages([GREETING])
      })
      .finally(() => setHistoryLoading(false))
  }, [])

  useEffect(() => {
    if (historyLoading) return
    const productName = location.state?.productName
    if (!productName || autoSentRef.current) return
    autoSentRef.current = true
    navigate(location.pathname, { replace: true, state: null })
    sendChatMessage(`${productName} ke baare mein batao`)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyLoading, location.state])

  async function sendMessage(event) {
    event.preventDefault()
    const text = message.trim()
    if (!text || loading) return
    setMessage('')
    await sendChatMessage(text)
  }
  async function saveName(event) {
    event.preventDefault()
    if (!name.trim() || naming) return
    setNaming(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE}/buyer/set-name`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sessionId, name: name.trim() }) })
      if (!response.ok) throw new Error('Could not save your name. Please try again.')
      const data = await response.json()
      setNeedsName(false)
      setMessages((current) => [...current, { role: 'agent', text: data.message }])
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setNaming(false)
    }
  }

  // Secondary, non-blocking: complementary product suggestions for the checkout panel.
  // Any failure just hides the section — it must never surface an error or block checkout.
  async function loadCrossSell(productId) {
    setCrossSell([])
    setCrossSellLoading(true)
    try {
      const response = await fetch(`${API_BASE}/products/${productId}/cross-sell`)
      if (!response.ok) throw new Error('cross-sell unavailable')
      const data = await response.json()
      setCrossSell(Array.isArray(data) ? data.slice(0, 3) : [])
    } catch {
      setCrossSell([])
    } finally {
      setCrossSellLoading(false)
    }
  }

  async function selectProduct(productId) {
    setSelecting(true)
    setError('')
    setResult(null)
    setCrossSell([])
    try {
      const response = await fetch(`${API_BASE}/payments/create-order`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ product_id: productId, session_id: sessionId }) })
      if (!response.ok) throw new Error('Checkout could not be prepared. Please try again.')
      setCheckout(await response.json())
      loadCrossSell(productId)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setSelecting(false)
    }
  }

  async function confirmOrder() {
    if (!checkout || confirming) return
    const pendingOrderId = checkout.pending_order_id
    setConfirming(true)
    setError('')
    setResult(null)
    try {
      // 1. Explicit-confirmation gate → backend mints the real Razorpay order for the final amount.
      const sessionResponse = await fetch(`${API_BASE}/payments/checkout-session`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pending_order_id: pendingOrderId, session_id: sessionId, confirmation: 'yes' }) })
      const session = await sessionResponse.json()
      if (!sessionResponse.ok) throw new Error(session.detail || 'Could not start Razorpay checkout.')
      if (session.status === 'failed') { setResult(session); setCheckout(null); setConfirming(false); return }

      // 2. Fetch ONLY the public Razorpay Key ID (the secret never leaves the server).
      const keyResponse = await fetch(`${API_BASE}/payments/razorpay-key`)
      const keyData = await keyResponse.json()
      if (!keyResponse.ok || !keyData.key_id) throw new Error('Razorpay key unavailable — check RAZORPAY_KEY_ID in the backend .env.')
      if (typeof window.Razorpay !== 'function') throw new Error('Razorpay checkout script did not load. Check your connection and retry.')

      // 3. Open the Razorpay-branded popup (UPI / Card / Netbanking, Razorpay logo).
      const rzp = new window.Razorpay({
        key: keyData.key_id,
        amount: session.amount, // already in paise, straight from the backend
        currency: session.currency,
        order_id: session.razorpay_order_id, // the order created in step 1
        name: 'StrideFit',
        description: session.description,
        theme: { color: '#9B8CFF' }, // StrideFit accent
        handler: (response) => finalizeOrder(response, pendingOrderId),
        modal: {
          ondismiss: () => {
            setConfirming(false)
            setError('Payment window band ho gaya — order abhi confirm nahi hua. "Confirm order" se dobara try kar sakte hain.')
          },
        },
      })
      rzp.on('payment.failed', (response) => {
        setConfirming(false)
        setError(response?.error?.description || 'Razorpay payment failed. Please try again.')
      })
      rzp.open()
    } catch (requestError) {
      setError(requestError.message)
      setConfirming(false)
    }
  }

  async function finalizeOrder(razorpayResponse, pendingOrderId) {
    setError('')
    try {
      // 4. Payment succeeded inside the widget → run the existing confirm-order "Bar" gate.
      const response = await fetch(`${API_BASE}/payments/confirm-order`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pending_order_id: pendingOrderId, session_id: sessionId, confirmation: 'yes', razorpay_payment_id: razorpayResponse?.razorpay_payment_id }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.detail || 'Payment confirmation failed.')
      if (data.status === 'failed') {
        setResult(data)
      } else {
        setResult({ ...data, status: 'success', razorpay_payment_id: razorpayResponse?.razorpay_payment_id })
      }
      setCheckout(null)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setConfirming(false)
    }
  }

  return <main className="min-h-screen bg-background px-4 py-5 font-body text-text-primary sm:px-8 lg:px-12"><div className="mx-auto max-w-7xl"><header className="flex items-center justify-between border-b border-border pb-5"><div className="flex items-center gap-3"><Logo /><div><p className="font-heading text-xl font-bold">StrideFit</p><p className="text-xs text-text-muted">Your everyday movement, upgraded.</p></div></div><div className="flex items-center gap-3"><button type="button" onClick={startNewChat} className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-muted transition hover:border-accent-start/70 hover:text-text-primary"><NewChatIcon />New Chat</button><Link className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-muted transition hover:border-accent-start/70 hover:text-text-primary" to="/catalog">Catalog</Link><Link className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-muted transition hover:border-accent-start/70 hover:text-text-primary" to="/dashboard">View as Merchant</Link><AppStatus variant="warning">TEST MODE</AppStatus></div></header>
    {error && <div className="mt-5 rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-red-200">{error}</div>}
    <div className="grid gap-6 py-7 lg:grid-cols-[minmax(0,0.86fr)_minmax(0,1.14fr)]"><section className="flex min-h-[650px] flex-col"><div className="mb-5"><p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-start">Personal shopper</p><h1 className="mt-2 font-heading text-3xl font-bold">Find your next stride.</h1><p className="mt-2 text-sm text-text-muted">Tell me what you need, and I&apos;ll keep the recommendations grounded in the StrideFit catalog.</p></div><Card className="flex flex-1 flex-col p-4"><div className="flex-1 space-y-3 overflow-y-auto pr-1">{historyLoading ? <div className="space-y-3"><div className="h-14 w-2/3 animate-pulse rounded-2xl bg-surface" /><div className="ml-auto h-10 w-1/2 animate-pulse rounded-2xl bg-surface" /></div> : messages.map((item, index) => <Message key={`${item.role}-${index}`} role={item.role}>{item.text}</Message>)}{loading && <Message role="agent"><span className="animate-pulse text-text-muted">Thinking through the catalog…</span></Message>}</div>{needsName && <form className="mt-4 border-t border-border pt-4" onSubmit={saveName}><label className="text-sm font-semibold">What should I call you?</label><div className="mt-2 flex gap-2"><input className="min-w-0 flex-1 rounded-lg border border-border bg-background px-3 py-2.5 text-sm outline-none placeholder:text-text-muted focus:border-accent-start" value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" /><Button disabled={naming}>{naming ? 'Saving…' : 'Save name'}</Button></div></form>}<form className="mt-4 flex gap-2 border-t border-border pt-4" onSubmit={sendMessage}><input className="min-w-0 flex-1 rounded-lg border border-border bg-background px-4 py-3 text-sm outline-none placeholder:text-text-muted focus:border-accent-start" value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Try: running shoes under ₹3000" /><Button disabled={loading || !message.trim()}>Send</Button></form></Card></section>
      <section><div className="mb-5 flex items-end justify-between"><div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-start">StrideFit catalog</p><h2 className="mt-2 font-heading text-2xl font-bold">Recommended for you</h2></div><span className="text-sm text-text-muted">{products.length} matches</span></div>{products.length ? <div className="grid gap-4 sm:grid-cols-2">{products.map((product) => <ProductCard key={product.id} product={product} onSelect={selectProduct} selecting={selecting} />)}</div> : <Card className="flex min-h-[300px] items-center justify-center text-center"><div><p className="font-heading text-xl font-semibold">Your shortlist will appear here.</p><p className="mt-2 max-w-sm text-sm leading-6 text-text-muted">Start a conversation to get real-time recommendations from the StrideFit catalog.</p></div></Card>}{checkout && <Card className="mt-5 border-accent-start/40 bg-surface p-5"><div className="flex items-center justify-between"><div><p className="text-sm font-semibold uppercase tracking-wider text-accent-start">Checkout review</p><h3 className="mt-1 font-heading text-xl font-bold">Ready when you are.</h3></div><AppStatus variant="warning">Confirmation needed</AppStatus></div><div className="mt-5 space-y-3 text-sm"><div className="flex justify-between text-text-muted"><span>Original amount</span><span className="text-text-primary">{formatMoney(checkout.amount)}</span></div><div className="flex justify-between text-text-muted"><span>Special discount</span><span className="text-green-300">−{formatMoney(checkout.discount_amount)}</span></div><div className="flex justify-between border-t border-border pt-3 font-semibold"><span>Final amount</span><span className="font-heading text-xl">{formatMoney(checkout.final_amount)}</span></div></div><p className="mt-4 text-xs leading-5 text-text-muted">A bounded StrideFit checkout offer has been applied. Please review the final amount before confirming.</p><div className="mt-5 flex gap-2"><Button onClick={confirmOrder} disabled={confirming}>{confirming ? 'Confirming…' : 'Confirm order'}</Button><Button variant="secondary" onClick={() => setCheckout(null)} disabled={confirming}>Cancel</Button></div></Card>}{checkout && (crossSellLoading || crossSell.length > 0) && <Card className="mt-4 border-border/70 bg-surface/60 p-4"><div className="flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">You might also like</p><span className="text-[11px] text-text-muted">Optional add-ons</span></div>{crossSellLoading ? <p className="mt-3 text-xs text-text-muted animate-pulse">Finding complementary picks…</p> : <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{crossSell.map((item) => <div key={item.id} onClick={() => navigate(`/product/${item.id}`)} role="button" tabIndex={0} className="cursor-pointer rounded-lg border border-border bg-background/40 px-3 py-2.5 transition hover:border-accent-start/70"><p className="text-sm font-semibold leading-tight">{item.name}</p><p className="mt-1 text-xs text-text-primary">{formatMoney(item.price)}</p>{item.reason && <p className="mt-1 text-[11px] leading-4 text-text-muted">{item.reason}</p>}</div>)}</div>}</Card>}{result && <Card className={`mt-5 ${result.status === 'success' ? 'border-success/40' : 'border-danger/40'}`}><AppStatus variant={result.status === 'success' ? 'success' : 'danger'}>{result.status === 'success' ? 'Payment successful' : 'Payment failed'}</AppStatus><h3 className="mt-4 font-heading text-xl font-bold">{result.status === 'success' ? 'Your StrideFit order is confirmed.' : 'We couldn&apos;t complete that payment.'}</h3>{result.status === 'success' ? <div className="mt-2 space-y-1 text-sm text-text-muted"><p>Razorpay order ID: <span className="font-mono text-text-primary">{result.order_id}</span></p>{result.razorpay_payment_id && <p>Razorpay payment ID: <span className="font-mono text-text-primary">{result.razorpay_payment_id}</span></p>}</div> : <p className="mt-2 text-sm leading-6 text-text-muted">{result.message}</p>}</Card>}<SavedForReview /></section></div></div></main>
}
