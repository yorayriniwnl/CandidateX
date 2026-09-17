'use client';

import React, { useState } from 'react';
import {
  Briefcase,
  UserCheck,
  Layers,
  Sparkles,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Play,
  FileText,
  AlertTriangle,
  Award,
} from 'lucide-react';
import { CanonicalRole, CandidateManifest, NormalizedRequirement } from '../types/cci';
import { JobIntakeForm } from './JobIntakeForm';
import { CandidateIntakeForm } from './CandidateIntakeForm';
import { PipelineTracker } from './PipelineTracker';

interface QuickDemoProfile {
  id: string;
  name: string;
  role: CanonicalRole;
  label: string;
  badge: string;
  badgeColor: string;
  manifest: CandidateManifest;
}

const QUICK_DEMO_PROFILES: QuickDemoProfile[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    name: 'Alice Chen',
    role: 'backend',
    label: 'Senior Distributed Backend',
    badge: 'High Coverage (RCI 90.0)',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
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
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
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
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
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

  // When pipeline starts running, switch to step 3
  React.useEffect(() => {
    if (isPipelineRunning) {
      setStep(3);
    }
  }, [isPipelineRunning]);

  const handleQuickDemoClick = (profile: QuickDemoProfile) => {
    // 1. Complete Job Spec
    onJobComplete(profile.role, '', []);
    // 2. Submit candidate manifest and trigger pipeline
    onCandidateSubmit(profile.manifest);
    // 3. Jump to Step 3
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
    <div className="space-y-6">
      {/* 1-Click Quick Demo Toolbar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <div className="p-1.5 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <span className="text-xs font-semibold text-slate-200">1-Click Demonstration Pre-sets:</span>
              <span className="text-[11px] text-slate-400 ml-1.5 hidden md:inline">
                Skip manual entry and evaluate a pre-configured candidate instantly:
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {QUICK_DEMO_PROFILES.map((profile) => (
              <button
                key={profile.id}
                type="button"
                onClick={() => handleQuickDemoClick(profile)}
                className="px-3 py-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-indigo-500/40 rounded-lg text-xs font-medium text-slate-200 transition-colors flex items-center gap-1.5"
              >
                <Play className="w-3 h-3 text-indigo-400" />
                <span>{profile.name}</span>
                <span className={`px-1.5 py-0.2 rounded text-[10px] border ${profile.badgeColor}`}>
                  {profile.badge}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Visual Stepper Progress Bar */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-xl">
        <div className="grid grid-cols-3 gap-2 text-xs">
          {/* Step 1 */}
          <button
            type="button"
            onClick={() => setStep(1)}
            className={`p-3 rounded-lg border transition-colors text-left flex items-center gap-3 ${
              step === 1
                ? 'bg-indigo-600/15 border-indigo-500 text-white shadow-sm'
                : 'bg-slate-950 border-slate-800/80 text-slate-400 hover:text-slate-200'
            }`}
          >
            <div className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
              step > 1 ? 'bg-emerald-500 text-white' : step === 1 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
            }`}>
              {step > 1 ? <CheckCircle2 className="w-4 h-4" /> : '1'}
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-slate-200 truncate">Step 1: Role &amp; Job Spec</div>
              <div className="text-[11px] text-slate-500 truncate">Select role &amp; requirements</div>
            </div>
          </button>

          {/* Step 2 */}
          <button
            type="button"
            onClick={() => setStep(2)}
            className={`p-3 rounded-lg border transition-colors text-left flex items-center gap-3 ${
              step === 2
                ? 'bg-indigo-600/15 border-indigo-500 text-white shadow-sm'
                : 'bg-slate-950 border-slate-800/80 text-slate-400 hover:text-slate-200'
            }`}
          >
            <div className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
              step > 2 ? 'bg-emerald-500 text-white' : step === 2 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
            }`}>
              {step > 2 ? <CheckCircle2 className="w-4 h-4" /> : '2'}
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-slate-200 truncate">Step 2: Candidate Materials</div>
              <div className="text-[11px] text-slate-500 truncate">CV, GitHub &amp; public links</div>
            </div>
          </button>

          {/* Step 3 */}
          <button
            type="button"
            onClick={() => setStep(3)}
            className={`p-3 rounded-lg border transition-colors text-left flex items-center gap-3 ${
              step === 3
                ? 'bg-indigo-600/15 border-indigo-500 text-white shadow-sm'
                : 'bg-slate-950 border-slate-800/80 text-slate-400 hover:text-slate-200'
            }`}
          >
            <div className={`w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shrink-0 ${
              isPipelineComplete && step === 3 ? 'bg-emerald-500 text-white' : step === 3 ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-slate-400'
            }`}>
              {isPipelineComplete && step === 3 ? <CheckCircle2 className="w-4 h-4" /> : '3'}
            </div>
            <div className="min-w-0">
              <div className="font-semibold text-slate-200 truncate">Step 3: Live Pipeline</div>
              <div className="text-[11px] text-slate-500 truncate">10-stage AST &amp; math execution</div>
            </div>
          </button>
        </div>
      </div>

      {/* Step Content */}
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
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors"
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
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1.5 transition-colors"
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
    </div>
  );
};
