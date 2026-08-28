export default function Logo() {
  return (
    <div className="flex h-[88px] w-[88px] items-center justify-center rounded-[22px] border border-white/10 bg-[linear-gradient(145deg,#0F0F14,#1A1A22)] shadow-badge">
      <svg width="58" height="58" viewBox="0 0 58 58" fill="none" aria-label="StrideFit logo" role="img">
        <path d="M39 15C34 11 21 12 20 19C19 25 27 26 34 28C41 30 40 38 34 42C28 46 18 44 15 40" stroke="url(#stride-gradient)" strokeWidth="5" strokeLinecap="round" />
        <circle cx="40" cy="14" r="4" fill="#9B8CFF" />
        <defs>
          <linearGradient id="stride-gradient" x1="14" y1="13" x2="42" y2="45" gradientUnits="userSpaceOnUse">
            <stop stopColor="#9B8CFF" />
            <stop offset="1" stopColor="#6C5CE7" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  )
}
