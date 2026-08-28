/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        background: '#1C1D24',
        surface: '#212228',
        border: '#2E2F38',
        'accent-start': '#9B8CFF',
        'accent-end': '#6C5CE7',
        'text-primary': '#F5F5F7',
        'text-muted': '#8A8B94',
        success: '#16A34A',
        warning: '#F59E0B',
        danger: '#DC2626',
      },
      fontFamily: { heading: ['Space Grotesk', 'sans-serif'], body: ['Inter', 'sans-serif'] },
      boxShadow: { badge: '0 14px 30px rgba(0, 0, 0, 0.32)' },
    },
  },
  plugins: [
    function ({ addUtilities }) {
      addUtilities({
        '.bg-accent-gradient': { background: 'linear-gradient(135deg, #9B8CFF 0%, #6C5CE7 100%)' },
      })
    },
  ],
}

