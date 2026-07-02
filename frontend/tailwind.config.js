/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#172126",
        canvas: "#f3f5f2",
        accent: "#246b57",
      },
      boxShadow: {
        card: "0 1px 2px rgba(23, 33, 38, 0.06), 0 10px 30px rgba(23, 33, 38, 0.06)",
      },
    },
  },
  plugins: [],
};

