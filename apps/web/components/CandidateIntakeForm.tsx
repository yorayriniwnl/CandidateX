'use client';

import React, { useState, useRef } from 'react';
import { CheckSquare, ExternalLink, FileUp, GitBranch, Globe, Plus, Trash2, UserCheck, ShieldAlert, Sparkles } from 'lucide-react';
import { CandidateManifest } from '../types/cci';

import { GlassCard } from '@/components/ui/GlassCard';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassButton } from '@/components/ui/GlassButton';
import { GlowBadge } from '@/components/ui/GlowBadge';
import { motion, AnimatePresence } from 'framer-motion';

interface CandidatePreset {
  id: string;
  name: string;
  email: string;
  role: string;
  badge: string;
  badgeColor: string;
  badgeVariant: 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand';
  repos: string[];
  deployments: string[];
  skills: string[];
  file: string;
}

const CANONICAL_PRESETS: CandidatePreset[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    name: 'Jordan Example (SYNTHETIC DEMONSTRATION DATA)',
    email: 'jordan@example.test',
    role: 'Backend (Senior)',
    badge: 'High Coverage',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    badgeVariant: 'success',
    repos: [
      'https://github.com/jordan-example-backend/distributed-payment-engine',
      'https://github.com/jordan-example-backend/pg-partition-manager',
    ],
    deployments: ['https://jordan.example.test'],
    skills: ['Python', 'Go', 'PostgreSQL', 'Kafka', 'Docker', 'Distributed Systems'],
    file: 'Jordan_Example_Backend_CV.pdf',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Alex Rivera (SYNTHETIC DEMONSTRATION DATA)',
    email: 'alex@example.test',
    role: 'Frontend (Staff)',
    badge: 'Design Systems',
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    badgeVariant: 'brand',
    repos: [
      'https://github.com/alex-rivera-frontend/a11y-kit-react',
      'https://github.com/alex-rivera-frontend/next-vitals-booster',
    ],
    deployments: ['https://alex.example.test'],
    skills: ['TypeScript', 'React', 'Next.js', 'Web Vitals', 'WAI-ARIA', 'Tailwind CSS'],
    file: 'Alex_Rivera_Frontend_CV.pdf',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    name: 'Morgan Lee (SYNTHETIC DEMONSTRATION DATA)',
    email: 'morgan@example.test',
    role: 'ML Engineer (Senior)',
    badge: 'PyTorch / LLMs',
    badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    badgeVariant: 'brand',
    repos: [
      'https://github.com/morgan-lee-ai/fast-alignment',
      'https://github.com/morgan-lee-ai/vector-gateway-service',
    ],
    deployments: ['https://morgan.example.test'],
    skills: ['Python', 'PyTorch', 'Transformers', 'vLLM', 'Qdrant', 'Model Evaluation'],
    file: 'Morgan_Lee_ML_CV.pdf',
  },
  {
    id: '44444444-4444-4444-4444-444444444444',
    name: 'Taylor Casey (SYNTHETIC DEMONSTRATION DATA)',
    email: 'taylor@example.test',
    role: 'DevOps / SRE (Staff)',
    badge: 'K8s / Terraform',
    badgeColor: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
    badgeVariant: 'info',
    repos: [
      'https://github.com/taylor-casey-infra/tf-blast-guard',
      'https://github.com/taylor-casey-infra/k8s-region-failover',
    ],
    deployments: ['https://taylor.example.test'],
    skills: ['Kubernetes', 'Terraform', 'Prometheus', 'ArgoCD', 'eBPF', 'AWS'],
    file: 'Taylor_Casey_DevOps_CV.pdf',
  },
  {
    id: '55555555-5555-5555-5555-555555555555',
    name: 'Sam Vance (SYNTHETIC DEMONSTRATION DATA)',
    email: 'sam@example.test',
    role: 'Fullstack (Principal)',
    badge: 'Type-Safe Stack',
    badgeColor: 'bg-teal-500/20 text-teal-300 border-teal-500/30',
    badgeVariant: 'info',
    repos: [
      'https://github.com/sam-vance-fullstack/type-safe-stack',
      'https://github.com/sam-vance-fullstack/collab-canvas',
    ],
    deployments: ['https://sam.example.test'],
    skills: ['React', 'Next.js', 'Node.js', 'PostgreSQL', 'Redis', 'tRPC'],
    file: 'Sam_Vance_Fullstack_CV.pdf',
  },
  {
    id: '77777777-7777-7777-7777-777777777777',
    name: 'Quinn Avery (SYNTHETIC DEMONSTRATION DATA)',
    email: 'quinn@example.test',
    role: 'Backend (Discrepancy Test)',
    badge: 'Contradiction Flag',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    badgeVariant: 'danger',
    repos: [
      'https://github.com/quinn-avery-dev/distributed-order-service',
    ],
    deployments: [],
    skills: ['Python', 'Unindexed Database Claims', 'Microservices'],
    file: 'Quinn_Avery_CV.pdf',
  },
];

