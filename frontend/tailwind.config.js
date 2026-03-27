/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:  '#f0f4ff',
          100: '#dce6ff',
          500: '#3b5bdb',
          600: '#2f4bbd',
          700: '#1f3864',
          900: '#0f1e3a',
        },
      },
    },
  },
  plugins: [],
}
