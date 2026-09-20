import type { Metadata } from "next";
import { HRDashboard } from "../../components/hr/HRDashboard";
import { PlatformHeader } from "../../components/navigation/PlatformHeader";

export const metadata: Metadata = {
  title: "Hiring Dashboard | CandidateX",
  description: "A simple candidate review workspace for hiring teams.",
};

export default function HRPage() {
  return (
    <div className="min-h-screen bg-[#030712] text-slate-100">
      <PlatformHeader surface="hiring" status="sample" />
      <HRDashboard />
    </div>
  );
}
