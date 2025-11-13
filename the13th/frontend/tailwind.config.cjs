/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          purple: "#6b21a8", // Tailwind purple-800
          purpleLight: "#7e22ce", // Tailwind purple-700
          grayBg: "#f3f4f6", // Tailwind gray-100
          grayCard: "#e5e7eb", // Tailwind gray-200
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
};
