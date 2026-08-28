export default function Button({ children, variant = 'primary', className = '', ...props }) {
  const styles = variant === 'secondary'
    ? 'border border-border bg-transparent text-text-primary hover:border-accent-start/70 hover:bg-white/5'
    : 'bg-accent-gradient text-white shadow-lg shadow-accent-end/20 hover:brightness-110'

  return (
    <button className={`rounded-lg px-4 py-2.5 font-body text-sm font-semibold transition ${styles} ${className}`} {...props}>
      {children}
    </button>
  )
}
