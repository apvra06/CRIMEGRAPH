/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0B0F1A",
        surface: "#131826",
        borderDark: "#232A3D",
        amberAccent: "#C99A3C",
        tealAccent: "#4FB6AC",
        alertRed: "#D9480F",
        textMuted: "#8A93A6",
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'monospace'],
        sans: ['"IBM Plex Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

