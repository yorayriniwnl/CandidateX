'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  FileCheck,
  HelpCircle,
  XCircle,
} from 'lucide-react';
import { CapabilityKey, ClaimCorroboration, ClaimStatus } from '../../types/cci';
import { GlassCard } from '../ui/GlassCard';
import { GlassInput } from '../ui/GlassInput';
import { GlowBadge } from '../ui/GlowBadge';

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
  { label: string; variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand'; icon: React.ComponentType<{ className?: string }> }
> = {
  corroborated: {
    label: 'Corroborated',
    variant: 'success',
    icon: CheckCircle2,
  },
  partial: {
    label: 'Partially Corroborated',
    variant: 'warning',
    icon: AlertCircle,
  },
  unknown: {
    label: 'Unobserved / Unknown',
    variant: 'neutral',
    icon: HelpCircle,
  },
  contradicted: {
    label: 'Contradicted',
    variant: 'danger',
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
    <GlassCard variant="default" className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/[0.06] pb-3">
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
        <div className="flex flex-wrap items-center gap-3">
          <div className="w-48">
            <GlassInput
              variant="search"
              placeholder="Search claims..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            {(['all', 'corroborated', 'partial', 'unknown', 'contradicted'] as const).map((st) => (
              <button key={st} onClick={() => setFilterStatus(st)} className="focus:outline-none">
                <GlowBadge
                  variant={filterStatus === st ? (st === 'all' ? 'brand' : STATUS_CONFIG[st].variant) : 'neutral'}
                  size="sm"
                  className={filterStatus !== st ? 'opacity-60 hover:opacity-100' : ''}
                >
                  {st.charAt(0).toUpperCase() + st.slice(1)}
                </GlowBadge>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Claims List */}
      <motion.div layout className="space-y-3 pt-1">
        <AnimatePresence>
          {filteredClaims.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-center py-8 text-slate-500 text-xs"
            >
              No self-claims match the current filter criteria.
            </motion.div>
          ) : (
            filteredClaims.map((claim, index) => {
              const statusCfg = STATUS_CONFIG[claim.status] || STATUS_CONFIG.unknown;
              const StatusIcon = statusCfg.icon;

              return (
                <motion.div
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2, delay: index * 0.05 }}
                  key={claim.claim_id}
                >
                  <GlassCard variant="subtle" className="p-4 space-y-2.5">
                    <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <GlowBadge variant={statusCfg.variant} size="sm">
                            <StatusIcon className="w-3 h-3 mr-1" />
                            {statusCfg.label}
                          </GlowBadge>
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
                    <p className="text-xs text-slate-400 bg-white/[0.03] p-2.5 rounded-lg border border-white/[0.05] leading-relaxed">
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
                                className="px-2 py-0.5 glass hover:bg-white/[0.08] border border-white/[0.08] text-slate-300 hover:text-indigo-300 rounded text-[10px] transition-colors cursor-pointer font-mono"
                                title={`Inspect attribution-gated confidence for ${id}`}
                              >
                                {id}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {claim.citation_urls && claim.citation_urls.length > 0 && (
                        <div className="flex items-center gap-2">
                          {claim.citation_urls.map((url, idx) => {
                            let displayName = url.replace(/https?:\/\/(www\.)?github\.com\//, '');
                            if (displayName.length > 35) displayName = displayName.substring(0, 32) + '...';
                            return (
                              <a
                                key={idx}
                                href={url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-1 px-2 py-0.5 glass hover:bg-white/[0.08] border border-white/[0.08] rounded text-indigo-400 hover:text-indigo-300 text-[10px] transition-colors"
                              >
                                <span>{displayName}</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </GlassCard>
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </motion.div>

      <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-white/[0.06]">
        <span>* Claims extracted strictly from CV and verified against concrete repository manifests.</span>
        <span>Unknown indicates absence of evidence in declared links, not proven falsehood.</span>
      </div>
    </GlassCard>
  );
};
