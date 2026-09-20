import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        surface: {
          DEFAULT: "rgba(255, 255, 255, 0.03)",
          hover: "rgba(255, 255, 255, 0.06)",
          active: "rgba(255, 255, 255, 0.08)",
          border: "rgba(255, 255, 255, 0.06)",
        },
      },
      animation: {
        "float-1": "float-1 20s ease-in-out infinite",
        "float-2": "float-2 25s ease-in-out infinite",
        "float-3": "float-3 22s ease-in-out infinite",
        "pulse-glow": "pulse-glow 3s ease-in-out infinite",
        shimmer: "shimmer 3s linear infinite",
        "gauge-fill": "gauge-fill 1.2s cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "fade-in-up": "fade-in-up 0.5s cubic-bezier(0.4, 0, 0.2, 1) forwards",
        "slide-in": "fade-in-up 0.3s cubic-bezier(0.4, 0, 0.2, 1) forwards",
      },
      backdropBlur: {
        xs: "2px",
        "2xl": "40px",
        "3xl": "64px",
      },
      boxShadow: {
        "glow-sm": "0 0 15px rgba(99, 102, 241, 0.08)",
        glow: "0 0 25px rgba(99, 102, 241, 0.12)",
        "glow-lg": "0 0 40px rgba(99, 102, 241, 0.18)",
        "glow-violet": "0 0 25px rgba(139, 92, 246, 0.12)",
        "glow-cyan": "0 0 25px rgba(34, 211, 238, 0.10)",
        "glow-emerald": "0 0 25px rgba(52, 211, 153, 0.10)",
        glass: "0 8px 32px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.06)",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
      },
      transitionTimingFunction: {
        spring: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
    },
  },
  plugins: [],
};
export default config;
