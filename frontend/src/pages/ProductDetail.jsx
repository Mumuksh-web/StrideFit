import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import Logo from '../components/Logo'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import ProductIllustration from '../components/ProductIllustration'
import { isInReviewList, subscribeReviewList, toggleReviewItem } from '../lib/reviewList'

const API_BASE = 'http://127.0.0.1:8000'

function money(value) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 0 }).format(Number(value || 0)) }

function BookmarkIcon({ filled }) {
  return filled
    ? <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor"><path d="M6 2a2 2 0 0 0-2 2v18l8-5.2L20 22V4a2 2 0 0 0-2-2H6z" /></svg>
    : <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4.5L5 21V4a1 1 0 0 1 1-1z" /></svg>
}

export default function ProductDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [product, setProduct] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [marked, setMarked] = useState(false)

  useEffect(() => {
    fetch(`${API_BASE}/products/${id}`)
      .then((response) => { if (!response.ok) throw new Error('Product details could not be loaded.'); return response.json() })
      .then(setProduct)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => { if (product) setMarked(isInReviewList(product.id)) }, [product])
  useEffect(() => subscribeReviewList(() => { if (product) setMarked(isInReviewList(product.id)) }), [product])

  return <main className="min-h-screen bg-background px-4 py-5 font-body text-text-primary sm:px-8 lg:px-12"><div className="mx-auto max-w-6xl"><header className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-5"><Link className="flex items-center gap-3" to="/catalog"><Logo /><div><p className="font-heading text-xl font-bold">StrideFit</p><p className="text-xs text-text-muted">Product details</p></div></Link><nav className="flex items-center gap-2"><Link className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-muted" to="/shop">Shop</Link><Link className="rounded-lg bg-white/5 px-3 py-2 text-xs font-semibold text-text-primary" to="/catalog">Catalog</Link><Badge variant="warning">TEST MODE</Badge></nav></header>{loading ? <div className="mt-10 h-96 animate-pulse rounded-xl bg-surface" /> : error ? <Card className="mt-10 border-danger/40 text-red-200">{error}</Card> : product && <section className="grid gap-8 py-10 lg:grid-cols-[1fr_0.9fr] lg:items-center"><ProductIllustration category={product.category} large /><div><Link className="text-sm text-text-muted hover:text-text-primary" to="/catalog">← Back to catalog</Link><div className="mt-6"><div className="flex items-center gap-2"><Badge variant="accent">{product.category}</Badge><button className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold transition ${marked ? 'bg-accent-gradient text-white' : 'border border-border text-text-muted hover:text-text-primary'}`} onClick={() => toggleReviewItem(product)} type="button"><BookmarkIcon filled={marked} />{marked ? 'Marked for Review' : 'Mark for Review'}</button></div><h1 className="mt-4 font-heading text-4xl font-bold leading-tight">{product.name}</h1><p className="mt-5 font-heading text-3xl font-bold text-accent-start">{money(product.price)}</p><p className="mt-6 text-base leading-8 text-text-muted">{product.description}</p><div className="mt-6 flex items-center gap-2 text-sm"><span className="h-2 w-2 rounded-full bg-success" />{product.stock} in stock</div><Button className="mt-8" onClick={() => navigate('/shop', { state: { productName: product.name, productId: product.id } })}>Ask AI about this</Button></div></div></section>}</div></main>
}
