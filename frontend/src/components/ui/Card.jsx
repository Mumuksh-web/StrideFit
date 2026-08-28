export default function Card({ children, className = '', ...props }) {
  return (
    <div className={`rounded-xl border border-border bg-surface p-6 ${className}`} {...props}>
      {children}
    </div>
  )
}
