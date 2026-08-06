/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // we can use 'media' or 'class'.
  theme: {
    extend: {
      colors: {
        background: '#0B0B0F',
        panel: '#111114',
        accent: '#0ea5e9', // teal/cyan
        textMain: '#f3f4f6',
        textMuted: '#9ca3af',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
