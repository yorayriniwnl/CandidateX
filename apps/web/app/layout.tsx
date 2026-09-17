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
  title: "CandidateX — Capability Intelligence",
  description: "AI-powered technical candidate evaluation platform for engineering teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="antialiased min-h-screen bg-[#030712] text-slate-100 font-[family-name:var(--font-sans)]">
        {/* Animated Background Orbs */}
        <div className="fixed inset-0 overflow-hidden pointer-events-none z-0" aria-hidden="true">
          <div
            className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full animate-float-1 opacity-30"
            style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)' }}
          />
          <div
            className="absolute top-[40%] right-[-15%] w-[500px] h-[500px] rounded-full animate-float-2 opacity-25"
            style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.12) 0%, transparent 70%)' }}
          />
          <div
            className="absolute bottom-[-10%] left-[30%] w-[550px] h-[550px] rounded-full animate-float-3 opacity-20"
            style={{ background: 'radial-gradient(circle, rgba(34,211,238,0.10) 0%, transparent 70%)' }}
          />
        </div>
        {/* Content Layer */}
        <div className="relative z-10">
          {children}
        </div>
      </body>
    </html>
  );
}
