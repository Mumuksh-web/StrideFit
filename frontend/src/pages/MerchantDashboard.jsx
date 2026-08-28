import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Logo from '../components/Logo'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'

const API_BASE = 'http://127.0.0.1:8000'
const typeLabels = {
  cross_sell_pattern: ['Cross-sell', 'accent'],
  revenue_trend: ['Revenue trend', 'success'],
  top_performing_product: ['Top product', 'warning'],
  discount_effectiveness: ['Discount impact', 'accent'],
  category_performance: ['Category performance', 'neutral'],
}

function formatMoney(value) {
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value || 0))
}

function formatTime(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

function FlagIcon() {
  return <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 3v18M5 4h11l-2 4 2 4H5" strokeLinecap="round" strokeLinejoin="round" /></svg>
}

function CommerceReadinessCard({ readiness }) {
  const [expanded, setExpanded] = useState(false)
  if (!readiness) return null
  const labelVariant = readiness.overall_label === 'Excellent readiness' ? 'success' : readiness.overall_label === 'Good readiness' ? 'warning' : 'danger'

  return (
    <Card className="cursor-pointer p-5" onClick={() => setExpanded((current) => !current)}>
      <p className="text-sm text-text-muted">AI Commerce Readiness</p>
      <div className="mt-4 flex items-end gap-3"><p className="font-heading text-3xl font-bold">{readiness.overall_score != null ? `${readiness.overall_score}/100` : 'N/A'}</p><Badge variant={labelVariant}>{readiness.overall_label}</Badge></div>
      <p className="mt-2 text-xs text-text-muted">{expanded ? 'Click to collapse' : 'Click to see component breakdown'}</p>
      {expanded && <div className="mt-4 space-y-2.5 border-t border-border pt-4">{readiness.components.map((component) => <div className="flex items-start justify-between gap-3 text-xs" key={component.name}><div className="min-w-0"><p className="font-semibold text-text-primary">{component.name}</p><p className="mt-0.5 leading-5 text-text-muted">{component.explanation}</p></div><span className={`shrink-0 font-heading text-sm font-bold ${component.status === 'unavailable' ? 'text-text-muted' : 'text-text-primary'}`}>{component.score != null ? `${component.score}/${component.max}` : 'N/A'}</span></div>)}</div>}
    </Card>
  )
}

function LostRevenueCard({ opportunity }) {
  const [expanded, setExpanded] = useState(false)
  const isUnmet = opportunity.type === 'unmet_demand'
  const evidence = opportunity.evidence

  return (
    <Card className="cursor-pointer p-5 transition hover:-translate-y-0.5 hover:border-accent-start/40" onClick={() => setExpanded((current) => !current)}>
      <div className="flex items-start justify-between gap-3">
        <span className="text-2xl">{isUnmet ? '🔥' : '💸'}</span>
        <Badge variant={isUnmet ? 'danger' : 'warning'}>{isUnmet ? 'Unmet Demand' : 'Price Sensitive'}</Badge>
      </div>
      <h3 className="mt-4 font-heading text-lg font-bold leading-snug">{opportunity.title}</h3>
      <p className="mt-2 text-sm leading-6 text-text-muted">{opportunity.description}</p>
      <div className="mt-4 flex items-center justify-between border-t border-border pt-4">
        <div><p className="text-xs text-text-muted">Affected buyers</p><p className="mt-1 font-heading text-xl font-bold">{opportunity.affected_buyers_count}</p></div>
        <div className="text-right"><p className="text-xs text-text-muted">Estimated opportunity</p><p className="mt-1 font-heading text-xl font-bold text-green-300">{opportunity.estimated_revenue != null ? formatMoney(opportunity.estimated_revenue) : 'Unavailable'}</p></div>
      </div>
      <p className="mt-3 text-[11px] leading-5 text-text-muted">{opportunity.calculation_note} <span className="text-amber-300">25% is an assumed conversion rate for this demo, not an observed number.</span></p>
      {expanded && <div className="mt-4 space-y-1.5 border-t border-border pt-4 text-xs"><div className="flex justify-between"><span className="text-text-muted">Category</span><span className="text-text-primary">{opportunity.category || '—'}</span></div><div className="flex justify-between"><span className="text-text-muted">Requirement</span><span className="text-text-primary">{opportunity.requirement || '—'}</span></div><div className="flex justify-between"><span className="text-text-muted">Budget range</span><span className="text-text-primary">{opportunity.budget_range}</span></div><div className="flex justify-between"><span className="text-text-muted">Relevant intent records</span><span className="text-text-primary">{evidence.intent_count}</span></div><div className="flex justify-between"><span className="text-text-muted">Confidence</span><span className="text-text-primary capitalize">{evidence.confidence}</span></div><div className="flex justify-between"><span className="text-text-muted">AOV used</span><span className="text-text-primary">{evidence.aov_used != null ? `${formatMoney(evidence.aov_used)} (${evidence.aov_source})` : 'Unavailable'}</span></div><div className="flex justify-between"><span className="text-text-muted">Conversion assumption</span><span className="text-text-primary">{Math.round(evidence.conversion_assumption * 100)}% (assumed)</span></div></div>}
      <p className="mt-3 text-[11px] text-text-muted">{expanded ? 'Click to collapse' : 'Click for evidence'}</p>
    </Card>
  )
}

function InsightCard({ insight, onMarkForReview }) {
  const [marking, setMarking] = useState(false)
  const [label, variant] = typeLabels[insight.insight_type] || ['AI insight', 'neutral']
  const underReview = insight.status === 'under_review'

  async function handleMarkForReview() {
    setMarking(true)
    try {
      await onMarkForReview(insight)
    } finally {
      setMarking(false)
    }
  }

  return (
    <Card className={`flex h-full flex-col justify-between bg-surface/90 p-5 transition hover:-translate-y-0.5 hover:border-accent-start/40 ${underReview ? 'opacity-60' : ''}`}>
      <div>
        <div className="flex items-center justify-between gap-3">
          <Badge variant={variant}>{label}</Badge>
          <div className="flex items-center gap-2">{underReview && <Badge variant="neutral">Under Review</Badge>}<span className="text-xs text-text-muted">{insight.priority} priority</span></div>
        </div>
        <h3 className="mt-5 font-heading text-lg font-semibold leading-snug text-text-primary">{insight.description}</h3>
      </div>
      <div className="mt-6 border-t border-border pt-4">
        <p className="text-xs uppercase tracking-wider text-text-muted">Suggested move</p>
        <p className="mt-2 text-sm leading-6 text-text-primary">{insight.suggested_offer || 'Keep monitoring this signal.'}</p>
        <div className="mt-4 flex items-end justify-between">
          <span className="text-xs text-text-muted">Estimated impact</span>
          <span className="font-heading text-lg font-bold text-green-300">{formatMoney(insight.revenue_impact_estimate)}</span>
        </div>
        <div className="mt-4 flex justify-end"><Button variant="secondary" className="px-3 py-1.5 text-xs" disabled={marking} onClick={handleMarkForReview}>{marking ? (underReview ? 'Unmarking…' : 'Marking…') : (underReview ? 'Unmark' : 'Mark for Review')}</Button></div>
      </div>
    </Card>
  )
}

function DashboardSkeleton() {
  return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[1, 2, 3, 4].map((item) => <div className="h-32 animate-pulse rounded-xl border border-border bg-surface" key={item} />)}</div>
}

