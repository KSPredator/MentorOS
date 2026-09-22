/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  // Design tokens live in src/index.css @theme (Tailwind v4 CSS-first config).
  theme: {
    extend: {},
  },
  plugins: [],
}
