'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  ArrowLeft,
  CheckCircle2,
  Play,
} from 'lucide-react';
import { CanonicalRole, CandidateManifest, NormalizedRequirement } from '../types/cci';
import { JobIntakeForm } from './JobIntakeForm';
import { CandidateIntakeForm } from './CandidateIntakeForm';
import { PipelineTracker } from './PipelineTracker';
import { GlassCard } from './ui/GlassCard';
import { GlowBadge } from './ui/GlowBadge';

interface QuickDemoProfile {
  id: string;
  name: string;
  role: CanonicalRole;
  label: string;
  badge: string;
  variant: 'success' | 'brand' | 'danger';
  manifest: CandidateManifest;
}

const QUICK_DEMO_PROFILES: QuickDemoProfile[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    name: 'Alice Chen',
    role: 'backend',
    label: 'Senior Distributed Backend',
    badge: 'High Coverage (RCI 90.0)',
    variant: 'success',
    manifest: {
      candidate_id: '11111111-1111-1111-1111-111111111111',
      full_name: 'Alice Chen',
      primary_email: 'alice.chen@example.com',
      github_usernames: ['alicechen-dev'],
      github_repositories: [
        'https://github.com/alicechen-dev/distributed-payment-engine',
        'https://github.com/alicechen-dev/pg-partition-manager',
      ],
      deployment_urls: ['https://alicechen.dev'],
      portfolio_urls: [],
      declared_skills: ['Python', 'Go', 'PostgreSQL', 'Kafka', 'Docker', 'Distributed Systems'],
      extraction_metadata: {},
    },
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Elena Rostova',
    role: 'frontend',
    label: 'Staff Frontend Platform',
    badge: 'Design Systems (RCI 86.0)',
    variant: 'brand',
    manifest: {
      candidate_id: '22222222-2222-2222-2222-222222222222',
      full_name: 'Elena Rostova',
      primary_email: 'elena.rostova@example.com',
      github_usernames: ['erostova-web'],
      github_repositories: [
        'https://github.com/erostova-web/a11y-kit-react',
        'https://github.com/erostova-web/next-vitals-booster',
      ],
      deployment_urls: ['https://erostova.design'],
      portfolio_urls: [],
      declared_skills: ['TypeScript', 'React', 'Next.js', 'Web Vitals', 'WAI-ARIA', 'Tailwind CSS'],
      extraction_metadata: {},
    },
  },
  {
    id: '77777777-7777-7777-7777-777777777777',
    name: 'Devin Vance',
    role: 'backend',
    label: 'Backend Conflict Demo',
    badge: 'Contradiction Alert (D_k < 0)',
    variant: 'danger',
    manifest: {
      candidate_id: '77777777-7777-7777-7777-777777777777',
      full_name: 'Devin Vance',
      primary_email: 'devin.vance@example.com',
      github_usernames: ['dvance-eng'],
      github_repositories: [
        'https://github.com/dvance-eng/toy-distributed-counter',
        'https://github.com/dvance-eng/quick-rest-starter',
      ],
      deployment_urls: ['https://devinvance.dev'],
      portfolio_urls: [],
      declared_skills: ['Distributed Systems', 'Kafka', 'Consensus Algorithms', 'Raft'],
      extraction_metadata: {},
    },
  },
];

