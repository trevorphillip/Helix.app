/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        'helix-bg':      '#0f1117',
        'helix-surface': '#151821',
        'helix-border':  '#1e2130',
        'helix-deep':    '#111318',
        'helix-teal':    '#1D9E75',
        'helix-amber':   '#EF9F27',
        'helix-text':    '#e8e6df',
        'helix-muted':   '#5F5E5A',
        'helix-mid':     '#888780',
      },
    },
  },
  plugins: [],
}