export const CandidateIntakeForm: React.FC<{
  onSubmit?: (manifest: CandidateManifest) => void;
}> = ({ onSubmit }) => {
  const [candidateId, setCandidateId] = useState(CANONICAL_PRESETS[0].id);
  const [candidateName, setCandidateName] = useState(CANONICAL_PRESETS[0].name);
  const [candidateEmail, setCandidateEmail] = useState(CANONICAL_PRESETS[0].email);
  const [githubRepos, setGithubRepos] = useState<string[]>(CANONICAL_PRESETS[0].repos);
  const [newRepoUrl, setNewRepoUrl] = useState('');
  const [repoError, setRepoError] = useState('');
  const [deploymentUrls, setDeploymentUrls] = useState<string[]>(CANONICAL_PRESETS[0].deployments);
  const [newDeployUrl, setNewDeployUrl] = useState('');
  const [deployError, setDeployError] = useState('');
  const [hasConsent, setHasConsent] = useState(true);
  const [fileName, setFileName] = useState(CANONICAL_PRESETS[0].file);
  const [declaredSkills, setDeclaredSkills] = useState<string[]>(CANONICAL_PRESETS[0].skills);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const applyPreset = (preset: CandidatePreset) => {
    setCandidateId(preset.id);
    setCandidateName(preset.name);
    setCandidateEmail(preset.email);
    setGithubRepos(preset.repos);
    setDeploymentUrls(preset.deployments);
    setFileName(preset.file);
    setDeclaredSkills(preset.skills);
  };

  const isValidUrl = (url: string) => {
    return url.startsWith('http://') || url.startsWith('https://');
  };

  const addRepo = () => {
    setRepoError('');
    if (newRepoUrl) {
      if (!isValidUrl(newRepoUrl)) {
        setRepoError('URL must start with http:// or https://');
        return;
      }
      if (!githubRepos.includes(newRepoUrl)) {
        setGithubRepos([...githubRepos, newRepoUrl]);
        setNewRepoUrl('');
      }
    }
  };

  const removeRepo = (idx: number) => {
    setGithubRepos(githubRepos.filter((_, i) => i !== idx));
  };

  const addDeploy = () => {
    setDeployError('');
    if (newDeployUrl) {
      if (!isValidUrl(newDeployUrl)) {
        setDeployError('URL must start with http:// or https://');
        return;
      }
      if (!deploymentUrls.includes(newDeployUrl)) {
        setDeploymentUrls([...deploymentUrls, newDeployUrl]);
        setNewDeployUrl('');
      }
    }
  };

  const removeDeploy = (idx: number) => {
    setDeploymentUrls(deploymentUrls.filter((_, i) => i !== idx));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFileName(e.target.files[0].name);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasConsent) return;

    const manifest: CandidateManifest = {
      candidate_id: candidateId,
      full_name: candidateName,
      primary_email: candidateEmail,
      github_usernames: [candidateEmail.split('@')[0]],
      github_repositories: githubRepos,
      deployment_urls: deploymentUrls,
      portfolio_urls: deploymentUrls,
      declared_skills: declaredSkills,
      extraction_metadata: { source: fileName, extracted_at: new Date().toISOString() },
    };

    if (onSubmit) {
      onSubmit(manifest);
    }
  };

  return (
    <GlassCard variant="strong" glow="emerald" className="p-6 space-y-6">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 rounded-lg text-emerald-400">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Candidate Technical Identity Intake</h2>
              <p className="text-xs text-slate-400">Closed-world evidence manifest extraction from CV</p>
            </div>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            Load Canonical Candidate Fixture
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
            {CANONICAL_PRESETS.map((p) => {
              const isSelected = candidateId === p.id;
              return (
                <GlassCard
                  key={p.id}
                  variant="subtle"
                  glow={isSelected ? 'emerald' : 'none'}
                  hoverLift
                  className={`cursor-pointer p-2.5 transition-all text-left ${isSelected ? 'ring-1 ring-emerald-500/50' : ''}`}
                  onClick={() => applyPreset(p)}
                >
                  <div className="flex items-center justify-between mb-1 gap-1">
                    <span className={`text-xs font-medium truncate ${isSelected ? 'text-emerald-300' : 'text-slate-200'}`}>
                      {p.name}
                    </span>
                    <GlowBadge variant={p.badgeVariant} size="sm">
                      {p.badge}
                    </GlowBadge>
                  </div>
                  <p className="text-[11px] text-slate-400 truncate">{p.role}</p>
                </GlassCard>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <GlassInput
            label="Candidate Full Name"
            required
            value={candidateName}
            onChange={(e) => setCandidateName(e.target.value)}
            glowColor="emerald"
          />
          <GlassInput
            type="email"
            label="Primary Email"
            required
            value={candidateEmail}
            onChange={(e) => setCandidateEmail(e.target.value)}
            glowColor="emerald"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">CV Document (PDF or DOCX)</label>
          <div 
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-700 hover:border-slate-600 rounded-lg p-4 bg-slate-950/40 text-center cursor-pointer transition-colors"
          >
            <FileUp className="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
            <p className="text-sm font-medium text-slate-300">{fileName}</p>
            <p className="text-xs text-slate-500">Embedded annotations and hyperlinks extracted deterministically</p>
          </div>
          <input 
            type="file" 
            ref={fileInputRef} 
            className="hidden" 
            accept=".pdf,.txt,.docx"
            onChange={handleFileChange}
          />
        </div>

        <div className="space-y-2">
          <label className="block text-xs font-medium text-slate-300 flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5 text-slate-400" />
            <span>Declared GitHub Repositories (Closed-World Manifest)</span>
          </label>
          <div className="space-y-1.5">
            <AnimatePresence>
              {githubRepos.map((repo, idx) => (
                <motion.div
                  key={repo}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-center justify-between p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs overflow-hidden"
                >
                  <span className="font-mono text-slate-300">{repo}</span>
                  <button
                    type="button"
                    onClick={() => removeRepo(idx)}
                    className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          <div className="flex gap-2 pt-1 items-start">
            <div className="flex-1">
              <GlassInput
                type="url"
                placeholder="https://github.com/candidate/new-project"
                value={newRepoUrl}
                onChange={(e) => setNewRepoUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addRepo();
                  }
                }}
                error={repoError}
                glowColor="emerald"
              />
            </div>
            <GlassButton
              type="button"
              variant="secondary"
              onClick={addRepo}
              icon={<Plus className="w-3.5 h-3.5" />}
              iconPosition="left"
            >
              Add
            </GlassButton>
          </div>
        </div>

        <div className="space-y-2">
          <label className="block text-xs font-medium text-slate-300 flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5 text-slate-400" />
            <span>Declared Live Deployments & Portfolios</span>
          </label>
          <div className="space-y-1.5">
            <AnimatePresence>
              {deploymentUrls.map((url, idx) => (
                <motion.div
                  key={url}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="flex items-center justify-between p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs overflow-hidden"
                >
                  <span className="font-mono text-slate-300">{url}</span>
                  <button
                    type="button"
                    onClick={() => removeDeploy(idx)}
                    className="text-slate-500 hover:text-rose-400 transition-colors p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
          <div className="flex gap-2 pt-1 items-start">
            <div className="flex-1">
              <GlassInput
                type="url"
                placeholder="https://demo-app.vercel.app"
                value={newDeployUrl}
                onChange={(e) => setNewDeployUrl(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addDeploy();
                  }
                }}
                error={deployError}
                glowColor="emerald"
              />
            </div>
            <GlassButton
              type="button"
              variant="secondary"
              onClick={addDeploy}
              icon={<Plus className="w-3.5 h-3.5" />}
              iconPosition="left"
            >
              Add
            </GlassButton>
          </div>
        </div>

        <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-lg flex items-start gap-2.5">
          <input
            type="checkbox"
            id="consent-check"
            checked={hasConsent}
            onChange={(e) => setHasConsent(e.target.checked)}
            className="mt-0.5 rounded border-slate-700 text-emerald-600 focus:ring-emerald-500"
          />
          <label htmlFor="consent-check" className="text-xs text-slate-300 cursor-pointer">
            <span className="font-semibold text-slate-200">Candidate Explicit Consent Acknowledged:</span>{' '}
            Candidate has provided authorization to inspect their declared repository artifacts, documentation, and live deployments for decision support. No unauthorized internet crawling will occur.
          </label>
        </div>

        <GlassButton
          type="submit"
          disabled={!hasConsent}
          variant="primary"
          icon={<UserCheck className="w-4 h-4" />}
          iconPosition="left"
          fullWidth
        >
          Register Candidate & Initiate Intelligence Pipeline
        </GlassButton>
      </form>
    </GlassCard>
  );
};
