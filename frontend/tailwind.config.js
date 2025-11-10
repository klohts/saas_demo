/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--color-bg)',
        surface: 'var(--color-surface)',
        surfaceAlt: 'var(--color-surface-alt)',
        accent: 'var(--color-accent)',
        accentLight: 'var(--color-accent-light)',
        text: 'var(--color-text)',
      },
    },
  },
  plugins: [],
}