function OrderBreakdown({ breakdown = {} }) {
  const statuses = [
    ['confirmed', 'bg-success'],
    ['pending', 'bg-warning'],
    ['failed', 'bg-danger'],
  ]
  return <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-text-muted">{statuses.map(([status, color]) => <span className="inline-flex items-center gap-1" key={status}><span className={`h-1.5 w-1.5 rounded-full ${color}`} />{breakdown[status] ?? 0} {status}</span>)}</div>
}

export default function MerchantDashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [insights, setInsights] = useState([])
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [insightFilter, setInsightFilter] = useState('all')
  const [auditFilter, setAuditFilter] = useState('all')
  const [lostRevenue, setLostRevenue] = useState(null)
  const [lostRevenueLoading, setLostRevenueLoading] = useState(true)
  const [readiness, setReadiness] = useState(null)

  async function loadDashboard() {
    setLoading(true)
    setError('')
    try {
      const [dashboardResponse, insightsResponse, auditResponse] = await Promise.all([
        fetch(`${API_BASE}/merchant/dashboard`),
        fetch(`${API_BASE}/merchant/insights`),
        fetch(`${API_BASE}/audit-logs`),
      ])
      if (![dashboardResponse, insightsResponse, auditResponse].every((response) => response.ok)) throw new Error('The dashboard service returned an error.')
      const [dashboardData, insightsData, auditData] = await Promise.all([dashboardResponse.json(), insightsResponse.json(), auditResponse.json()])
      setDashboard(dashboardData)
      setInsights(insightsData.insights || [])
      setAuditLogs(auditData || [])
    } catch (loadError) {
      setError(loadError.message || 'Unable to load dashboard data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadDashboard() }, [])

  useEffect(() => {
    fetch(`${API_BASE}/merchant/lost-revenue-radar`)
      .then((response) => { if (!response.ok) throw new Error('Lost Revenue Radar unavailable'); return response.json() })
      .then(setLostRevenue)
      .catch(() => setLostRevenue(null))
      .finally(() => setLostRevenueLoading(false))
  }, [])

  useEffect(() => {
    fetch(`${API_BASE}/merchant/commerce-readiness`)
      .then((response) => { if (!response.ok) throw new Error('Commerce readiness unavailable'); return response.json() })
      .then(setReadiness)
      .catch(() => setReadiness(null))
  }, [])

  async function markInsightForReview(insight) {
    try {
      const response = await fetch(`${API_BASE}/merchant/insights/${insight.id}/review`, { method: 'PATCH' })
      if (!response.ok) throw new Error('Unable to mark this insight for review.')
      const updated = await response.json()
      setInsights((current) => current.map((item) => item.id === insight.id ? updated : item))
    } catch (reviewError) {
      setError(reviewError.message || 'Unable to mark this insight for review.')
    }
  }

  async function flagAuditLog(logId) {
    try {
      const response = await fetch(`${API_BASE}/audit-logs/${logId}/flag`, { method: 'PATCH' })
      if (!response.ok) throw new Error('Unable to flag this audit event.')
      const updated = await response.json()
      setAuditLogs((current) => current.map((item) => item.id === logId ? updated : item))
    } catch (flagError) {
      setError(flagError.message || 'Unable to flag this audit event.')
    }
  }

  const visibleInsights = insightFilter === 'under_review' ? insights.filter((insight) => insight.status === 'under_review') : insights
  const visibleAuditLogs = auditFilter === 'flagged' ? auditLogs.filter((log) => log.flagged_for_review) : auditLogs

  const kpis = [
    ['Total revenue', dashboard ? formatMoney(dashboard.total_revenue) : '—', 'Confirmed orders'],
    ['Total orders', dashboard?.total_orders ?? '—', 'Qualifying order volume'],
    ['Active AI insights', dashboard?.active_insights?.length ?? insights.length, 'Signals ready to act on'],
    ['AI-assisted revenue', dashboard ? formatMoney(dashboard.ai_assisted_revenue) : '—', 'Confirmed discounted orders'],
  ]

  return (
    <main className="min-h-screen bg-background px-5 py-6 font-body text-text-primary sm:px-8 lg:px-12">
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-wrap items-center justify-between gap-5 border-b border-border pb-6">
          <div className="flex items-center gap-3">
            <Logo />
            <div><p className="font-heading text-xl font-bold">StrideFit</p><p className="text-xs text-text-muted">Merchant command center</p></div>
          </div>
          <div className="flex items-center gap-4"><p className="hidden text-sm text-text-muted sm:block">Good evening, StrideFit! 👋</p><Link className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-muted transition hover:border-accent-start/70 hover:text-text-primary" to="/shop">Shop</Link><Link className="rounded-lg border border-border px-3 py-2 text-xs font-semibold text-text-muted transition hover:border-accent-start/70 hover:text-text-primary" to="/catalog">Catalog</Link><Badge variant="warning">TEST MODE</Badge></div>
        </header>

        {error && <div className="mt-6 flex items-center justify-between gap-4 rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-red-200"><span>{error}</span><Button onClick={loadDashboard} variant="secondary">Retry</Button></div>}
        <section className="py-8"><div className="mb-5"><p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-start">Overview</p><h1 className="mt-2 font-heading text-3xl font-bold">Growth at a glance</h1></div>{loading ? <DashboardSkeleton /> : <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{kpis.map(([label, value, helper]) => <Card className="p-5" key={label}><p className="text-sm text-text-muted">{label}</p><p className="mt-4 font-heading text-3xl font-bold">{value}</p>{label === 'Total orders' ? <OrderBreakdown breakdown={dashboard.order_breakdown} /> : <p className="mt-2 text-xs text-text-muted">{helper}</p>}</Card>)}</div>}
          {readiness && <div className="mt-4 max-w-xs sm:max-w-sm"><CommerceReadinessCard readiness={readiness} /></div>}
        </section>

        <section className="pb-10"><div className="mb-5 flex items-end justify-between"><div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-start">AI signal room</p><h2 className="mt-2 font-heading text-2xl font-bold">Growth opportunities</h2></div><span className="text-sm text-text-muted">{visibleInsights.length} signals</span></div><div className="mb-5 flex gap-2"><button className={`rounded-full px-4 py-2 text-xs font-semibold transition ${insightFilter === 'all' ? 'bg-accent-gradient text-white' : 'border border-border text-text-muted hover:text-text-primary'}`} onClick={() => setInsightFilter('all')} type="button">All</button><button className={`rounded-full px-4 py-2 text-xs font-semibold transition ${insightFilter === 'under_review' ? 'bg-accent-gradient text-white' : 'border border-border text-text-muted hover:text-text-primary'}`} onClick={() => setInsightFilter('under_review')} type="button">Under Review</button></div>{loading ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><div className="h-64 animate-pulse rounded-xl bg-surface" /><div className="h-64 animate-pulse rounded-xl bg-surface" /></div> : visibleInsights.length ? <><p className="mb-4 text-sm text-text-muted">Estimated opportunity impact: <strong className="text-text-primary">{dashboard ? formatMoney(dashboard.estimated_opportunity_impact) : '—'}</strong></p><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{visibleInsights.map((insight) => <InsightCard insight={insight} key={insight.id} onMarkForReview={markInsightForReview} />)}</div></> : <Card>{insightFilter === 'under_review' ? 'No insights under review yet.' : 'No active insights available yet.'}</Card>}</section>

        <section className="pb-10"><div className="mb-5 flex items-end justify-between"><div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-start">Lost Revenue Radar</p><h2 className="mt-2 font-heading text-2xl font-bold">Demand we&apos;re not capturing</h2></div>{lostRevenue && <span className="text-sm text-text-muted">{lostRevenue.opportunities.length} opportunit{lostRevenue.opportunities.length === 1 ? 'y' : 'ies'}</span>}</div>
          {lostRevenueLoading ? <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3"><div className="h-56 animate-pulse rounded-xl bg-surface" /><div className="h-56 animate-pulse rounded-xl bg-surface" /></div>
            : lostRevenue && lostRevenue.opportunities.length ? <><p className="mb-4 text-xs leading-5 text-text-muted">Estimated revenue below assumes a <strong className="text-text-primary">25% conversion rate</strong> — this is an assumption for this demo, not an observed historical rate.</p><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{lostRevenue.opportunities.map((opportunity, index) => <LostRevenueCard key={`${opportunity.type}-${opportunity.category}-${opportunity.requirement}-${index}`} opportunity={opportunity} />)}</div></>
            : <Card className="flex min-h-[160px] flex-col items-center justify-center gap-2 text-center"><p className="font-heading text-lg font-semibold">Data build ho raha hai jaise jaise customers shop karte hain.</p><p className="max-w-md text-sm leading-6 text-text-muted">Lost Revenue Radar becomes more accurate as more buyer interactions are recorded.</p></Card>}
        </section>

        <section className="pb-10"><div className="mb-5 flex items-end justify-between"><div><p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-start">Traceability</p><h2 className="mt-2 font-heading text-2xl font-bold">Audit trail</h2></div><div className="flex gap-2"><button className={`rounded-full px-4 py-2 text-xs font-semibold transition ${auditFilter === 'all' ? 'bg-accent-gradient text-white' : 'border border-border text-text-muted hover:text-text-primary'}`} onClick={() => setAuditFilter('all')} type="button">All</button><button className={`rounded-full px-4 py-2 text-xs font-semibold transition ${auditFilter === 'flagged' ? 'bg-accent-gradient text-white' : 'border border-border text-text-muted hover:text-text-primary'}`} onClick={() => setAuditFilter('flagged')} type="button">Flagged</button></div></div><Card className="overflow-hidden p-0"><div className="overflow-x-auto"><table className="w-full min-w-[860px] text-left text-sm"><thead className="border-b border-border bg-white/[0.03] text-xs uppercase tracking-wider text-text-muted"><tr><th className="px-5 py-4">Time</th><th className="px-5 py-4">Action</th><th className="px-5 py-4">Amount</th><th className="px-5 py-4">Reason</th><th className="px-5 py-4">Limit check</th><th className="px-5 py-4">Status</th><th className="px-5 py-4">Review</th></tr></thead><tbody className="divide-y divide-border">{loading ? <tr><td className="px-5 py-8 text-text-muted" colSpan="7">Loading audit events…</td></tr> : visibleAuditLogs.length ? visibleAuditLogs.map((log) => <tr className={`text-text-primary ${log.flagged_for_review ? 'bg-danger/5' : ''}`} key={log.id}><td className="whitespace-nowrap px-5 py-4 text-text-muted">{formatTime(log.timestamp)}</td><td className="px-5 py-4 font-semibold"><span className="inline-flex items-center gap-2">{log.flagged_for_review && <span className="h-1.5 w-1.5 rounded-full bg-danger" />}{log.action.replaceAll('_', ' ')}</span></td><td className="px-5 py-4">{log.amount ? formatMoney(log.amount) : '—'}</td><td className="max-w-sm px-5 py-4 text-text-muted">{log.reason || '—'}</td><td className="px-5 py-4"><span className={log.limit_check_passed ? 'text-green-300' : 'text-red-300'}>{log.limit_check_passed ? '✓ Passed' : '✗ Failed'}</span></td><td className="px-5 py-4"><Badge variant={log.status === 'created' || log.status === 'confirmed' ? 'success' : log.status === 'failed' ? 'danger' : 'neutral'}>{log.status}</Badge></td><td className="px-5 py-4">{log.flagged_for_review ? <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-red-300"><FlagIcon />Flagged</span> : <Button variant="secondary" className="px-3 py-1.5 text-xs" onClick={() => flagAuditLog(log.id)}>Flag</Button>}</td></tr>) : <tr><td className="px-5 py-8 text-text-muted" colSpan="7">{auditFilter === 'flagged' ? 'No flagged audit events yet.' : 'No audit events recorded yet.'}</td></tr>}</tbody></table></div></Card></section>
      </div>
    </main>
  )
}
