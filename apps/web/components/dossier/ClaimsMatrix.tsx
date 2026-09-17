'use client';

import React, { useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  FileCheck,
  Filter,
  HelpCircle,
  Search,
  XCircle,
} from 'lucide-react';
import { CapabilityKey, ClaimCorroboration, ClaimStatus } from '../../types/cci';

const CAPABILITY_LABELS: Record<CapabilityKey, string> = {
  backend_engineering: 'Backend Engineering',
  frontend_engineering: 'Frontend Engineering',
  database_engineering: 'Database Engineering',
  devops_cloud: 'DevOps & Cloud',
  machine_learning: 'Machine Learning',
  data_engineering: 'Data Engineering',
  algorithms_problem_solving: 'Algorithms & Problem Solving',
  testing_quality: 'Testing & Quality',
  security: 'Security & Privacy',
  software_architecture: 'Software Architecture',
  collaboration: 'Collaboration',
  documentation_communication: 'Documentation & Communication',
};

const STATUS_CONFIG: Record<
  ClaimStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ComponentType<{ className?: string }> }
> = {
  corroborated: {
    label: 'Corroborated',
    bg: 'bg-emerald-500/10',
    text: 'text-emerald-400',
    border: 'border-emerald-500/30',
    icon: CheckCircle2,
  },
  partial: {
    label: 'Partially Corroborated',
    bg: 'bg-amber-500/10',
    text: 'text-amber-400',
    border: 'border-amber-500/30',
    icon: AlertCircle,
  },
  unknown: {
    label: 'Unobserved / Unknown',
    bg: 'bg-slate-800',
    text: 'text-slate-400',
    border: 'border-slate-700',
    icon: HelpCircle,
  },
  contradicted: {
    label: 'Contradicted',
    bg: 'bg-rose-500/10',
    text: 'text-rose-400',
    border: 'border-rose-500/30',
    icon: XCircle,
  },
};

export const ClaimsMatrix: React.FC<{
  claims: ClaimCorroboration[];
  onSelectCapability?: (key: CapabilityKey) => void;
  selectedCapability?: CapabilityKey | null;
  onInspectEvidence?: (evidenceId: string) => void;
}> = ({ claims, onSelectCapability, selectedCapability, onInspectEvidence }) => {
  const [filterStatus, setFilterStatus] = useState<ClaimStatus | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredClaims = claims.filter((claim) => {
    if (filterStatus !== 'all' && claim.status !== filterStatus) return false;
    if (selectedCapability && claim.target_capability !== selectedCapability) return false;
    if (
      searchQuery &&
      !claim.claim_text.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !claim.explanation.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
            <FileCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-100">Self-Claims Verification Matrix</h2>
            <p className="text-xs text-slate-400">
              Cross-referencing CV declarations against repository evidence, commit diffs & tests
            </p>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search claims..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-44"
            />
          </div>

          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5 text-xs">
            {(['all', 'corroborated', 'partial', 'unknown', 'contradicted'] as const).map((st) => (
              <button
                key={st}
                onClick={() => setFilterStatus(st)}
                className={`px-2 py-1 rounded-md text-[11px] font-medium transition-colors capitalize ${
                  filterStatus === st
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Claims List */}
      <div className="space-y-3 pt-1">
        {filteredClaims.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No self-claims match the current filter criteria.
          </div>
        ) : (
          filteredClaims.map((claim) => {
            const statusCfg = STATUS_CONFIG[claim.status] || STATUS_CONFIG.unknown;
            const StatusIcon = statusCfg.icon;

            return (
              <div
                key={claim.claim_id}
                className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 space-y-2.5 hover:border-slate-700 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ${statusCfg.bg} ${statusCfg.text} ${statusCfg.border}`}
                      >
                        <StatusIcon className="w-3 h-3" />
                        {statusCfg.label}
                      </span>
                      <button
                        type="button"
                        onClick={() => onSelectCapability && onSelectCapability(claim.target_capability)}
                        className="text-[11px] font-mono text-indigo-400 hover:underline"
                      >
                        {CAPABILITY_LABELS[claim.target_capability] || claim.target_capability}
                      </button>
                    </div>
                    <p className="text-xs font-semibold text-slate-100 leading-relaxed pt-1">
                      &ldquo;{claim.claim_text}&rdquo;
                    </p>
                  </div>

                  <div className="text-right shrink-0">
                    <span className="text-[11px] font-mono text-slate-400 block">Confidence:</span>
                    <span className="text-xs font-mono font-bold text-slate-200">
                      {(claim.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Explanation */}
                <p className="text-xs text-slate-400 bg-slate-900/60 p-2.5 rounded border border-slate-800/80 leading-relaxed">
                  {claim.explanation}
                </p>

                {/* Citations & Evidence IDs */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[11px] font-mono">
                  {claim.grounding_evidence_ids && claim.grounding_evidence_ids.length > 0 && (
                    <div className="flex items-center gap-1.5 text-slate-500">
                      <span>Evidence:</span>
                      <div className="flex flex-wrap gap-1">
                        {claim.grounding_evidence_ids.map((id) => (
                          <button
                            key={id}
                            type="button"
                            onClick={() => onInspectEvidence && onInspectEvidence(id)}
                            className="px-1.5 py-0.5 bg-slate-900 hover:bg-indigo-950/40 border border-slate-800 hover:border-indigo-500/50 text-slate-300 hover:text-indigo-300 rounded text-[10px] transition-colors cursor-pointer font-mono"
                            title={`Inspect 6-Factor Confidence Decomposition for ${id}`}
                          >
                            {id}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {claim.citation_urls && claim.citation_urls.length > 0 && (
                    <div className="flex items-center gap-2">
                      {claim.citation_urls.map((url, idx) => (
                        <a
                          key={idx}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-[11px]"
                        >
                          <span>{url.replace(/https?:\/\/(www\.)?github\.com\//, '')}</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800/80">
        <span>* Claims extracted strictly from CV and verified against concrete repository manifests.</span>
        <span>Unknown indicates absence of evidence in declared links, not proven falsehood.</span>
      </div>
    </div>
  );
};
