import type { Metadata } from "next";
import { HRDashboard } from "../../components/hr/HRDashboard";
import { PlatformHeader } from '../../components/navigation/PlatformHeader';

export const metadata: Metadata = {
  title: "Candidates & Students | CandidateX",
  description: "Manage candidate and student profiles, audit technical capabilities, and review verified evidence dossiers.",
};

export default function HRPage() {
  return (
    <div className="studio-surface">
      <PlatformHeader surface="candidates" />
      <HRDashboard />
    </div>
  );
}
