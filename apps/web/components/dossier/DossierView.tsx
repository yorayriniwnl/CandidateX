'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import {
  LayoutDashboard,
  Layers,
  MessageSquare,
  FileCheck2,
  GitFork,
} from 'lucide-react';
import { CapabilityKey, CanonicalRole, Dossier, CEGGraph } from '../../types/cci';
import { TabSlider } from '../ui/TabSlider';
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

type DossierSubTab = 'overview' | 'capabilities' | 'probes' | 'claims' | 'graph';

const DOSSIER_TABS = (probeCount: number) => [
  { key: 'overview', label: 'Executive Overview', icon: <LayoutDashboard className="w-4 h-4" /> },
  { key: 'capabilities', label: '12 Core Capabilities', icon: <Layers className="w-4 h-4" /> },
  { key: 'probes', label: 'Interview Guide', icon: <MessageSquare className="w-4 h-4" />, badge: probeCount > 0 ? probeCount : undefined },
  { key: 'claims', label: 'Claims & Proof', icon: <FileCheck2 className="w-4 h-4" /> },
  { key: 'graph', label: 'Evidence & Audit', icon: <GitFork className="w-4 h-4" /> },
];

const tabContentVariants: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.25, ease: 'easeOut' } },
  exit: { opacity: 0, y: -4, transition: { duration: 0.1 } },
};

export const DossierView: React.FC<{
  initialDossier: Dossier;
  graph: CEGGraph;
  candidateName?: string;
  onSelectCandidate?: (candidateId: string, name: string) => void;
}> = ({ initialDossier, graph: initialGraph, candidateName = 'Jordan Example (SYNTHETIC DEMONSTRATION DATA)', onSelectCandidate }) => {
  const [graph, setGraph] = useState<CEGGraph>(initialGraph);
  const [dossier, setDossier] = useState<Dossier>(initialDossier);
  const [activeSubTab, setActiveSubTab] = useState<DossierSubTab>('overview');
  const [selectedCapability, setSelectedCapability] = useState<CapabilityKey | null>(null);
  const [inspectedEvidenceId, setInspectedEvidenceId] = useState<string | null>(null);
  const [isWeightsModalOpen, setIsWeightsModalOpen] = useState(false);
  const [isScorecardModalOpen, setIsScorecardModalOpen] = useState(false);
  const [auditRefreshTrigger, setAuditRefreshTrigger] = useState(0);

  React.useEffect(() => {
    setDossier(initialDossier);
    setGraph(initialGraph);
  }, [initialDossier, initialGraph]);

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

  const handleApplyWeights = (newWeights: Record<CapabilityKey, number>, confirmedDossier: Dossier, confirmedGraph: CEGGraph) => {
    setCustomWeights(newWeights);
    setDossier(confirmedDossier);
    setGraph(confirmedGraph);
    setAuditRefreshTrigger(t => t + 1);
  };

  React.useEffect(() => {
    if (initialDossier.role_weights) setCustomWeights(initialDossier.role_weights);
  }, [initialDossier]);

  const probeCount = dossier.interview_probes?.length || 0;

  return (
    <div className="space-y-5">
      {/* Header with RCI gauge, candidate info, actions */}
      <DossierHeader
        dossier={dossier}
        candidateName={candidateName}
        onOpenWeightsModal={() => setIsWeightsModalOpen(true)}
        onSelectCandidate={onSelectCandidate}
      />

      {/* Sub-tabs with sliding indicator */}
      <TabSlider
        tabs={DOSSIER_TABS(probeCount)}
        activeKey={activeSubTab}
        onChange={(key) => setActiveSubTab(key as DossierSubTab)}
        size="sm"
      />

      {/* Tab content with transitions */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeSubTab}
          variants={tabContentVariants}
          initial="initial"
          animate="animate"
          exit="exit"
        >
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
        </motion.div>
      </AnimatePresence>

      {/* Modals */}
      <ExpertWeightOverrideModal
        isOpen={isWeightsModalOpen}
        onClose={() => setIsWeightsModalOpen(false)}
        currentRole={dossier.role}
        currentWeights={customWeights}
        estimates={dossier.capability_estimates}
        candidateId={dossier.candidate_id}
        onApplyWeights={handleApplyWeights}
      />

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
