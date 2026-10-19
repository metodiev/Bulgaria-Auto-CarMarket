/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111f",
        panel: "#0d1b2f",
        edge: "#1d3350",
        accent: "#2dd4bf",
        amber: "#f5b942",
      },
      boxShadow: {
        glow: "0 0 40px rgba(45, 212, 191, 0.12)",
      },
    },
  },
  plugins: [],
};
