/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: {
          DEFAULT: '#0B0F17',
          deep: '#070A0F',
        },
        surface: {
          1: '#111827',
          2: '#182032',
          3: '#1F2B42',
        },
        border: {
          subtle: '#1E293B',
          active: '#334155',
          glow: '#06B6D4',
        },
        cyan: {
          DEFAULT: '#06B6D4',
          bright: '#38BDF8',
          dim: '#0891B2',
          glow: 'rgba(6, 182, 212, 0.25)',
        },
        amber: {
          DEFAULT: '#F59E0B',
          bright: '#FBBF24',
          dim: '#D97706',
          glow: 'rgba(245, 158, 11, 0.25)',
        },
        emerald: {
          DEFAULT: '#10B981',
          bright: '#34D399',
          dim: '#059669',
          glow: 'rgba(16, 185, 129, 0.25)',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        'cyan-glow': '0 0 20px -3px rgba(6, 182, 212, 0.35)',
        'amber-glow': '0 0 20px -3px rgba(245, 158, 11, 0.35)',
        'emerald-glow': '0 0 20px -3px rgba(16, 185, 129, 0.35)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
      },
    },
  },
  plugins: [],
}
