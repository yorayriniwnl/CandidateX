'use client';

import React, { useState, useEffect } from 'react';
import { Check, RefreshCw, Sliders, AlertCircle, Sparkles, ShieldAlert } from 'lucide-react';
import { CapabilityEstimate, CapabilityKey, CanonicalRole, Dossier, CEGGraph } from '../../types/cci';
import { submitRecruiterOverride } from '../../lib/api';
import { GlassModal } from '@/components/ui/GlassModal';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassButton } from '@/components/ui/GlassButton';
import { RadialGauge } from '@/components/ui/RadialGauge';
import { ProgressBar } from '@/components/ui/ProgressBar';
import { GlowBadge } from '@/components/ui/GlowBadge';

const ALL_CAPABILITIES: { key: CapabilityKey; label: string }[] = [
  { key: 'backend_engineering', label: 'Backend Engineering' },
  { key: 'frontend_engineering', label: 'Frontend Engineering' },
  { key: 'database_engineering', label: 'Database Engineering' },
  { key: 'devops_cloud', label: 'DevOps & Cloud' },
  { key: 'machine_learning', label: 'Machine Learning' },
  { key: 'data_engineering', label: 'Data Engineering' },
  { key: 'algorithms_problem_solving', label: 'Algorithms & Problem Solving' },
  { key: 'testing_quality', label: 'Testing & Quality' },
  { key: 'security', label: 'Security & Privacy' },
  { key: 'software_architecture', label: 'Software Architecture' },
  { key: 'collaboration', label: 'Collaboration' },
  { key: 'documentation_communication', label: 'Documentation & Communication' },
];

const DEFAULT_ROLE_WEIGHTS: Record<CanonicalRole, Record<CapabilityKey, number>> = {
  backend: {
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
  },
  frontend: {
    frontend_engineering: 0.30,
    testing_quality: 0.12,
    software_architecture: 0.10,
    backend_engineering: 0.08,
    security: 0.08,
    documentation_communication: 0.08,
    collaboration: 0.08,
    algorithms_problem_solving: 0.06,
    devops_cloud: 0.04,
    database_engineering: 0.02,
    data_engineering: 0.02,
    machine_learning: 0.02,
  },
  fullstack: {
    backend_engineering: 0.20,
    frontend_engineering: 0.20,
    database_engineering: 0.12,
    testing_quality: 0.10,
    software_architecture: 0.10,
    devops_cloud: 0.08,
    security: 0.06,
    collaboration: 0.05,
    documentation_communication: 0.05,
    algorithms_problem_solving: 0.04,
    data_engineering: 0.00,
    machine_learning: 0.00,
  },
  ml_engineer: {
    machine_learning: 0.30,
    data_engineering: 0.18,
    algorithms_problem_solving: 0.14,
    backend_engineering: 0.10,
    testing_quality: 0.08,
    devops_cloud: 0.06,
    software_architecture: 0.06,
    documentation_communication: 0.04,
    collaboration: 0.04,
    database_engineering: 0.00,
    security: 0.00,
    frontend_engineering: 0.00,
  },
  devops_cloud: {
    devops_cloud: 0.30,
    security: 0.18,
    backend_engineering: 0.12,
    testing_quality: 0.10,
    software_architecture: 0.08,
    database_engineering: 0.06,
    collaboration: 0.06,
    documentation_communication: 0.06,
    algorithms_problem_solving: 0.04,
    data_engineering: 0.00,
    machine_learning: 0.00,
    frontend_engineering: 0.00,
  },
  data_engineer: {
    data_engineering: 0.30,
    database_engineering: 0.20,
    backend_engineering: 0.14,
    devops_cloud: 0.10,
    testing_quality: 0.08,
    algorithms_problem_solving: 0.06,
    software_architecture: 0.04,
    collaboration: 0.04,
    documentation_communication: 0.04,
    machine_learning: 0.00,
    security: 0.00,
    frontend_engineering: 0.00,
  },
};