export const EvaluationWizard: React.FC<{
  currentRole: CanonicalRole;
  pipelineStageIndex: number;
  isPipelineRunning: boolean;
  isPipelineComplete: boolean;
  onJobComplete: (role: CanonicalRole, jdText: string, reqs: NormalizedRequirement[]) => void;
  onCandidateSubmit: (manifest: CandidateManifest) => void;
  onViewDossier: () => void;
}> = ({
  currentRole,
  pipelineStageIndex,
  isPipelineRunning,
  isPipelineComplete,
  onJobComplete,
  onCandidateSubmit,
  onViewDossier,
}) => {
  const [step, setStep] = useState<1 | 2 | 3>(isPipelineRunning ? 3 : 1);

  React.useEffect(() => {
    if (isPipelineRunning) {
      setStep(3);
    }
  }, [isPipelineRunning]);

  const handleQuickDemoClick = (profile: QuickDemoProfile) => {
    onJobComplete(profile.role, '', []);
    onCandidateSubmit(profile.manifest);
    setStep(3);
  };

  const handleJobFormComplete = (role: CanonicalRole, jdText: string, reqs: NormalizedRequirement[]) => {
    onJobComplete(role, jdText, reqs);
    setStep(2);
  };

  const handleCandidateFormSubmit = (manifest: CandidateManifest) => {
    onCandidateSubmit(manifest);
    setStep(3);
  };

  return (
    <div className="space-y-5">
      {/* 1-Click Quick Demo Presets */}
      <GlassCard variant="strong" glow="indigo" className="p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-brand-500/15 text-brand-400 flex items-center justify-center shrink-0">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-bold text-white">1-Click Demonstration Presets</span>
              <span className="text-[11px] text-slate-400 ml-2 hidden md:inline">
                Evaluate pre-configured candidate profiles instantly:
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {QUICK_DEMO_PROFILES.map((profile) => (
              <button
                key={profile.id}
                type="button"
                onClick={() => handleQuickDemoClick(profile)}
                className="px-3 py-1.5 glass hover:bg-white/[0.08] rounded-xl text-xs font-medium text-slate-200 transition-all flex items-center gap-2 group"
              >
                <Play className="w-3 h-3 text-brand-400 group-hover:scale-110 transition-transform" />
                <span className="font-semibold">{profile.name}</span>
                <GlowBadge variant={profile.variant} size="sm">
                  {profile.badge}
                </GlowBadge>
              </button>
            ))}
          </div>
        </div>
      </GlassCard>

      {/* Visual Stepper */}
      <GlassCard variant="subtle" className="p-3">
        <div className="grid grid-cols-3 gap-2 text-xs">
          {/* Step 1 */}
          <button
            type="button"
            onClick={() => setStep(1)}
            className={`p-3 rounded-xl border transition-all text-left flex items-center gap-3 ${
              step === 1
                ? 'glass-strong border-brand-500/50 shadow-glow-sm'
                : 'glass-subtle border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
              step > 1 ? 'bg-emerald-500/20 text-emerald-400' : step === 1 ? 'bg-brand-500 text-white shadow-glow-sm' : 'bg-white/[0.04] text-slate-500'
            }`}>
              {step > 1 ? <CheckCircle2 className="w-4 h-4" /> : '1'}
            </div>
            <div className="min-w-0">
              <div className={`font-semibold truncate ${step === 1 ? 'text-white' : 'text-slate-400'}`}>
                Role &amp; Job Spec
              </div>
              <div className="text-[10px] text-slate-500 truncate">Define target capabilities</div>
            </div>
          </button>

          {/* Step 2 */}
          <button
            type="button"
            onClick={() => setStep(2)}
            className={`p-3 rounded-xl border transition-all text-left flex items-center gap-3 ${
              step === 2
                ? 'glass-strong border-brand-500/50 shadow-glow-sm'
                : 'glass-subtle border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
              step > 2 ? 'bg-emerald-500/20 text-emerald-400' : step === 2 ? 'bg-brand-500 text-white shadow-glow-sm' : 'bg-white/[0.04] text-slate-500'
            }`}>
              {step > 2 ? <CheckCircle2 className="w-4 h-4" /> : '2'}
            </div>
            <div className="min-w-0">
              <div className={`font-semibold truncate ${step === 2 ? 'text-white' : 'text-slate-400'}`}>
                Candidate Artifacts
              </div>
              <div className="text-[10px] text-slate-500 truncate">GitHub &amp; resume links</div>
            </div>
          </button>

          {/* Step 3 */}
          <button
            type="button"
            onClick={() => setStep(3)}
            className={`p-3 rounded-xl border transition-all text-left flex items-center gap-3 ${
              step === 3
                ? 'glass-strong border-brand-500/50 shadow-glow-sm'
                : 'glass-subtle border-transparent text-slate-500 hover:text-slate-300'
            }`}
          >
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center font-bold text-xs shrink-0 ${
              isPipelineComplete && step === 3
                ? 'bg-emerald-500/20 text-emerald-400'
                : step === 3
                ? 'bg-brand-500 text-white shadow-glow-sm'
                : 'bg-white/[0.04] text-slate-500'
            }`}>
              {isPipelineComplete && step === 3 ? <CheckCircle2 className="w-4 h-4" /> : '3'}
            </div>
            <div className="min-w-0">
              <div className={`font-semibold truncate ${step === 3 ? 'text-white' : 'text-slate-400'}`}>
                Intelligence Engine
              </div>
              <div className="text-[10px] text-slate-500 truncate">10-stage AST &amp; math</div>
            </div>
          </button>
        </div>
      </GlassCard>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {step === 1 && (
            <div className="space-y-4">
              <JobIntakeForm onComplete={handleJobFormComplete} />
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Step 1: Role &amp; Job Spec</span>
                </button>
              </div>
              <CandidateIntakeForm onSubmit={handleCandidateFormSubmit} />
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="text-xs text-slate-400 hover:text-white flex items-center gap-1.5 transition-colors"
                >
                  <ArrowLeft className="w-3.5 h-3.5" />
                  <span>Back to Step 2: Candidate Materials</span>
                </button>
              </div>
              <PipelineTracker
                currentStageIndex={pipelineStageIndex}
                isComplete={isPipelineComplete}
                onViewDossier={onViewDossier}
              />
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};
