const art = {
  'running shoes': { icon: '↗', tone: 'from-accent-start/80 to-accent-end/50' },
  sneakers: { icon: '◒', tone: 'from-warning/80 to-orange-500/40' },
  'sports socks': { icon: '⌁', tone: 'from-success/80 to-emerald-900/50' },
  'sports accessories': { icon: '✦', tone: 'from-sky-400/80 to-blue-900/50' },
}

export default function ProductIllustration({ category, large = false }) {
  const style = art[category] || art.sneakers
  return <div className={`relative flex ${large ? 'h-80' : 'h-44'} items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br ${style.tone}`}><div className="absolute h-40 w-40 rounded-full border border-white/20 bg-black/10 blur-sm" /><span className={`relative font-heading font-bold text-white/90 ${large ? 'text-8xl' : 'text-6xl'}`}>{style.icon}</span><span className="absolute bottom-3 left-4 text-[10px] font-semibold uppercase tracking-[0.22em] text-white/60">StrideFit / {category}</span></div>
}
