'use client';

import React, { useState } from 'react';
import { CapabilityKey, CanonicalRole, Dossier, CEGGraph } from '../../types/cci';
import { DossierHeader } from './DossierHeader';
import { CapabilityBreakdownTable } from './CapabilityBreakdownTable';
import { ContradictionDiagnosticsCard } from './ContradictionDiagnosticsCard';
import { InterviewProbesPanel } from './InterviewProbesPanel';
import { ClaimsMatrix } from './ClaimsMatrix';
import { GraphViewer } from './GraphViewer';
import { ExpertWeightOverrideModal } from './ExpertWeightOverrideModal';

export const DossierView: React.FC<{
  initialDossier: Dossier;
  graph: CEGGraph;
  candidateName?: string;
}> = ({ initialDossier, graph, candidateName = 'Alice Developer' }) => {
  const [dossier, setDossier] = useState<Dossier>(initialDossier);
  const [selectedCapability, setSelectedCapability] = useState<CapabilityKey | null>(null);
  const [isWeightsModalOpen, setIsWeightsModalOpen] = useState(false);
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
  };

  return (
    <div className="space-y-6">
      {/* 1. Header with RCI, Coverage, and Invariant Badges */}
      <DossierHeader
        dossier={dossier}
        candidateName={candidateName}
        onOpenWeightsModal={() => setIsWeightsModalOpen(true)}
      />

      {/* 2. Core Capabilities Point Estimates & Confidence Intervals */}
      <CapabilityBreakdownTable
        estimates={dossier.capability_estimates}
        weights={customWeights}
        selectedCapability={selectedCapability}
        onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
      />

      {/* 3. Contradiction Diagnostics (D_k in [-1, +1]) */}
      <ContradictionDiagnosticsCard
        conflicts={dossier.capability_conflicts}
        selectedCapability={selectedCapability}
        onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
      />

      {/* 4. Prioritized Technical Interview Probes */}
      <InterviewProbesPanel
        probes={dossier.interview_probes}
        questions={dossier.interview_questions}
        selectedCapability={selectedCapability}
        onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
      />

      {/* 5. Self-Claims Verification Matrix */}
      <ClaimsMatrix
        claims={dossier.claims_corroboration}
        selectedCapability={selectedCapability}
        onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
      />

      {/* 6. Candidate Evidence Graph (CEG) Interactive Viewer */}
      <GraphViewer
        graph={graph}
        selectedCapability={selectedCapability}
        onSelectCapability={(key) => setSelectedCapability(selectedCapability === key ? null : key)}
      />

      {/* Expert Weight Override Modal */}
      <ExpertWeightOverrideModal
        isOpen={isWeightsModalOpen}
        onClose={() => setIsWeightsModalOpen(false)}
        currentRole={dossier.role}
        currentWeights={customWeights}
        estimates={dossier.capability_estimates}
        onApplyWeights={handleApplyWeights}
      />
    </div>
  );
};
