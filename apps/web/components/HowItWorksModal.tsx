'use client';

import React, { useState } from 'react';
import {
  X,
  ShieldCheck,
  Cpu,
  AlertTriangle,
  Layers,
  ArrowRight,
  BookOpen,
  HelpCircle,
  FileCode2,
  CheckCircle2,
  Sparkles,
  Award,
  GitBranch,
  Search,
} from 'lucide-react';

export const HowItWorksModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState<'principles' | 'lifecycle' | 'glossary'>('principles');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">How Candidate Capability Intelligence Works</h2>
              <p className="text-xs text-slate-400">A guide to evidence-backed technical candidate evaluation</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Sub-Navigation Tabs */}
        <div className="flex items-center gap-2 px-5 pt-3 border-b border-slate-800 bg-slate-950/40 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('principles')}
            className={`pb-2.5 px-3 font-medium transition-colors border-b-2 ${
              activeTab === 'principles'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            1. Core Principles &amp; Safety
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('lifecycle')}
            className={`pb-2.5 px-3 font-medium transition-colors border-b-2 ${
              activeTab === 'lifecycle'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            2. The Evaluation Journey
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('glossary')}
            className={`pb-2.5 px-3 font-medium transition-colors border-b-2 ${
              activeTab === 'glossary'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            3. Plain-English Metric Glossary
          </button>
        </div>

        {/* Content Area */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs text-slate-300">
          {/* Tab 1: Principles */}
          {activeTab === 'principles' && (
            <div className="space-y-4">
              <div className="p-4 bg-indigo-500/10 border border-indigo-500/20 rounded-xl">
                <h3 className="text-sm font-semibold text-indigo-300 mb-1">
                  Why not just use an AI resume scanner?
                </h3>
                <p className="text-slate-300 leading-relaxed">
                  Traditional keyword scanners and black-box LLMs hallucinate, reward buzzword stuffing, and fail to verify whether a candidate actually wrote or understood the code they claim. CCI replaces subjective guessing with <strong>deterministic static code analysis</strong> and <strong>verifiable mathematical confidence</strong>.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                    <Cpu className="w-4 h-4" />
                  </div>
                  <h4 className="font-semibold text-slate-100 text-sm">1. Zero Code Execution</h4>
                  <p className="text-slate-400 leading-relaxed text-[11px]">
                    Untrusted candidate code is <strong>never executed</strong> in any runtime or shell. We inspect Abstract Syntax Trees (AST), git histories, and dependency manifests deterministically without security risks.
                  </p>
                </div>

                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <h4 className="font-semibold text-slate-100 text-sm">2. Missing Evidence != Zero</h4>
                  <p className="text-slate-400 leading-relaxed text-[11px]">
                    Many great engineers write proprietary code at work and have empty GitHubs. We never assign a score of 0.0 for missing skills. Instead, they are marked <strong>UNKNOWN</strong> with targeted interview questions to verify in person.
                  </p>
                </div>

                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl space-y-2">
                  <div className="w-8 h-8 rounded-lg bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-sky-400">
                    <ShieldCheck className="w-4 h-4" />
                  </div>
                  <h4 className="font-semibold text-slate-100 text-sm">3. Human Decision Support</h4>
                  <p className="text-slate-400 leading-relaxed text-[11px]">
                    CCI <strong>never makes autonomous hiring or rejection decisions</strong>. It prepares evidence-backed technical briefing packets and prioritized probe questions so human engineering panels can conduct high-signal interviews.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Lifecycle */}
          {activeTab === 'lifecycle' && (
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex items-start gap-3.5">
                  <div className="w-7 h-7 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center font-bold text-indigo-400 shrink-0 mt-0.5">
                    1
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-100 text-sm">Job Spec &amp; Candidate Material Ingestion</h4>
                    <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                      You select a target role (e.g., Backend, Frontend, ML) and provide the candidate’s CV, GitHub repositories, or live portfolio. The system extracts closed-world identity links and normalizes job requirements into 12 core technical capability dimensions.
                    </p>
                  </div>
                </div>

                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex items-start gap-3.5">
                  <div className="w-7 h-7 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center font-bold text-indigo-400 shrink-0 mt-0.5">
                    2
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-100 text-sm">Safe AST Analysis &amp; 6-Factor Confidence Calibration</h4>
                    <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                      Static parsers extract structural code metrics (cyclomatic complexity, test coverage, migration patterns) and calibrate evidence confidence across 6 objective factors: Authority, Ownership (discounting forks), Recency, Verifiability, Complexity, and Source Reliability.
                    </p>
                  </div>
                </div>

                <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl flex items-start gap-3.5">
                  <div className="w-7 h-7 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center font-bold text-indigo-400 shrink-0 mt-0.5">
                    3
                  </div>
                  <div>
                    <h4 className="font-semibold text-slate-100 text-sm">Technical Readiness Score &amp; Grounded Interview Guide</h4>
                    <p className="text-slate-400 text-[11px] mt-1 leading-relaxed">
                      The platform calculates the Role Capability Index (RCI) strictly over observed evidence, flags any discrepancies between resume claims and repository artifacts ($D_k$), and compiles a prioritized technical interview question guide with expected answers and rating rubrics.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: Glossary */}
          {activeTab === 'glossary' && (
            <div className="space-y-3">
              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                <div className="flex items-center gap-2 font-semibold text-indigo-300 text-sm mb-1">
                  <Award className="w-4 h-4" />
                  <span>Role Capability Index (RCI) — Technical Readiness Score</span>
                </div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  A 0–100 composite score measuring demonstrated technical competence weighted specifically for the target role. Calculated strictly over verified evidence (unobserved capabilities never drag the score down to zero).
                </p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                <div className="flex items-center gap-2 font-semibold text-emerald-300 text-sm mb-1">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Evidence Coverage % — Observation Breadth</span>
                </div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  The proportion of role requirements that have verifiable repository or work artifact evidence. A coverage of 25% means 3 out of 12 skills have public code proof; the remaining 9 are flagged for in-person interview verification.
                </p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                <div className="flex items-center gap-2 font-semibold text-rose-300 text-sm mb-1">
                  <AlertTriangle className="w-4 h-4" />
                  <span>Contradiction Diagnostic ($D_k$) — Discrepancy Alert</span>
                </div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Measures alignment between self-declared resume claims and static code artifacts ($D_k \in [-1, +1]$). When a candidate claims senior distributed systems expertise but their repository only contains basic starter scripts, a discrepancy is flagged to give interviewers an exact code-defense question.
                </p>
              </div>

              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl">
                <div className="flex items-center gap-2 font-semibold text-sky-300 text-sm mb-1">
                  <FileCode2 className="w-4 h-4" />
                  <span>Kish Depth (n_eff) — Evidence Sample Size</span>
                </div>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Measures the effective number of independent, non-redundant evidence sources supporting a score. Higher values mean multiple distinct repositories or commits corroborate the skill.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between">
          <span className="text-[11px] text-slate-500">
            Powered by 10 Verified Formal Theorems • Pure Functional Rescoring
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors shadow-sm"
          >
            Got It, Let's Explore
          </button>
        </div>
      </div>
    </div>
  );
};
