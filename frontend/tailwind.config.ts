import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        dukaan: {
          canvas: "#FAF8F5",
          card: "#FFFFFF",
          border: "#E7E2DA",
          primary: "#C2410C",
          primaryDark: "#9A3412",
          accent: "#D97706",
          text: "#1C1917",
          muted: "#6B6560",
          success: "#15803D",
          successBg: "#F0FDF4",
          error: "#B91C1C",
          errorBg: "#FEF2F2",
          warning: "#B45309",
          warningBg: "#FFFBEB",
        },
      },
      boxShadow: {
        warm: "0 2px 8px -2px rgba(45, 35, 25, 0.08), 0 1px 3px -1px rgba(45, 35, 25, 0.05)",
        floating: "0 10px 25px -5px rgba(45, 35, 25, 0.12), 0 8px 10px -6px rgba(45, 35, 25, 0.08)",
      },
    },
  },
  plugins: [],
};
export default config;
