'use client';

import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import {
  AlertCircle,
  Award,
  CheckCircle,
  Gauge,
  Sliders,
  ShieldCheck,
  Printer,
  Download,
  FileText,
  ChevronDown,
  Users,
} from 'lucide-react';
import { Dossier } from '../../types/cci';
import { downloadDossier } from '../../lib/api';
import { GlassCard } from '../ui/GlassCard';
import { GlowBadge } from '../ui/GlowBadge';
import { RadialGauge } from '../ui/RadialGauge';
import { AnimatedCounter } from '../ui/AnimatedCounter';
import { GlassButton } from '../ui/GlassButton';

const CANONICAL_CANDIDATE_LIST = [
  { id: '11111111-1111-1111-1111-111111111111', name: 'Example Candidate One', role: 'Backend (Senior)' },
  { id: '22222222-2222-2222-2222-222222222222', name: 'Example Candidate Two', role: 'Frontend (Staff)' },
  { id: '33333333-3333-3333-3333-333333333333', name: 'Example Candidate Three', role: 'ML Engineer (Senior)' },
  { id: '44444444-4444-4444-4444-444444444444', name: 'Example Candidate Four', role: 'DevOps / SRE (Staff)' },
  { id: '55555555-5555-5555-5555-555555555555', name: 'Example Candidate Five', role: 'Fullstack (Principal)' },
  { id: '77777777-7777-7777-7777-777777777777', name: 'Example Candidate Six', role: 'Backend (Discrepancy Demo)' },
];

