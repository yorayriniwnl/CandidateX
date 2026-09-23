import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CandidateX — Evidence OS",
  description: "Role-aware candidate capability intelligence. Static analysis, traceable evidence, explicit unknowns.",
  other: {
    "darkreader-lock": "true",
    "color-scheme": "dark"
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="min-h-screen bg-[#07090d] text-slate-100 font-[family-name:var(--font-sans)]">
        {children}
      </body>
    </html>
  );
}
