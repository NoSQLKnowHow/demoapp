import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        prism: {
          navy: "#0f172a",
          teal: "#14b8a6",
          slate: "#1e293b",
        },
      },
    },
  },
  plugins: [],
} satisfies Config;
