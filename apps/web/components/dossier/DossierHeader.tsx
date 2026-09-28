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
  FileCode,
  Table,
  Archive,
  ChevronDown,
  Users,
} from 'lucide-react';
import { Dossier } from '../../types/cci';
import { TEAM_MEMBERS } from '../../lib/team-members';
import { downloadDossier, ExportFormat, ExportScope } from '../../lib/api';
import { GlassCard } from '../ui/GlassCard';
import { GlowBadge } from '../ui/GlowBadge';
import { RadialGauge } from '../ui/RadialGauge';
import { AnimatedCounter } from '../ui/AnimatedCounter';
import { GlassButton } from '../ui/GlassButton';
import { PhotoLightboxModal } from '../ui/PhotoLightboxModal';

const CANONICAL_CANDIDATE_LIST = TEAM_MEMBERS.map((member) => ({
  id: member.id, name: member.name, role: member.role_label,
}));

export const DossierHeader: React.FC<{
  dossier: Dossier;
  candidateName?: string;
  candidatePicture?: string | null;
  onOpenWeightsModal?: () => void;
  onSelectCandidate?: (candidateId: string, name: string) => void;
}> = ({ dossier, candidateName = 'Ayush Roy', candidatePicture, onOpenWeightsModal, onSelectCandidate }) => {
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const [isCandidateMenuOpen, setIsCandidateMenuOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isPhotoModalOpen, setIsPhotoModalOpen] = useState(false);
  const coveragePercent = Math.round(dossier.coverage * 100);
  const isLowCoverage = dossier.coverage < 0.30 || dossier.is_insufficient_evidence;
  const picture = candidatePicture || (dossier as any).picture || (dossier as any).manifest?.picture;

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

  const handleDownload = async (
    format: ExportFormat,
    scope: ExportScope = 'report'
  ) => {
    try {
      setIsExporting(true);
      setIsExportMenuOpen(false);
      await downloadDossier(dossier.candidate_id, format, candidateName, scope);
    } catch (err) {
      console.warn('Direct API export failed, falling back to client-side fallback:', err);
      if (format === 'html' && scope === 'report') {
        window.print();
      } else {
        const cleanName = candidateName.toLowerCase().replace(/[^a-z0-9]/g, '_');
        const scopeSuffix =
          scope === 'audit' ? 'full_audit' : scope === 'full' ? 'report_and_full_audit' : 'technical_report';
        let content = '';
        let mimeType = 'text/plain';
        const ext = format === 'markdown' ? 'md' : format;

        if (format === 'json') {
          content = JSON.stringify(
            scope === 'full'
              ? { candidate_id: dossier.candidate_id, report: dossier, full_audit: { run_id: dossier.analysis_run_id, evidence: (dossier as any).evidence_records } }
              : dossier,
            null,
            2
          );
          mimeType = 'application/json';
        } else if (format === 'csv') {
          content = 'Evidence ID,Target Capability,Polarity,Confidence\n' +
            (((dossier as any).evidence_records || []) as any[]).map((e: any) => `"${e.evidence_id}","${e.target_capability}","${e.is_positive_support ? 'POSITIVE' : 'NEGATIVE'}","${e.confidence}"`).join('\n');
          mimeType = 'text/csv';
        } else {
          content = `# ${candidateName} — ${scope === 'audit' ? 'Full Audit' : 'Technical Report'}\n\nRole: ${dossier.role}\nRCI: ${dossier.rci ?? 'UNKNOWN'}\nCoverage: ${Math.round(dossier.coverage * 100)}%\n\nEvidence Records: ${(dossier as any).evidence_records?.length || 0}`;
        }

        const blob = new Blob([content], { type: mimeType });
        const link = document.createElement('a');
        link.href = window.URL.createObjectURL(blob);
        link.download = `${cleanName}_${scopeSuffix}.${ext}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(link.href);
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
          {picture && (
            <>
              <button
                type="button"
                onClick={() => setIsPhotoModalOpen(true)}
                className="p-0 border-0 bg-transparent rounded-2xl cursor-pointer hover:scale-105 transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400 shrink-0"
                title="Click to view full photo (large view, unrestricted)"
                aria-label={`View full photo of ${candidateName}`}
              >
                <img
                  src={picture}
                  alt={candidateName}
                  className="w-14 h-14 rounded-2xl object-cover border border-purple-500/40 shadow-glow-sm"
                  data-testid="dossier-header-picture"
                />
              </button>
              <PhotoLightboxModal
                isOpen={isPhotoModalOpen}
                onClose={() => setIsPhotoModalOpen(false)}
                src={picture}
                name={candidateName}
                subtitle="Candidate Profile Photo"
              />
            </>
          )}
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
          {/* Export Report and Audit Dropdown */}
          <div className="relative" ref={exportMenuRef}>
            <GlassButton
              variant="primary"
              size="sm"
              onClick={() => setIsExportMenuOpen(!isExportMenuOpen)}
              loading={isExporting}
              icon={<ChevronDown className="w-3 h-3 opacity-80" />}
              iconPosition="right"
              aria-label="Export report and audit options"
            >
              <Download className="w-3.5 h-3.5 mr-2" />
              {isExporting ? 'Exporting...' : 'Export Report & Audit'}
            </GlassButton>

            {isExportMenuOpen && (
              <div className="absolute right-0 mt-2 w-64 glass-strong border border-white/[0.12] rounded-xl shadow-2xl py-2 z-50 text-xs text-slate-200 backdrop-blur-2xl divide-y divide-white/[0.06] max-h-[85vh] overflow-y-auto">
                {/* 1. Report Options */}
                <div className="py-1">
                  <div className="px-3 py-1 text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider flex items-center justify-between">
                    <span>Technical Report</span>
                    <span className="text-[9px] text-brand-400">Brief</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setIsExportMenuOpen(false);
                      window.print();
                    }}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <Printer className="w-3.5 h-3.5 text-brand-400 shrink-0" />
                    <span>Print / Save as PDF</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('html', 'report')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <FileText className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Download HTML Report</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('markdown', 'report')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <FileText className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                    <span>Download Markdown Report</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('json', 'report')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <FileCode className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>Download JSON Report</span>
                  </button>
                </div>

                {/* 2. Full Audit Options */}
                <div className="py-1">
                  <div className="px-3 py-1 text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider flex items-center justify-between">
                    <span>Full Audit Log</span>
                    <span className="text-[9px] text-emerald-400">Governance</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDownload('html', 'audit')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Download Full Audit (HTML)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('markdown', 'audit')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                    <span>Download Full Audit (Markdown)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('json', 'audit')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <FileCode className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                    <span>Download Full Audit (JSON)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('csv', 'audit')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <Table className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                    <span>Download Audit Trail (CSV)</span>
                  </button>
                </div>

                {/* 3. Combined Package */}
                <div className="py-1">
                  <div className="px-3 py-1 text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider flex items-center justify-between">
                    <span>Complete Package</span>
                    <span className="text-[9px] text-purple-400">Report + Audit</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDownload('html', 'full')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <Archive className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    <span>Export Package (HTML)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('markdown', 'full')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <FileText className="w-3.5 h-3.5 text-pink-400 shrink-0" />
                    <span>Export Package (Markdown)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDownload('json', 'full')}
                    className="w-full px-3 py-1.5 text-left hover:bg-white/[0.06] flex items-center gap-2 transition-colors text-slate-200 hover:text-white"
                  >
                    <FileCode className="w-3.5 h-3.5 text-amber-300 shrink-0" />
                    <span>Export Package (JSON)</span>
                  </button>
                </div>
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
              JD Fit Score (RCI)
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