export const ExpertWeightOverrideModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  currentRole: CanonicalRole;
  currentWeights: Record<CapabilityKey, number>;
  estimates: Record<CapabilityKey, CapabilityEstimate>;
  candidateId?: string;
  onApplyWeights: (weights: Record<CapabilityKey, number>, dossier: Dossier, graph: CEGGraph) => void;
}> = ({ isOpen, onClose, currentRole, currentWeights, estimates, candidateId, onApplyWeights }) => {
  const [weights, setWeights] = useState<Record<CapabilityKey, number>>({ ...currentWeights });
  const [saveError, setSaveError] = useState('');
  const [saving, setSaving] = useState(false);
  const [justification, setJustification] = useState(
    'Recruiter adjustments aligned with specialized hiring requirements.'
  );

  useEffect(() => {
    setWeights({ ...currentWeights });
  }, [currentWeights, isOpen]);

  const totalSum = Object.values(weights).reduce((acc, val) => acc + val, 0);
  const isValidSum = Math.abs(totalSum - 1.0) < 0.005;

  let observedWeightSum = 0;
  let weightedScoreSum = 0;
  ALL_CAPABILITIES.forEach(({ key }) => {
    const est = estimates[key];
    if (est && est.is_observed && est.estimate !== null) {
      const w = weights[key] || 0;
      observedWeightSum += w;
      weightedScoreSum += w * est.estimate;
    }
  });

  const simulatedRCI = observedWeightSum > 0 ? weightedScoreSum / observedWeightSum : null;

  const handleSliderChange = (key: CapabilityKey, val: number) => {
    setWeights((prev) => ({
      ...prev,
      [key]: val,
    }));
  };

  const handleNormalize = () => {
    if (totalSum <= 0) return;
    const normalized: Record<CapabilityKey, number> = {} as any;
    ALL_CAPABILITIES.forEach(({ key }) => {
      normalized[key] = Number(((weights[key] || 0) / totalSum).toFixed(4));
    });
    setWeights(normalized);
  };

  const handleReset = () => {
    const defaults = DEFAULT_ROLE_WEIGHTS[currentRole] || DEFAULT_ROLE_WEIGHTS.backend;
    setWeights({ ...defaults });
  };

  const handleSave = async () => {
    let finalWeights = { ...weights };
    if (!isValidSum && totalSum > 0) {
      ALL_CAPABILITIES.forEach(({ key }) => {
        finalWeights[key] = (finalWeights[key] || 0) / totalSum;
      });
    }

    if (!candidateId || totalSum <= 0 || saving) return;
    setSaving(true); setSaveError('');
    try {
      const result = await submitRecruiterOverride({
        candidate_id: candidateId, role_weights: finalWeights,
        justification: justification || 'Recruiter role weight override',
      });
      onApplyWeights(finalWeights, result.dossier, result.graph);
      onClose();
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : 'Override failed. The dossier is unchanged.');
    } finally { setSaving(false); }
  };

  return (
    <GlassModal
      isOpen={isOpen}
      onClose={onClose}
      title="Expert Role Weight Calibration"
      subtitle={`Adjust capability weightings for role "${currentRole}"`}
      size="lg"
    >
      <div className="flex flex-col h-full max-h-[85vh]">
        {saveError && <p role="alert" className="p-4 text-rose-300 bg-rose-500/10 mb-4 rounded-lg">{saveError}</p>}
        
        {/* Live Simulation Callout */}
        <div className="p-4 bg-slate-950/50 border-b border-slate-800 grid grid-cols-2 gap-4">
          <div className="flex items-center gap-4">
            <RadialGauge
              value={simulatedRCI !== null ? simulatedRCI / 100 : 0}
              size={64}
              strokeWidth={6}
              color={simulatedRCI !== null ? '#6366f1' : '#475569'}
              label="RCI"
              showPercentage={false}
              animated
            />
            <div>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono block">
                Simulated RCI
              </span>
              <div className="text-2xl font-black text-indigo-400 font-mono">
                {simulatedRCI !== null ? simulatedRCI.toFixed(1) : 'UNKNOWN'}
              </div>
            </div>
          </div>

          <div className="flex flex-col justify-center space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">
                Total Weight (Must = 1.0)
              </span>
              <span
                className={`text-sm font-bold font-mono ${
                  isValidSum ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {totalSum.toFixed(3)}
              </span>
            </div>
            <ProgressBar 
              value={totalSum > 1 ? 1 : totalSum} 
              color={isValidSum ? 'emerald' : 'amber'} 
              size="sm" 
            />
            {!isValidSum && (
              <GlassButton
                variant="ghost"
                size="sm"
                onClick={handleNormalize}
                icon={<Sparkles className="w-3 h-3" />}
                className="mt-2 self-end text-amber-300"
              >
                Normalize
              </GlassButton>
            )}
          </div>
        </div>

        {/* Sliders List */}
        <div className="p-5 overflow-y-auto space-y-3.5 flex-1">
          {ALL_CAPABILITIES.map(({ key, label }) => {
            const w = weights[key] || 0;
            const est = estimates[key];
            const isObserved = est && est.is_observed && est.estimate !== null;

            return (
              <div key={key} className="space-y-1 bg-slate-950/40 p-3 rounded-lg border border-slate-800/60">
                <div className="flex justify-between items-center text-xs mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-200">{label}</span>
                    {!isObserved && (
                      <GlowBadge variant="neutral" size="sm">
                        Unobserved
                      </GlowBadge>
                    )}
                  </div>
                  <span className="font-mono text-indigo-400 font-semibold">
                    {(w * 100).toFixed(1)}%
                  </span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="0.50"
                  step="0.01"
                  value={w}
                  onChange={(e) => handleSliderChange(key, parseFloat(e.target.value))}
                  className="w-full accent-indigo-500 h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer"
                />
              </div>
            );
          })}
        </div>

        {/* Mandatory Audit Justification */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-indigo-400" />
              <span>Mandatory Audit Trail Justification</span>
            </label>
            <span className="text-[10px] text-slate-500 font-mono">Immutable Logged Event</span>
          </div>
          <GlassInput
            variant="textarea"
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="Explain why role capability weights were adjusted for this evaluation..."
          />
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between">
          <GlassButton
            variant="ghost"
            onClick={handleReset}
            icon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Reset to Role Defaults
          </GlassButton>

          <div className="flex items-center gap-2">
            <GlassButton variant="ghost" onClick={onClose}>
              Cancel
            </GlassButton>
            <GlassButton
              variant="primary"
              onClick={handleSave}
              disabled={saving || totalSum <= 0 || !candidateId}
              loading={saving}
              icon={<Check className="w-3.5 h-3.5" />}
            >
              Apply Role Weights
            </GlassButton>
          </div>
        </div>
      </div>
    </GlassModal>
  );
};
