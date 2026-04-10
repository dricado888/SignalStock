/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg:       '#09090b',
          surface:  '#111113',
          border:   '#27272a',
          muted:    '#52525b',
          text:     '#f4f4f5',
          subtext:  '#a1a1aa',
          cyan:     '#22d3ee',
          positive: '#4ade80',
          negative: '#f87171',
          amber:    '#f59e0b',
        },
      },
      fontFamily: {
        sans:   ['Inter', 'system-ui', 'sans-serif'],
        mono:   ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
        ticker: ['"JetBrains Mono"', '"Fira Code"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        'cyan-glow': '0 0 0 1px rgba(34,211,238,0.3), 0 4px 20px rgba(34,211,238,0.06)',
      },
    },
  },
  plugins: [],
}
