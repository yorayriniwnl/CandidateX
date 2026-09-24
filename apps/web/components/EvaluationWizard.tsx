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
import { GlassCard } from '@/components/ui/GlassCard';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { GlassButton } from '@/components/ui/GlassButton';

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
    name: 'Jordan Example (SYNTHETIC DEMONSTRATION DATA)',
    role: 'backend',
    label: 'Senior Distributed Backend',
    badge: 'High Coverage (RCI 90.0)',
    variant: 'success',
    manifest: {
      candidate_id: '11111111-1111-1111-1111-111111111111',
      full_name: 'Jordan Example (SYNTHETIC DEMONSTRATION DATA)',
      primary_email: 'jordan@example.test',
      github_usernames: ['jordan-example-backend'],
      github_repositories: [
        'https://github.com/jordan-example-backend/distributed-payment-engine',
        'https://github.com/jordan-example-backend/pg-partition-manager',
      ],
      deployment_urls: ['https://jordan.example.test'],
      portfolio_urls: [],
      declared_skills: ['Python', 'Go', 'PostgreSQL', 'Kafka', 'Docker', 'Distributed Systems'],
      extraction_metadata: {},
    },
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Alex Rivera (SYNTHETIC DEMONSTRATION DATA)',
    role: 'frontend',
    label: 'Staff Frontend Platform',
    badge: 'Design Systems (RCI 86.0)',
    variant: 'brand',
    manifest: {
      candidate_id: '22222222-2222-2222-2222-222222222222',
      full_name: 'Alex Rivera (SYNTHETIC DEMONSTRATION DATA)',
      primary_email: 'alex@example.test',
      github_usernames: ['alex-rivera-frontend'],
      github_repositories: [
        'https://github.com/alex-rivera-frontend/a11y-kit-react',
        'https://github.com/alex-rivera-frontend/next-vitals-booster',
      ],
      deployment_urls: ['https://alex.example.test'],
      portfolio_urls: [],
      declared_skills: ['TypeScript', 'React', 'Next.js', 'Web Vitals', 'WAI-ARIA', 'Tailwind CSS'],
      extraction_metadata: {},
    },
  },
  {
    id: '77777777-7777-7777-7777-777777777777',
    name: 'Quinn Avery (SYNTHETIC DEMONSTRATION DATA)',
    role: 'backend',
    label: 'Backend Conflict Demo',
    badge: 'Contradiction Alert (D_k < 0)',
    variant: 'danger',
    manifest: {
      candidate_id: '77777777-7777-7777-7777-777777777777',
      full_name: 'Quinn Avery (SYNTHETIC DEMONSTRATION DATA)',
      primary_email: 'quinn@example.test',
      github_usernames: ['quinn-avery-dev'],
      github_repositories: [
        'https://github.com/quinn-avery-dev/toy-distributed-counter',
        'https://github.com/quinn-avery-dev/quick-rest-starter',
      ],
      deployment_urls: ['https://quinn.example.test'],
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
  const [maxStepAllowed, setMaxStepAllowed] = useState<1 | 2 | 3>(isPipelineRunning ? 3 : 1);

  React.useEffect(() => {
    if (isPipelineRunning) {
      setStep(3);
      setMaxStepAllowed(3);
    }
  }, [isPipelineRunning]);

  const handleQuickDemoClick = (profile: QuickDemoProfile) => {
    onJobComplete(profile.role, '', []);
    onCandidateSubmit(profile.manifest);
    setMaxStepAllowed(3);
    setStep(3);
  };

  const handleJobFormComplete = (role: CanonicalRole, jdText: string, reqs: NormalizedRequirement[]) => {
    onJobComplete(role, jdText, reqs);
    setMaxStepAllowed(Math.max(maxStepAllowed, 2) as 2 | 3);
    setStep(2);
  };

  const handleCandidateFormSubmit = (manifest: CandidateManifest) => {
    onCandidateSubmit(manifest);
    setMaxStepAllowed(3);
    setStep(3);
  };

  const handleStepClick = (targetStep: 1 | 2 | 3) => {
    if (targetStep <= maxStepAllowed) {
      setStep(targetStep);
    }
  };

  // Calculate line widths based on current step
  const getLineWidth = () => {
    if (step === 3) return '100%';
    if (step === 2) return '50%';
    return '0%';
  };

  return (
    <div className="space-y-6">
      {/* 1-Click Quick Demo Presets */}
      <GlassCard variant="subtle" glow="indigo" className="p-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 text-brand-400 flex items-center justify-center shrink-0 shadow-[0_0_15px_rgba(99,102,241,0.3)]">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-100">1-Click Demonstration Presets</div>
              <div className="text-xs text-slate-400">
                Evaluate pre-configured candidate profiles instantly
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {QUICK_DEMO_PROFILES.map((profile) => (
              <GlassButton
                key={profile.id}
                variant="secondary"
                size="sm"
                onClick={() => handleQuickDemoClick(profile)}
                icon={<Play className="w-3 h-3 group-hover:scale-110 transition-transform" />}
                className="group !py-1.5"
              >
                <span className="font-semibold text-slate-200">{profile.name}</span>
                <GlowBadge variant={profile.variant} size="sm" className="ml-2">
                  {profile.badge}
                </GlowBadge>
              </GlassButton>
            ))}
          </div>
        </div>
      </GlassCard>

      {/* Visual Stepper */}
      <div className="relative z-10 px-2">
        {/* Connecting Line Background */}
        <div className="absolute left-6 right-6 top-1/2 -translate-y-1/2 h-1 bg-slate-800 rounded-full z-[-1]" />
        
        {/* Connecting Line Foreground */}
        <div 
          className="absolute left-6 top-1/2 -translate-y-1/2 h-1 bg-indigo-500 rounded-full z-[-1] transition-all duration-500 ease-in-out"
          style={{ width: getLineWidth(), maxWidth: 'calc(100% - 3rem)' }}
        />

        <div className="grid grid-cols-3 gap-2">
          {/* Step 1 */}
          <button
            type="button"
            onClick={() => handleStepClick(1)}
            disabled={1 > maxStepAllowed}
            className={`group p-3 rounded-xl transition-all flex flex-col items-center text-center gap-2 ${
              step === 1 ? 'opacity-100' : 'opacity-70 hover:opacity-100'
            } ${1 > maxStepAllowed ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'}`}
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0 transition-all ${
              step > 1 ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.5)]' : 
              step === 1 ? 'bg-indigo-500 text-white shadow-[0_0_15px_rgba(99,102,241,0.5)]' : 
              'bg-slate-800 text-slate-400'
            }`}>
              {step > 1 ? <CheckCircle2 className="w-5 h-5" /> : '1'}
            </div>
            <div className="min-w-0">
              <div className={`text-sm font-semibold truncate ${step === 1 ? 'text-white' : 'text-slate-400'}`}>
                Role & Job Spec
              </div>
            </div>
          </button>

          {/* Step 2 */}
          <button
            type="button"
            onClick={() => handleStepClick(2)}
            disabled={2 > maxStepAllowed}
            className={`group p-3 rounded-xl transition-all flex flex-col items-center text-center gap-2 ${
              step === 2 ? 'opacity-100' : 'opacity-70 hover:opacity-100'
            } ${2 > maxStepAllowed ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'}`}
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0 transition-all ${
              step > 2 ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.5)]' : 
              step === 2 ? 'bg-indigo-500 text-white shadow-[0_0_15px_rgba(99,102,241,0.5)]' : 
              'bg-slate-800 text-slate-400'
            }`}>
              {step > 2 ? <CheckCircle2 className="w-5 h-5" /> : '2'}
            </div>
            <div className="min-w-0">
              <div className={`text-sm font-semibold truncate ${step === 2 ? 'text-white' : 'text-slate-400'}`}>
                Candidate Artifacts
              </div>
            </div>
          </button>

          {/* Step 3 */}
          <button
            type="button"
            onClick={() => handleStepClick(3)}
            disabled={3 > maxStepAllowed}
            className={`group p-3 rounded-xl transition-all flex flex-col items-center text-center gap-2 ${
              step === 3 ? 'opacity-100' : 'opacity-70 hover:opacity-100'
            } ${3 > maxStepAllowed ? 'cursor-not-allowed opacity-40' : 'cursor-pointer'}`}
          >
            <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm shrink-0 transition-all ${
              isPipelineComplete && step === 3
                ? 'bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.5)]'
                : step === 3
                ? 'bg-indigo-500 text-white shadow-[0_0_15px_rgba(99,102,241,0.5)]'
                : 'bg-slate-800 text-slate-400'
            }`}>
              {isPipelineComplete && step === 3 ? <CheckCircle2 className="w-5 h-5" /> : '3'}
            </div>
            <div className="min-w-0">
              <div className={`text-sm font-semibold truncate ${step === 3 ? 'text-white' : 'text-slate-400'}`}>
                Intelligence Engine
              </div>
            </div>
          </button>
        </div>
      </div>

      {/* Step Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={step}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="bg-slate-900/30 rounded-2xl p-4 border border-slate-800/50"
        >
          {step === 1 && (
            <div className="space-y-4">
              <JobIntakeForm onComplete={handleJobFormComplete} />
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <GlassButton
                  variant="ghost"
                  size="sm"
                  onClick={() => handleStepClick(1)}
                  icon={<ArrowLeft className="w-4 h-4" />}
                >
                  Back to Role & Job Spec
                </GlassButton>
              </div>
              <CandidateIntakeForm onSubmit={handleCandidateFormSubmit} />
            </div>
          )}

          {step === 3 && (
            <div className="space-y-4">
              <div className="flex items-center justify-between px-1">
                <GlassButton
                  variant="ghost"
                  size="sm"
                  onClick={() => handleStepClick(2)}
                  icon={<ArrowLeft className="w-4 h-4" />}
                >
                  Back to Candidate Materials
                </GlassButton>
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
