'use client';

import React, { useState } from 'react';
import {
  AlertCircle,
  Award,
  CheckCircle,
  Gauge,
  Sliders,
  ShieldCheck,
  User,
  Printer,
  Download,
  FileText,
  ChevronDown,
  Users,
  Sparkles,
} from 'lucide-react';
import { Dossier } from '../../types/cci';
import { downloadDossier } from '../../lib/api';

const CANONICAL_CANDIDATE_LIST = [
  { id: '11111111-1111-1111-1111-111111111111', name: 'Alice Chen', role: 'Backend (Senior)' },
  { id: '22222222-2222-2222-2222-222222222222', name: 'Elena Rostova', role: 'Frontend (Staff)' },
  { id: '33333333-3333-3333-3333-333333333333', name: 'Dr. Marcus Thorne', role: 'ML Engineer (Senior)' },
  { id: '44444444-4444-4444-4444-444444444444', name: 'Tariq Mansour', role: 'DevOps / SRE (Staff)' },
  { id: '55555555-5555-5555-5555-555555555555', name: "Samuel O'Connor", role: 'Fullstack (Principal)' },
  { id: '66666666-6666-6666-6666-666666666666', name: 'Jordan Blake', role: 'Backend (Junior)' },
  { id: '77777777-7777-7777-7777-777777777777', name: 'Devin Vance', role: 'Backend (Discrepancy Demo)' },
];

