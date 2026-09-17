'use client';

import React, { useState, useEffect } from 'react';
import { Check, RefreshCw, Sliders, X, AlertCircle, Sparkles } from 'lucide-react';
import { CapabilityEstimate, CapabilityKey, CanonicalRole } from '../../types/cci';

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
  onApplyWeights: (weights: Record<CapabilityKey, number>) => void;
}> = ({ isOpen, onClose, currentRole, currentWeights, estimates, onApplyWeights }) => {
  const [weights, setWeights] = useState<Record<CapabilityKey, number>>({ ...currentWeights });

  useEffect(() => {
    setWeights({ ...currentWeights });
  }, [currentWeights, isOpen]);

  if (!isOpen) return null;

  const totalSum = Object.values(weights).reduce((acc, val) => acc + val, 0);
  const isValidSum = Math.abs(totalSum - 1.0) < 0.005;

  // Functional recalculation of RCI:
  // RCI = sum_{k in O} (w_k * q_k) / sum_{k in O} w_k
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

  const handleSave = () => {
    // If not strictly normalized, normalize before applying
    let finalWeights = { ...weights };
    if (!isValidSum && totalSum > 0) {
      ALL_CAPABILITIES.forEach(({ key }) => {
        finalWeights[key] = (finalWeights[key] || 0) / totalSum;
      });
    }
    onApplyWeights(finalWeights);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Expert Role Weights Override</h2>
              <p className="text-xs text-slate-400">
                Adjust capability weightings w_k for role &ldquo;{currentRole}&rdquo;. Total weight must sum to 1.0.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Live Simulation Callout */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <div>
              <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono block">
                Simulated RCI (Functional Rescore)
              </span>
              <div className="text-2xl font-black text-indigo-400 font-mono">
                {simulatedRCI !== null ? simulatedRCI.toFixed(1) : 'UNKNOWN'}
                <span className="text-xs text-slate-500 font-normal"> / 100</span>
              </div>
            </div>
          </div>

          <div className="flex flex-col items-end justify-center">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono block mb-1">
              Total Weight Sum (Must = 1.0)
            </span>
            <div className="flex items-center gap-2">
              <span
                className={`text-base font-bold font-mono ${
                  isValidSum ? 'text-emerald-400' : 'text-amber-400'
                }`}
              >
                {totalSum.toFixed(3)}
              </span>
              {!isValidSum && (
                <button
                  type="button"
                  onClick={handleNormalize}
                  className="px-2 py-0.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded text-[11px] font-semibold flex items-center gap-1"
                >
                  <Sparkles className="w-3 h-3" />
                  Normalize
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Sliders List */}
        <div className="p-5 overflow-y-auto space-y-3.5 flex-1">
          {ALL_CAPABILITIES.map(({ key, label }) => {
            const w = weights[key] || 0;
            const est = estimates[key];
            const isObserved = est && est.is_observed && est.estimate !== null;

            return (
              <div key={key} className="space-y-1 bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/60">
                <div className="flex justify-between items-center text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-200">{label}</span>
                    {!isObserved && (
                      <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 text-slate-400 rounded">
                        Unobserved
                      </span>
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

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between">
          <button
            type="button"
            onClick={handleReset}
            className="px-3 py-1.5 text-xs text-slate-400 hover:text-white flex items-center gap-1.5 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset to Role Defaults</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg shadow-md transition-colors flex items-center gap-1.5"
            >
              <Check className="w-3.5 h-3.5" />
              <span>Apply Role Weights</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
