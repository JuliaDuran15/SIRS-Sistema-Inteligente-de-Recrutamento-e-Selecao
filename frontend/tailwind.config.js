export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans  : ["'Plus Jakarta Sans'", "'Instrument Sans'", "sans-serif"],
        serif : ["'Instrument Serif'", "serif"],
        mono  : ["'JetBrains Mono'",   "monospace"],
      },
    },
  },
  plugins: [],
}