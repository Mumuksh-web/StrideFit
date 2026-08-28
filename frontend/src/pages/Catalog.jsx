import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Logo from '../components/Logo'
import Badge from '../components/ui/Badge'
import Card from '../components/ui/Card'
import ProductIllustration from '../components/ProductIllustration'
import { getReviewList, subscribeReviewList, toggleReviewItem } from '../lib/reviewList'

const API_BASE = 'http://127.0.0.1:8000'
const filters = [['all', 'All'], ['running shoes', 'Running Shoes'], ['sneakers', 'Sneakers'], ['sports socks', 'Socks'], ['sports accessories', 'Accessories']]

function money(value) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', minimumFractionDigits: 0 }).format(Number(value || 0)) }

function BookmarkIcon({ filled }) {
  return filled
    ? <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor"><path d="M6 2a2 2 0 0 0-2 2v18l8-5.2L20 22V4a2 2 0 0 0-2-2H6z" /></svg>
    : <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4.5L5 21V4a1 1 0 0 1 1-1z" /></svg>
}

export default function Catalog() {
  const [products, setProducts] = useState([])
  const [activeFilter, setActiveFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reviewList, setReviewList] = useState(() => getReviewList())

  useEffect(() => {
    fetch(`${API_BASE}/products`)
      .then((response) => { if (!response.ok) throw new Error('Catalog could not be loaded.'); return response.json() })
      .then(setProducts)
      .catch((requestError) => setError(requestError.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => subscribeReviewList(setReviewList), [])

  const visibleProducts = activeFilter === 'all' ? products : products.filter((product) => product.category === activeFilter)
  return <main className="min-h-screen bg-background px-4 py-5 font-body text-text-primary sm:px-8 lg:px-12"><div className="mx-auto max-w-7xl"><header className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-5"><Link className="flex items-center gap-3" to="/shop"><Logo /><div><p className="font-heading text-xl font-bold">StrideFit</p><p className="text-xs text-text-muted">The full movement catalog</p></div></Link><nav className="flex items-center gap-2"><Link className="rounded-lg bg-white/5 px-3 py-2 text-xs font-semibold text-text-primary" to="/shop">Shop</Link><Link className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-muted" to="/dashboard">Dashboard</Link><Badge variant="warning">TEST MODE</Badge></nav></header><section className="py-10"><p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-start">StrideFit catalog</p><div className="mt-2 flex flex-wrap items-end justify-between gap-4"><div><h1 className="font-heading text-4xl font-bold">Built to keep you moving.</h1><p className="mt-3 text-text-muted">Browse the collection, then ask the AI shopper when you want a second opinion.</p></div><span className="flex items-center gap-2 text-sm text-text-muted"><span>{products.length} products</span><span className="inline-flex items-center gap-1 rounded-full bg-white/5 px-2.5 py-1 text-xs font-semibold text-accent-start">🔖 {reviewList.length} saved for review</span></span></div><div className="mt-8 flex flex-wrap gap-2">{filters.map(([value, label]) => <button className={`rounded-full px-4 py-2 text-sm font-semibold transition ${activeFilter === value ? 'bg-accent-gradient text-white' : 'border border-border text-text-muted hover:text-text-primary'}`} key={value} onClick={() => setActiveFilter(value)}>{label}</button>)}</div></section>{error && <Card className="border-danger/40 text-red-200">{error}</Card>}{loading ? <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{[1, 2, 3, 4, 5, 6].map((item) => <div className="h-96 animate-pulse rounded-xl bg-surface" key={item} />)}</div> : <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">{visibleProducts.map((product) => { const marked = reviewList.some((item) => item.id === product.id); return <Card className="p-4" key={product.id}><div className="relative"><ProductIllustration category={product.category} /><button className={`absolute right-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full transition ${marked ? 'bg-accent-gradient text-white' : 'bg-black/30 text-text-muted hover:text-white'}`} onClick={(event) => { event.preventDefault(); event.stopPropagation(); toggleReviewItem(product) }} type="button" aria-label={marked ? 'Remove from review list' : 'Mark for review'} title={marked ? 'Marked for review' : 'Mark for review'}><BookmarkIcon filled={marked} /></button></div><div className="mt-4 flex items-center justify-between gap-3"><Badge variant="neutral">{product.category}</Badge><span className="font-heading text-xl font-bold">{money(product.price)}</span></div><h2 className="mt-3 font-heading text-xl font-bold">{product.name}</h2><p className="mt-2 min-h-12 text-sm leading-6 text-text-muted">{product.description}</p><Link className="mt-5 block rounded-lg border border-border px-4 py-2.5 text-center text-sm font-semibold text-text-primary transition hover:border-accent-start/70" to={`/product/${product.id}`}>View Details</Link></Card> })}</div>}</div></main>
}