export const DossierHeader: React.FC<{
  dossier: Dossier;
  candidateName?: string;
  onOpenWeightsModal?: () => void;
  onSelectCandidate?: (candidateId: string, name: string) => void;
}> = ({ dossier, candidateName = 'Alice Developer', onOpenWeightsModal, onSelectCandidate }) => {
  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);
  const [isCandidateMenuOpen, setIsCandidateMenuOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const coveragePercent = Math.round(dossier.coverage * 100);
  const isLowCoverage = dossier.coverage < 0.30 || dossier.is_insufficient_evidence;

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

  // Human-friendly readiness tier
  const rci = dossier.rci;
  let readinessTier = { label: 'Inconclusive / Sparse', color: 'text-amber-400 bg-amber-500/10 border-amber-500/30' };
  if (rci !== null) {
    if (rci >= 88) {
      readinessTier = { label: 'Exceptional (88+)', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' };
    } else if (rci >= 75) {
      readinessTier = { label: 'Strong (75-87)', color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/30' };
    } else if (rci >= 60) {
      readinessTier = { label: 'Developing (60-74)', color: 'text-sky-400 bg-sky-500/10 border-sky-500/30' };
    }
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
      {/* Low Coverage Warning Banner */}
      {isLowCoverage && (
        <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-center gap-2.5 text-xs text-amber-300">
          <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
          <div>
            <span className="font-semibold">Sparse Public Code Footprint ({coveragePercent}%):</span> Most role skills were not observed in public GitHub repos. Missing skills are marked UNKNOWN, never failed. Focus the technical interview on unobserved skills.
          </div>
        </div>
      )}

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h1 className="text-2xl font-bold text-white tracking-tight">{candidateName}</h1>

            <span className="px-2.5 py-0.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 rounded-full text-xs font-semibold uppercase tracking-wider">
              {dossier.role.replace('_', ' ')}
            </span>

            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${readinessTier.color}`}>
              {readinessTier.label}
            </span>

            {/* Quick Candidate Switcher Dropdown */}
            {onSelectCandidate && (
              <div className="relative inline-block ml-1">
                <button
                  type="button"
                  onClick={() => setIsCandidateMenuOpen(!isCandidateMenuOpen)}
                  className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-md text-xs font-medium flex items-center gap-1 transition-colors"
                >
                  <Users className="w-3 h-3 text-indigo-400" />
                  <span>Switch Candidate</span>
                  <ChevronDown className="w-3 h-3 opacity-60" />
                </button>

                {isCandidateMenuOpen && (
                  <div className="absolute left-0 mt-1 w-64 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1 z-50 text-xs">
                    <div className="px-3 py-1 text-[10px] uppercase font-mono text-slate-500 border-b border-slate-800">
                      Switch Candidate Dossier
                    </div>
                    {CANONICAL_CANDIDATE_LIST.map((cand) => (
                      <button
                        key={cand.id}
                        type="button"
                        onClick={() => {
                          setIsCandidateMenuOpen(false);
                          onSelectCandidate(cand.id, cand.name);
                        }}
                        className={`w-full px-3 py-2 text-left hover:bg-slate-800 flex items-center justify-between transition-colors ${
                          cand.id === dossier.candidate_id ? 'bg-indigo-600/20 text-indigo-300 font-semibold' : 'text-slate-300'
                        }`}
                      >
                        <div>
                          <div>{cand.name}</div>
                          <div className="text-[10px] text-slate-500">{cand.role}</div>
                        </div>
                        {cand.id === dossier.candidate_id && (
                          <span className="w-2 h-2 rounded-full bg-indigo-400" />
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          <p className="text-xs text-slate-400 font-mono">
            Candidate ID: {dossier.candidate_id} • Evaluated: {new Date(dossier.generated_at).toLocaleDateString()}
          </p>
        </div>

        <div className="flex items-center gap-2.5 relative">
          {/* Export Brief Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsExportMenuOpen(!isExportMenuOpen)}
              disabled={isExporting}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 shadow-sm shadow-indigo-600/30"
            >
              <Download className="w-3.5 h-3.5" />
              <span>{isExporting ? 'Exporting...' : 'Export Brief'}</span>
              <ChevronDown className="w-3 h-3 ml-0.5 opacity-80" />
            </button>

            {isExportMenuOpen && (
              <div className="absolute right-0 mt-2 w-48 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl py-1 z-50 text-xs text-slate-200">
                <button
                  type="button"
                  onClick={() => {
                    setIsExportMenuOpen(false);
                    window.print();
                  }}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800 flex items-center gap-2 transition-colors"
                >
                  <Printer className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Print / Save as PDF</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload('html')}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800 flex items-center gap-2 transition-colors border-t border-slate-800"
                >
                  <FileText className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Download HTML Brief</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleDownload('markdown')}
                  className="w-full px-3 py-2 text-left hover:bg-slate-800 flex items-center gap-2 transition-colors"
                >
                  <FileText className="w-3.5 h-3.5 text-sky-400" />
                  <span>Download Markdown</span>
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={onOpenWeightsModal}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 border border-slate-700"
          >
            <Sliders className="w-3.5 h-3.5 text-indigo-400" />
            <span>Role Weights Override</span>
          </button>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
        {/* RCI Score Card */}
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-1">
              Technical Readiness Score (RCI)
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-3xl font-black text-indigo-400">
                {dossier.rci !== null ? dossier.rci.toFixed(1) : 'UNKNOWN'}
              </span>
              <span className="text-xs text-slate-500 font-mono">/ 100</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1">Weighted composite of verified code capabilities</p>
          </div>
          <div className="p-3 bg-indigo-500/10 text-indigo-400 rounded-xl">
            <Award className="w-6 h-6" />
          </div>
        </div>

        {/* Evidence Coverage Card */}
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-1">
              Verified Code Coverage
            </span>
            <div className="flex items-baseline gap-2">
              <span className={`text-3xl font-black ${isLowCoverage ? 'text-amber-400' : 'text-emerald-400'}`}>
                {coveragePercent}%
              </span>
              <span className="text-xs text-slate-500 font-mono">of role requirements</span>
            </div>
            <div className="w-32 bg-slate-800 h-1.5 rounded-full overflow-hidden mt-2">
              <div
                className={`h-full ${isLowCoverage ? 'bg-amber-400' : 'bg-emerald-400'}`}
                style={{ width: `${Math.min(100, coveragePercent)}%` }}
              />
            </div>
          </div>
          <div className="p-3 bg-emerald-500/10 text-emerald-400 rounded-xl">
            <Gauge className="w-6 h-6" />
          </div>
        </div>

        {/* Invariant Decision Support Card */}
        <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider block mb-1">
              Decision Boundary
            </span>
            <div className="flex items-center gap-1.5 text-slate-200 text-sm font-semibold">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Interviewer Support Only</span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 leading-normal">
              Zero autonomous hire/reject calls. AI generates grounded evidence for humans.
            </p>
          </div>
          <div className="p-3 bg-slate-800/80 text-slate-400 rounded-xl">
            <CheckCircle className="w-6 h-6" />
          </div>
        </div>
      </div>
    </div>
  );
};
