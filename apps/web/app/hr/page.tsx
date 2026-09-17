import type { Metadata } from "next";
import { HRDashboard } from "../../components/hr/HRDashboard";

export const metadata: Metadata = {
  title: "Hiring Dashboard | CandidateX",
  description: "A simple candidate review workspace for hiring teams.",
};

export default function HRPage() {
  return <HRDashboard />;
}