export const DossierHeader: React.FC<{
  dossier: Dossier;
  candidateName?: string;
  onOpenWeightsModal?: () => void;
  onSelectCandidate?: (candidateId: string, name: string) => void;
}> = ({ dossier, candidateName = 'Example Candidate One', onOpenWeightsModal, onSelectCandidate }) => {
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const [isCandidateMenuOpen, setIsCandidateMenuOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const coveragePercent = Math.round(dossier.coverage * 100);
  const isLowCoverage = dossier.coverage < 0.30 || dossier.is_insufficient_evidence;

  const exportMenuRef = useRef<HTMLDivElement>(null);
  const candidateMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(event.target as Node)) {
        setIsExportMenuOpen(false);
      }
      if (candidateMenuRef.current && !candidateMenuRef.current.contains(event.target as Node)) {
        setIsCandidateMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleDownload = async (format: 'html' | 'markdown' | 'json') => {
    try {
      setIsExporting(true);
      setIsExportMenuOpen(false);
      await downloadDossier(dossier.candidate_id, format, candidateName);
    } catch (err) {
      console.warn('Direct API export failed, falling back to print:', err);
      if (format === 'html') {
        window.print();
      }
    } finally {
      setIsExporting(false);
    }
  };

  const rci = dossier.rci;
  let readinessTier: { label: string; variant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand' } = {
    label: 'Inconclusive / Sparse',
    variant: 'warning',
  };
  if (rci !== null) {
    if (rci >= 88) {
      readinessTier = { label: 'Exceptional (88+)', variant: 'success' };
    } else if (rci >= 75) {
      readinessTier = { label: 'Strong (75-87)', variant: 'brand' };
    } else if (rci >= 60) {
      readinessTier = { label: 'Developing (60-74)', variant: 'info' };
    }
  }

  const getRciGlow = (value: number | null): 'emerald' | 'indigo' | 'amber' | 'rose' | 'none' => {
    if (value === null) return 'none';
    if (value >= 75) return 'emerald';
    if (value >= 50) return 'indigo';
    if (value >= 30) return 'amber';
    return 'rose';
  };

  return (
    <GlassCard variant="strong" glow="indigo" className="space-y-4">
      {/* Low Coverage Warning Banner */}
      {isLowCoverage && (
        <div className="p-3 bg-amber-500/[0.08] border border-amber-500/20 rounded-xl flex items-center gap-2.5 text-xs text-amber-300">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
          <div>
            <span className="font-semibold">Sparse Public Code Footprint ({coveragePercent}%):</span> Most role skills were not observed in public GitHub repos. Missing skills are marked UNKNOWN, never failed. Focus technical interview on unobserved skills.
          </div>
        </div>
      )}

      {/* Hero Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-5 border-b border-white/[0.06] pb-5">
        <div className="flex items-center gap-4">
          <RadialGauge
            value={rci !== null ? rci / 100 : 0}
            size={76}
            strokeWidth={6}
            label="RCI"
            showPercentage={true}
          />
          <div>
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <h1 className="text-2xl font-black tracking-tight text-gradient bg-clip-text text-transparent bg-gradient-to-r from-white to-slate-400">
                {candidateName}
              </h1>

              <GlowBadge variant="brand" size="sm">
                {dossier.role.replace('_', ' ')}
              </GlowBadge>

              <GlowBadge variant={readinessTier.variant} size="sm">
                {readinessTier.label}
              </GlowBadge>

              {/* Quick Candidate Switcher Dropdown */}
              {onSelectCandidate && (
                <div className="relative inline-block ml-1" ref={candidateMenuRef}>
                  <GlassButton
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsCandidateMenuOpen(!isCandidateMenuOpen)}
                    icon={<ChevronDown className="w-3 h-3 opacity-60" />}
                    iconPosition="right"
                  >
                    <Users className="w-3 h-3 text-brand-400 mr-1.5" />
                    Switch
                  </GlassButton>

                  {isCandidateMenuOpen && (
                    <div className="absolute left-0 mt-2 w-64 glass-strong border border-white/[0.12] rounded-xl shadow-2xl py-1.5 z-50 text-xs backdrop-blur-2xl">
                      <div className="px-3 py-1 text-[10px] uppercase font-mono text-slate-500 border-b border-white/[0.06]">
                        Switch Candidate
                      </div>
                      {CANONICAL_CANDIDATE_LIST.map((cand) => (
                        <button
                          key={cand.id}
                          type="button"
                          onClick={() => {
                            setIsCandidateMenuOpen(false);
                            onSelectCandidate(cand.id, cand.name);
                          }}
                          className={`w-full px-3 py-2 text-left hover:bg-white/[0.06] flex items-center justify-between transition-colors ${
                            cand.id === dossier.candidate_id ? 'bg-brand-500/20 text-brand-300 font-semibold' : 'text-slate-300'
                          }`}
                        >
                          <div>
                            <div>{cand.name}</div>
                            <div className="text-[10px] text-slate-500">{cand.role}</div>
                          </div>
                          {cand.id === dossier.candidate_id && (
                            <span className="w-2 h-2 rounded-full bg-brand-400 shadow-glow-sm" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <p className="text-xs text-slate-500 font-mono">
              Candidate ID: {dossier.candidate_id.slice(0, 18)}... • Evaluated: {new Date(dossier.generated_at).toLocaleDateString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 relative self-end md:self-center">
          {/* Export Brief Dropdown */}
          <div className="relative" ref={exportMenuRef}>
            <GlassButton
              variant="primary"
              size="sm"
              onClick={() => setIsExportMenuOpen(!isExportMenuOpen)}
              loading={isExporting}
              icon={<ChevronDown className="w-3 h-3 opacity-80" />}
              iconPosition="right"
            >
              <Download className="w-3.5 h-3.5 mr-2" />
              {isExporting ? 'Exporting...' : 'Export Brief'}
            </GlassButton>

            {isExportMenuOpen && (
              <div className="absolute right-0 mt-2 w-52 glass-strong border border-white/[0.12] rounded-xl shadow-2xl py-1.5 z-50 text-xs text-slate-200 backdrop-blur-2xl">
                <button
                  type="button"
                  onClick={() => {
                    setIsExportMenuOpen(false);
                    window.print();
                  }}
                  className="w-full px-3 py-2 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors"
                >
                  <Printer className="w-3.5 h-3.5 text-brand-400" />
                  <span>Print / Save as PDF</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload('html')}
                  className="w-full px-3 py-2 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors border-t border-white/[0.06]"
                >
                  <FileText className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Download HTML Brief</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload('markdown')}
                  className="w-full px-3 py-2 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors"
                >
                  <FileText className="w-3.5 h-3.5 text-sky-400" />
                  <span>Download Markdown</span>
                </button>
              </div>
            )}
          </div>

          <GlassButton
            variant="secondary"
            size="sm"
            onClick={onOpenWeightsModal}
          >
            <Sliders className="w-3.5 h-3.5 text-brand-400 mr-2" />
            Role Weights
          </GlassButton>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-1">
        {/* RCI Score Card */}
        <GlassCard variant="subtle" glow={getRciGlow(dossier.rci)} className="flex items-center justify-between p-4">
          <div>
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
              Technical Readiness (RCI)
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-black text-brand-400 font-mono">
                {dossier.rci !== null ? (
                  <AnimatedCounter value={dossier.rci} decimals={1} />
                ) : (
                  'UNKNOWN'
                )}
              </span>
              <span className="text-xs text-slate-500 font-mono">/ 100</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Weighted composite of verified code capabilities</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-brand-500/15 text-brand-400 flex items-center justify-center shrink-0">
            <Award className="w-5 h-5" />
          </div>
        </GlassCard>

        {/* Evidence Coverage Card */}
        <GlassCard variant="subtle" glow={isLowCoverage ? 'amber' : 'emerald'} className="flex items-center justify-between p-4">
          <div>
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
              Verified Code Coverage
            </span>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-black ${isLowCoverage ? 'text-amber-400' : 'text-emerald-400'} font-mono`}>
                <AnimatedCounter value={coveragePercent} suffix="%" />
              </span>
              <span className="text-xs text-slate-500 font-mono">of role requirements</span>
            </div>
            <div className="w-36 bg-white/[0.06] h-1.5 rounded-full overflow-hidden mt-2">
              <div
                className={`h-full rounded-full transition-all duration-1000 ${
                  isLowCoverage
                    ? 'bg-gradient-to-r from-amber-500 to-amber-400'
                    : 'bg-gradient-to-r from-emerald-500 to-teal-400'
                }`}
                style={{ width: `${Math.min(100, coveragePercent)}%` }}
              />
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center shrink-0">
            <Gauge className="w-5 h-5" />
          </div>
        </GlassCard>

        {/* Decision Support Card */}
        <GlassCard variant="subtle" className="flex items-center justify-between p-4">
          <div>
            <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block mb-1">
              Decision Boundary
            </span>
            <div className="flex items-center gap-1.5 text-slate-200 text-sm font-semibold">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Interviewer Support Only</span>
            </div>
            <p className="text-[10px] text-slate-400 mt-1 leading-normal">
              Zero autonomous hire/reject calls. AI generates grounded evidence for humans.
            </p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-white/[0.04] text-slate-400 flex items-center justify-center shrink-0">
            <CheckCircle className="w-5 h-5" />
          </div>
        </GlassCard>
      </div>
    </GlassCard>
  );
};
