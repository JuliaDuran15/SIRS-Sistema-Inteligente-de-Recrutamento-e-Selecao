/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["'Plus Jakarta Sans'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      colors: {
        brand: {
          black:   "#07111A",
          teal:    "#0E5068",
          sky:     "#4DC8E8",
          ocean:   "#1A8BBF",
          pale:    "#7DD8F0",
          emerald: "#1AAA80",
          mint:    "#2EE8B4",
          cloud:   "#DFF0F6",
        },
      },
      boxShadow: {
        'gradient': '0 4px 14px 0 rgba(77, 200, 232, 0.4)',
      }
    },
  },
  plugins: [],
}