'use client';

import React, { useState } from 'react';
import {
  LayoutDashboard,
  Layers,
  MessageSquare,
  FileCheck2,
  GitFork,
  ShieldCheck,
} from 'lucide-react';
import { CapabilityKey, CanonicalRole, Dossier, CEGGraph } from '../../types/cci';
import { DossierHeader } from './DossierHeader';
import { DossierOverviewTab } from './DossierOverviewTab';
import { CapabilityBreakdownTable } from './CapabilityBreakdownTable';
import { ContradictionDiagnosticsCard } from './ContradictionDiagnosticsCard';
import { InterviewProbesPanel } from './InterviewProbesPanel';
import { ClaimsMatrix } from './ClaimsMatrix';
import { GraphViewer } from './GraphViewer';
import { ExpertWeightOverrideModal } from './ExpertWeightOverrideModal';
import { InterviewScorecardModal } from './InterviewScorecardModal';
import { AuditTrailViewer } from './AuditTrailViewer';
import { EvidenceProvenanceModal } from './EvidenceProvenanceModal';

export const DossierView: React.FC<{
  initialDossier: Dossier;
  graph: CEGGraph;
  candidateName?: string;
  onSelectCandidate?: (candidateId: string, name: string) => void;
}> = ({ initialDossier, graph, candidateName = 'Alice Developer', onSelectCandidate }) => {
  const [dossier, setDossier] = useState<Dossier>(initialDossier);
  const [activeSubTab, setActiveSubTab] = useState<'overview' | 'capabilities' | 'probes' | 'claims' | 'graph'>('overview');
  const [selectedCapability, setSelectedCapability] = useState<CapabilityKey | null>(null);
  const [inspectedEvidenceId, setInspectedEvidenceId] = useState<string | null>(null);
  const [isWeightsModalOpen, setIsWeightsModalOpen] = useState(false);
  const [isScorecardModalOpen, setIsScorecardModalOpen] = useState(false);
  const [auditRefreshTrigger, setAuditRefreshTrigger] = useState(0);

  // Sync state if initialDossier changes
  React.useEffect(() => {
    setDossier(initialDossier);
  }, [initialDossier]);

  const [customWeights, setCustomWeights] = useState<Record<CapabilityKey, number>>({
    backend_engineering: 0.25,
    database_engineering: 0.15,
    software_architecture: 0.12,
    testing_quality: 0.10,
    devops_cloud: 0.08,
    security: 0.08,
    algorithms_problem_solving: 0.08,
    collaboration: 0.05,
    documentation_communication: 0.05,
    data_engineering: 0.02,
    frontend_engineering: 0.01,
    machine_learning: 0.01,
  });

  const handleApplyWeights = (newWeights: Record<CapabilityKey, number>) => {
    setCustomWeights(newWeights);

    // Functional rescore of RCI
    let observedWeightSum = 0;
    let weightedScoreSum = 0;

    Object.entries(dossier.capability_estimates).forEach(([key, est]) => {
      if (est.is_observed && est.estimate !== null) {
        const w = newWeights[key as CapabilityKey] || 0;
        observedWeightSum += w;
        weightedScoreSum += w * est.estimate;
      }
    });

    const newRci = observedWeightSum > 0 ? weightedScoreSum / observedWeightSum : null;

    setDossier((prev) => ({
      ...prev,
      rci: newRci,
    }));

    // Trigger audit trail refresh after override
    setTimeout(() => {
      setAuditRefreshTrigger((t) => t + 1);
    }, 300);
  };

  return (
    <div className="space-y-6">
      {/* 1. Header with RCI, Coverage, Candidate Switcher, and Export */}
      <DossierHeader
        dossier={dossier}
        candidateName={candidateName}
        onOpenWeightsModal={() => setIsWeightsModalOpen(true)}
        onSelectCandidate={onSelectCandidate}
      />

      {/* 2. Focused Dossier Sub-Navigation Tabs */}
      <div className="flex items-center gap-1.5 p-1 bg-slate-900 border border-slate-800 rounded-xl overflow-x-auto text-xs">
        <button
          type="button"
          onClick={() => setActiveSubTab('overview')}
          className={`px-3.5 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 shrink-0 ${
            activeSubTab === 'overview'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span>Executive Overview</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab('capabilities')}
          className={`px-3.5 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 shrink-0 ${
            activeSubTab === 'capabilities'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>12 Core Capabilities</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab('probes')}
          className={`px-3.5 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 shrink-0 ${
            activeSubTab === 'probes'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          <span>Interview Guide &amp; Scorecard</span>
          {dossier.interview_probes && dossier.interview_probes.length > 0 && (
            <span className="px-1.5 py-0.2 bg-indigo-500/20 text-indigo-300 rounded-full text-[10px] font-mono">
              {dossier.interview_probes.length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab('claims')}
          className={`px-3.5 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 shrink-0 ${
            activeSubTab === 'claims'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <FileCheck2 className="w-4 h-4" />
          <span>Claims &amp; Code Proof</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveSubTab('graph')}
          className={`px-3.5 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 shrink-0 ${
            activeSubTab === 'graph'
              ? 'bg-indigo-600 text-white shadow-sm'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <GitFork className="w-4 h-4" />
          <span>Evidence Graph &amp; Audit Log</span>
        </button>
      </div>

      {/* 3. Tab Contents */}
      {activeSubTab === 'overview' && (
        <DossierOverviewTab
          dossier={dossier}
          candidateName={candidateName}
          onNavigateToTab={(tab) => setActiveSubTab(tab)}
          onSelectCapability={(key) => setSelectedCapability(key)}
        />
      )}

      {activeSubTab === 'capabilities' && (
        <CapabilityBreakdownTable
          estimates={dossier.capability_estimates}
          weights={customWeights}
          selectedCapability={selectedCapability}
          onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
        />
      )}

      {activeSubTab === 'probes' && (
        <InterviewProbesPanel
          probes={dossier.interview_probes}
          questions={dossier.interview_questions}
          selectedCapability={selectedCapability}
          onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
          onOpenScorecard={() => setIsScorecardModalOpen(true)}
          onInspectEvidence={(id) => setInspectedEvidenceId(id)}
        />
      )}

      {activeSubTab === 'claims' && (
        <div className="space-y-6">
          <ContradictionDiagnosticsCard
            conflicts={dossier.capability_conflicts}
            selectedCapability={selectedCapability}
            onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
          />

          <ClaimsMatrix
            claims={dossier.claims_corroboration}
            selectedCapability={selectedCapability}
            onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
            onInspectEvidence={(id) => setInspectedEvidenceId(id)}
          />
        </div>
      )}

      {activeSubTab === 'graph' && (
        <div className="space-y-6">
          <GraphViewer
            graph={graph}
            selectedCapability={selectedCapability}
            onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
            onInspectEvidence={(id) => setInspectedEvidenceId(id)}
          />

          <AuditTrailViewer
            candidateId={dossier.candidate_id}
            refreshTrigger={auditRefreshTrigger}
          />
        </div>
      )}

      {/* Expert Weight Override Modal */}
      <ExpertWeightOverrideModal
        isOpen={isWeightsModalOpen}
        onClose={() => setIsWeightsModalOpen(false)}
        currentRole={dossier.role}
        currentWeights={customWeights}
        estimates={dossier.capability_estimates}
        candidateId={dossier.candidate_id}
        onApplyWeights={handleApplyWeights}
      />

      {/* Live Interview Scorecard Modal */}
      <InterviewScorecardModal
        isOpen={isScorecardModalOpen}
        onClose={() => setIsScorecardModalOpen(false)}
        candidateId={dossier.candidate_id}
        candidateName={candidateName}
        probes={dossier.interview_probes}
        questions={dossier.interview_questions}
        onFeedbackSubmitted={() => {
          setAuditRefreshTrigger((t) => t + 1);
        }}
      />

      {/* 6-Factor Evidence Provenance & Static AST Decomposition Modal */}
      <EvidenceProvenanceModal
        isOpen={!!inspectedEvidenceId}
        onClose={() => setInspectedEvidenceId(null)}
        nodeId={inspectedEvidenceId}
        graph={graph}
        dossier={dossier}
      />
    </div>
  );
};
