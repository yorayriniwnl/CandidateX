'use client';

import React, { useState } from 'react';
import { CheckSquare, ExternalLink, FileUp, GitBranch, Globe, Plus, Trash2, UserCheck, ShieldAlert, Sparkles } from 'lucide-react';
import { CandidateManifest } from '../types/cci';

interface CandidatePreset {
  id: string;
  name: string;
  email: string;
  role: string;
  badge: string;
  badgeColor: string;
  repos: string[];
  deployments: string[];
  skills: string[];
  file: string;
}

const CANONICAL_PRESETS: CandidatePreset[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    name: 'Alice Chen',
    email: 'alice.chen@example.com',
    role: 'Backend (Senior)',
    badge: 'High Coverage',
    badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    repos: [
      'https://github.com/alicechen-dev/distributed-payment-engine',
      'https://github.com/alicechen-dev/pg-partition-manager',
    ],
    deployments: ['https://alicechen.dev'],
    skills: ['Python', 'Go', 'PostgreSQL', 'Kafka', 'Docker', 'Distributed Systems'],
    file: 'Alice_Chen_Backend_CV.pdf',
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    name: 'Elena Rostova',
    email: 'elena.rostova@example.com',
    role: 'Frontend (Staff)',
    badge: 'Design Systems',
    badgeColor: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    repos: [
      'https://github.com/erostova-web/a11y-kit-react',
      'https://github.com/erostova-web/next-vitals-booster',
    ],
    deployments: ['https://erostova.design'],
    skills: ['TypeScript', 'React', 'Next.js', 'Web Vitals', 'WAI-ARIA', 'Tailwind CSS'],
    file: 'Elena_Rostova_Frontend_CV.pdf',
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    name: 'Dr. Marcus Thorne',
    email: 'marcus.thorne@example.com',
    role: 'ML Engineer (Senior)',
    badge: 'PyTorch / LLMs',
    badgeColor: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    repos: [
      'https://github.com/mthorne-ai/fast-alignment',
      'https://github.com/mthorne-ai/vector-gateway-service',
    ],
    deployments: ['https://mthorne.ai'],
    skills: ['Python', 'PyTorch', 'Transformers', 'vLLM', 'Qdrant', 'Model Evaluation'],
    file: 'Marcus_Thorne_ML_CV.pdf',
  },
  {
    id: '44444444-4444-4444-4444-444444444444',
    name: 'Tariq Mansour',
    email: 'tariq.mansour@example.com',
    role: 'DevOps / SRE (Staff)',
    badge: 'K8s / Terraform',
    badgeColor: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
    repos: [
      'https://github.com/tmansour-infra/tf-blast-guard',
      'https://github.com/tmansour-infra/k8s-region-failover',
    ],
    deployments: ['https://tmansour.cloud'],
    skills: ['Kubernetes', 'Terraform', 'Prometheus', 'ArgoCD', 'eBPF', 'AWS'],
    file: 'Tariq_Mansour_SRE_CV.pdf',
  },
  {
    id: '55555555-5555-5555-5555-555555555555',
    name: "Samuel O'Connor",
    email: 'samuel.oconnor@example.com',
    role: 'Fullstack (Principal)',
    badge: 'Type-Safe Stack',
    badgeColor: 'bg-teal-500/20 text-teal-300 border-teal-500/30',
    repos: [
      'https://github.com/soconnor-fullstack/type-safe-stack',
      'https://github.com/soconnor-fullstack/collab-canvas',
    ],
    deployments: ['https://soconnor.tech'],
    skills: ['React', 'Next.js', 'Node.js', 'PostgreSQL', 'Redis', 'tRPC'],
    file: 'Samuel_OConnor_Fullstack_CV.pdf',
  },
  {
    id: '66666666-6666-6666-6666-666666666666',
    name: 'Jordan Blake',
    email: 'jordan.blake@example.com',
    role: 'Backend (Junior)',
    badge: 'Sparse Evidence',
    badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-500/30',
    repos: [
      'https://github.com/jordanblake-dev/mini-calculator-script',
    ],
    deployments: [],
    skills: ['Python', 'Basic Scripting'],
    file: 'Jordan_Blake_Junior_CV.pdf',
  },
  {
    id: '77777777-7777-7777-7777-777777777777',
    name: 'Devin Vance',
    email: 'devin.vance@example.com',
    role: 'Backend (Conflict Test)',
    badge: 'Contradiction Flag',
    badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-500/30',
    repos: [
      'https://github.com/devinvance-dev/distributed-order-service',
    ],
    deployments: [],
    skills: ['Python', 'Unindexed Database Claims', 'Microservices'],
    file: 'Devin_Vance_CV.pdf',
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
  const [deploymentUrls, setDeploymentUrls] = useState<string[]>(CANONICAL_PRESETS[0].deployments);
  const [newDeployUrl, setNewDeployUrl] = useState('');
  const [hasConsent, setHasConsent] = useState(true);
  const [fileName, setFileName] = useState(CANONICAL_PRESETS[0].file);
  const [declaredSkills, setDeclaredSkills] = useState<string[]>(CANONICAL_PRESETS[0].skills);

  const applyPreset = (preset: CandidatePreset) => {
    setCandidateId(preset.id);
    setCandidateName(preset.name);
    setCandidateEmail(preset.email);
    setGithubRepos(preset.repos);
    setDeploymentUrls(preset.deployments);
    setFileName(preset.file);
    setDeclaredSkills(preset.skills);
  };

  const addRepo = () => {
    if (newRepoUrl && !githubRepos.includes(newRepoUrl)) {
      setGithubRepos([...githubRepos, newRepoUrl]);
      setNewRepoUrl('');
    }
  };

  const removeRepo = (idx: number) => {
    setGithubRepos(githubRepos.filter((_, i) => i !== idx));
  };

  const addDeploy = () => {
    if (newDeployUrl && !deploymentUrls.includes(newDeployUrl)) {
      setDeploymentUrls([...deploymentUrls, newDeployUrl]);
      setNewDeployUrl('');
    }
  };

  const removeDeploy = (idx: number) => {
    setDeploymentUrls(deploymentUrls.filter((_, i) => i !== idx));
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
    <form onSubmit={handleSubmit} className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
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

      {/* Canonical Cohort Quick-Load Presets */}
      <div>
        <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
          Load Canonical Candidate Fixture
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          {CANONICAL_PRESETS.map((p) => {
            const isSelected = candidateId === p.id;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => applyPreset(p)}
                className={`text-left p-2.5 rounded-lg border transition-all ${
                  isSelected
                    ? 'bg-emerald-500/10 border-emerald-500/60 ring-1 ring-emerald-500/50'
                    : 'bg-slate-950/50 border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1 gap-1">
                  <span className={`text-xs font-medium truncate ${isSelected ? 'text-emerald-300' : 'text-slate-200'}`}>
                    {p.name}
                  </span>
                  <span className={`px-1.5 py-0.5 text-[9px] font-semibold rounded border shrink-0 ${p.badgeColor}`}>
                    {p.badge}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 truncate">{p.role}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Candidate Full Name</label>
          <input
            type="text"
            required
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
            value={candidateName}
            onChange={(e) => setCandidateName(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1">Primary Email</label>
          <input
            type="email"
            required
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
            value={candidateEmail}
            onChange={(e) => setCandidateEmail(e.target.value)}
          />
        </div>
      </div>

      {/* CV Document Upload */}
      <div>
        <label className="block text-xs font-medium text-slate-300 mb-1">CV Document (PDF or DOCX)</label>
        <div className="border-2 border-dashed border-slate-700 hover:border-slate-600 rounded-lg p-4 bg-slate-950/40 text-center cursor-pointer transition-colors">
          <FileUp className="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
          <p className="text-sm font-medium text-slate-300">{fileName}</p>
          <p className="text-xs text-slate-500">Embedded annotations and hyperlinks extracted deterministically</p>
        </div>
      </div>

      {/* Extracted Repositories */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-slate-300 flex items-center gap-1.5">
          <GitBranch className="w-3.5 h-3.5 text-slate-400" />
          <span>Declared GitHub Repositories (Closed-World Manifest)</span>
        </label>
        <div className="space-y-1.5">
          {githubRepos.map((repo, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs"
            >
              <span className="font-mono text-slate-300">{repo}</span>
              <button
                type="button"
                onClick={() => removeRepo(idx)}
                className="text-slate-500 hover:text-rose-400 transition-colors p-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-2 pt-1">
          <input
            type="url"
            placeholder="https://github.com/candidate/new-project"
            className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
            value={newRepoUrl}
            onChange={(e) => setNewRepoUrl(e.target.value)}
          />
          <button
            type="button"
            onClick={addRepo}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium flex items-center gap-1 border border-slate-700"
          >
            <Plus className="w-3.5 h-3.5" /> Add
          </button>
        </div>
      </div>

      {/* Extracted Deployments */}
      <div className="space-y-2">
        <label className="block text-xs font-medium text-slate-300 flex items-center gap-1.5">
          <Globe className="w-3.5 h-3.5 text-slate-400" />
          <span>Declared Live Deployments & Portfolios</span>
        </label>
        <div className="space-y-1.5">
          {deploymentUrls.map((url, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between p-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs"
            >
              <span className="font-mono text-slate-300">{url}</span>
              <button
                type="button"
                onClick={() => removeDeploy(idx)}
                className="text-slate-500 hover:text-rose-400 transition-colors p-1"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
        <div className="flex gap-2 pt-1">
          <input
            type="url"
            placeholder="https://demo-app.vercel.app"
            className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
            value={newDeployUrl}
            onChange={(e) => setNewDeployUrl(e.target.value)}
          />
          <button
            type="button"
            onClick={addDeploy}
            className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium flex items-center gap-1 border border-slate-700"
          >
            <Plus className="w-3.5 h-3.5" /> Add
          </button>
        </div>
      </div>

      {/* Candidate Consent Checkbox */}
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

      <button
        type="submit"
        disabled={!hasConsent}
        className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2"
      >
        <UserCheck className="w-4 h-4" />
        Register Candidate & Initiate Intelligence Pipeline
      </button>
    </form>
  );
};
