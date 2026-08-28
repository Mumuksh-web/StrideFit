const STORAGE_KEY = 'stridefit-review-list'
const CHANGE_EVENT = 'stridefit-review-list-changed'

export function getReviewList() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function isInReviewList(productId) {
  return getReviewList().some((item) => item.id === productId)
}

export function toggleReviewItem(product) {
  const current = getReviewList()
  const exists = current.some((item) => item.id === product.id)
  const next = exists
    ? current.filter((item) => item.id !== product.id)
    : [...current, { id: product.id, name: product.name, price: product.price, category: product.category }]

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // storage unavailable (e.g. private mode quota) — ignore, in-memory state still updates via the event below
  }

  window.dispatchEvent(new CustomEvent(CHANGE_EVENT, { detail: next }))
  return next
}

export function subscribeReviewList(callback) {
  function handler(event) { callback(event.detail || getReviewList()) }
  window.addEventListener(CHANGE_EVENT, handler)
  return () => window.removeEventListener(CHANGE_EVENT, handler)
}
