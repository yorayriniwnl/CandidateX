import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import "./studio.css";
import { Suspense } from "react";
import { MotionProvider } from '../components/studio/MotionProvider';
import { NavigationScrollManager } from '../components/navigation/NavigationScrollManager';

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
  title: "CandidateX — Evidence-first hiring intelligence",
  description: "CandidateX brings live evidence review into a human-led technical interview workflow.",
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
    <html lang="en" className={`dark ${inter.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <body className="studio-theme noise-texture antialiased min-h-screen text-slate-100 font-[family-name:var(--font-sans)]" suppressHydrationWarning>
        <div className="studio-atmosphere" aria-hidden="true" />
        <Suspense fallback={null}>
          <NavigationScrollManager />
        </Suspense>
        <MotionProvider><div className="relative z-10">{children}</div></MotionProvider>
      </body>
    </html>
  );
}
