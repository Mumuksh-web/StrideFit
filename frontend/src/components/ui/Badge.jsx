const variants = {
  accent: 'bg-accent-start/15 text-accent-start ring-accent-start/30',
  success: 'bg-success/15 text-green-300 ring-success/30',
  warning: 'bg-warning/15 text-amber-300 ring-warning/30',
  danger: 'bg-danger/15 text-red-300 ring-danger/30',
  neutral: 'bg-white/10 text-text-muted ring-white/10',
}

export default function Badge({ children, variant = 'neutral' }) {
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${variants[variant]}`}>{children}</span>
}
