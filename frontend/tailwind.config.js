/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#070910',
          900: '#0a0c10',
          850: '#0e1117',
          800: '#12161d',
          750: '#171c25',
          700: '#1d2430',
          600: '#232a36',
          500: '#2e3746',
        },
        cyan: { 400: '#22d3ee', 500: '#06b6d4' },
        violet: { 400: '#a78bfa', 500: '#8b5cf6', 600: '#7c3aed' },
        muted: '#8b98ab',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 0 1px rgba(34,211,238,0.18), 0 18px 50px -22px rgba(34,211,238,0.35)',
        card: '0 12px 40px -24px rgba(0,0,0,0.9)',
      },
      backgroundImage: {
        'grid-faint':
          'linear-gradient(to right, rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.03) 1px, transparent 1px)',
      },
      keyframes: {
        'fade-up': { '0%': { opacity: '0', transform: 'translateY(6px)' }, '100%': { opacity: '1', transform: 'none' } },
        shimmer: { '100%': { transform: 'translateX(100%)' } },
      },
      animation: {
        'fade-up': 'fade-up 0.28s ease-out both',
        shimmer: 'shimmer 1.6s infinite',
      },
    },
  },
  plugins: [],
}
