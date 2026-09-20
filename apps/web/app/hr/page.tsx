import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { HRDashboard } from "../../components/hr/HRDashboard";

export const metadata: Metadata = {
  title: "Hiring Dashboard | CandidateX",
  description: "A simple candidate review workspace for hiring teams.",
};

export default function HRPage() {
  return (
    <div className="min-h-screen bg-[#030712] text-slate-100">
      <div className="border-b border-white/[0.06] bg-[#0a0f1e]/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-6 py-3 lg:px-8">
          <Link href="/workspace" className="flex items-center gap-2 text-sm font-medium text-slate-400 transition-colors hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Back to Workspace
          </Link>
          <div className="h-4 w-px bg-white/[0.1]" />
          <Link href="/research-demo" className="text-sm font-medium text-slate-400 transition-colors hover:text-white">
            Research Demo
          </Link>
        </div>
      </div>
      <HRDashboard />
    </div>
  );
}
