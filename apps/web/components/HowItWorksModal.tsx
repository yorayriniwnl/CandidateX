'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldCheck,
  Cpu,
  AlertTriangle,
  ArrowRight,
  BookOpen,
  FileCode2,
  CheckCircle2,
  Award,
} from 'lucide-react';
import { GlassModal } from '@/components/ui/GlassModal';
import { TabSlider } from '@/components/ui/TabSlider';
import { GlassCard } from '@/components/ui/GlassCard';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { GlassButton } from '@/components/ui/GlassButton';

export const HowItWorksModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
}> = ({ isOpen, onClose }) => {
  const [activeTab, setActiveTab] = useState('principles');

  const tabs = [
    { key: 'principles', label: '1. Core Principles & Safety' },
    { key: 'lifecycle', label: '2. The Evaluation Journey' },
    { key: 'glossary', label: '3. Metric Glossary' },
  ];

  return (
    <GlassModal
      isOpen={isOpen}
      onClose={onClose}
      title="How Candidate Capability Intelligence Works"
      subtitle="A guide to evidence-backed technical candidate evaluation"
      size="lg"
    >
      <div className="flex flex-col gap-6">
        <TabSlider
          tabs={tabs}
          activeKey={activeTab}
          onChange={setActiveTab}
          size="sm"
        />

        <div className="min-h-[350px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.2 }}
              className="text-sm text-slate-300"
            >
              {activeTab === 'principles' && (
                <div className="space-y-4">
                  <GlassCard variant="subtle" className="p-4 bg-indigo-500/5 border-indigo-500/20">
                    <h3 className="text-sm font-semibold text-indigo-300 mb-2">
                      Why not just use an AI resume scanner?
                    </h3>
                    <p className="text-slate-300 leading-relaxed text-sm">
                      Traditional keyword scanners and black-box LLMs hallucinate, reward buzzword stuffing, and fail to verify whether a candidate actually wrote or understood the code they claim. CCI replaces subjective guessing with <strong>deterministic static code analysis</strong> and <strong>verifiable mathematical confidence</strong>.
                    </p>
                  </GlassCard>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>
                      <GlassCard variant="subtle" className="p-4 h-full space-y-3">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
                          <Cpu className="w-4 h-4" />
                        </div>
                        <h4 className="font-semibold text-slate-100 text-sm">1. Zero Code Execution</h4>
                        <p className="text-slate-400 leading-relaxed text-xs">
                          Untrusted candidate code is <strong>never executed</strong> in any runtime or shell. We inspect Abstract Syntax Trees (AST), git histories, and dependency manifests deterministically without security risks.
                        </p>
                      </GlassCard>
                    </motion.div>

                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}>
                      <GlassCard variant="subtle" className="p-4 h-full space-y-3">
                        <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
                          <AlertTriangle className="w-4 h-4" />
                        </div>
                        <h4 className="font-semibold text-slate-100 text-sm">2. Missing Evidence != Zero</h4>
                        <p className="text-slate-400 leading-relaxed text-xs">
                          Many great engineers write proprietary code at work and have empty GitHubs. We never assign a score of 0.0 for missing skills. Instead, they are marked <strong>UNKNOWN</strong> with targeted interview questions to verify in person.
                        </p>
                      </GlassCard>
                    </motion.div>

                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
                      <GlassCard variant="subtle" className="p-4 h-full space-y-3">
                        <div className="w-8 h-8 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400">
                          <ShieldCheck className="w-4 h-4" />
                        </div>
                        <h4 className="font-semibold text-slate-100 text-sm">3. Human Decision Support</h4>
                        <p className="text-slate-400 leading-relaxed text-xs">
                          CCI <strong>never makes autonomous hiring or rejection decisions</strong>. It prepares evidence-backed technical briefing packets and prioritized probe questions so human engineering panels can conduct high-signal interviews.
                        </p>
                      </GlassCard>
                    </motion.div>
                  </div>
                </div>
              )}

              {activeTab === 'lifecycle' && (
                <div className="space-y-4">
                  <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }}>
                    <GlassCard variant="subtle" className="p-4 flex items-start gap-4">
                      <div className="w-8 h-8 rounded-full bg-indigo-500/20 flex items-center justify-center font-bold text-indigo-400 shrink-0">
                        1
                      </div>
                      <div>
                        <h4 className="font-semibold text-slate-100">Job Spec & Candidate Material Ingestion</h4>
                        <p className="text-slate-400 text-sm mt-1 leading-relaxed">
                          You select a target role (e.g., Backend, Frontend, ML) and provide the candidate’s CV, GitHub repositories, or live portfolio. The system extracts closed-world identity links and normalizes job requirements into 12 core technical capability dimensions.
                        </p>
                      </div>
                    </GlassCard>
                  </motion.div>

                  <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }}>
                    <GlassCard variant="subtle" className="p-4 flex items-start gap-4">
                      <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center font-bold text-emerald-400 shrink-0">
                        2
                      </div>
                      <div>
                        <h4 className="font-semibold text-slate-100">Safe AST Analysis & Attribution-Gated Evidence Weights</h4>
                        <p className="text-slate-400 text-sm mt-1 leading-relaxed">
                          Static parsers extract code metrics. A path-specific account contribution ratio gates the geometric mean of artifact integrity, recency, verification, technical depth, and source reliability. This weight does not verify human identity or line-level authorship.
                        </p>
                      </div>
                    </GlassCard>
                  </motion.div>

                  <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }}>
                    <GlassCard variant="subtle" className="p-4 flex items-start gap-4">
                      <div className="w-8 h-8 rounded-full bg-amber-500/20 flex items-center justify-center font-bold text-amber-400 shrink-0">
                        3
                      </div>
                      <div>
                        <h4 className="font-semibold text-slate-100">Technical Readiness Score & Grounded Interview Guide</h4>
                        <p className="text-slate-400 text-sm mt-1 leading-relaxed">
                          The platform calculates the Role Capability Index (RCI) strictly over observed evidence, flags any discrepancies between resume claims and repository artifacts ($D_k$), and compiles a prioritized technical interview question guide with expected answers and rating rubrics.
                        </p>
                      </div>
                    </GlassCard>
                  </motion.div>
                </div>
              )}

              {activeTab === 'glossary' && (
                <div className="space-y-4">
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                    <GlassCard variant="subtle" className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Award className="w-4 h-4 text-indigo-400" />
                        <GlowBadge variant="brand" size="sm">Role Capability Index (RCI)</GlowBadge>
                        <span className="text-sm font-semibold text-slate-200">Technical Readiness Score</span>
                      </div>
                      <p className="text-slate-400 text-sm leading-relaxed">
                        A 0–100 composite score measuring demonstrated technical competence weighted specifically for the target role. Calculated strictly over verified evidence (unobserved capabilities never drag the score down to zero).
                      </p>
                    </GlassCard>
                  </motion.div>

                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                    <GlassCard variant="subtle" className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        <GlowBadge variant="success" size="sm">Evidence Coverage %</GlowBadge>
                        <span className="text-sm font-semibold text-slate-200">Observation Breadth</span>
                      </div>
                      <p className="text-slate-400 text-sm leading-relaxed">
                        The proportion of role requirements that have verifiable repository or work artifact evidence. A coverage of 25% means 3 out of 12 skills have public code proof; the remaining 9 are flagged for in-person interview verification.
                      </p>
                    </GlassCard>
                  </motion.div>

                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                    <GlassCard variant="subtle" className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <AlertTriangle className="w-4 h-4 text-rose-400" />
                        <GlowBadge variant="danger" size="sm">Contradiction Diagnostic ($D_k$)</GlowBadge>
                        <span className="text-sm font-semibold text-slate-200">Discrepancy Alert</span>
                      </div>
                      <p className="text-slate-400 text-sm leading-relaxed">
                        Measures alignment between self-declared resume claims and static code artifacts ($D_k \in [-1, +1]$). When a candidate claims senior distributed systems expertise but their repository only contains basic starter scripts, a discrepancy is flagged to give interviewers an exact code-defense question.
                      </p>
                    </GlassCard>
                  </motion.div>

                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                    <GlassCard variant="subtle" className="p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <FileCode2 className="w-4 h-4 text-sky-400" />
                        <GlowBadge variant="info" size="sm">Kish Depth (n_eff)</GlowBadge>
                        <span className="text-sm font-semibold text-slate-200">Evidence Sample Size</span>
                      </div>
                      <p className="text-slate-400 text-sm leading-relaxed">
                        Measures the effective number of independent, non-redundant evidence sources supporting a score. Higher values mean multiple distinct repositories or commits corroborate the skill.
                      </p>
                    </GlassCard>
                  </motion.div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        <div className="flex items-center justify-between mt-2 pt-4 border-t border-slate-800/50">
          <span className="text-xs text-slate-500">
            Powered by 10 Verified Formal Theorems • Pure Functional Rescoring
          </span>
          <GlassButton variant="primary" onClick={onClose}>
            Got It, Let's Explore
          </GlassButton>
        </div>
      </div>
    </GlassModal>
  );
};
