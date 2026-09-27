import type { Metadata } from "next";
import { HRDashboard } from "../../components/hr/HRDashboard";
import { PlatformHeader } from '../../components/navigation/PlatformHeader';

export const metadata: Metadata = {
  title: "Hiring Dashboard | CandidateX",
  description: "A simple candidate review workspace for hiring teams.",
};

export default function HRPage() {
  return (
    <div className="studio-surface">
      <PlatformHeader surface="candidates" />
      <HRDashboard />
    </div>
  );
}
