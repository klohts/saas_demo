/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        accent: "#B8A9C9", // lavender
        primary: "#6B5B95", // purple
        dark: "#1F1F1F",
        light: "#F5F5F5",
        card: "#F2E9E4",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        heading: ["Poppins", "sans-serif"],
      },
    },
  },
  plugins: [],
};
