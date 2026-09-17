'use client';

import React, { useState } from 'react';
import { CheckSquare, ExternalLink, FileUp, GitBranch, Globe, Plus, Trash2, UserCheck, ShieldAlert } from 'lucide-react';
import { CandidateManifest } from '../types/cci';

export const CandidateIntakeForm: React.FC<{
  onSubmit?: (manifest: CandidateManifest) => void;
}> = ({ onSubmit }) => {
  const [candidateName, setCandidateName] = useState('Alice Developer');
  const [candidateEmail, setCandidateEmail] = useState('alice.dev@example.com');
  const [githubRepos, setGithubRepos] = useState<string[]>([
    'https://github.com/alicedev/high-throughput-service',
    'https://github.com/alicedev/distributed-cache',
  ]);
  const [newRepoUrl, setNewRepoUrl] = useState('');
  const [deploymentUrls, setDeploymentUrls] = useState<string[]>([
    'https://alice-portfolio.vercel.app',
  ]);
  const [newDeployUrl, setNewDeployUrl] = useState('');
  const [hasConsent, setHasConsent] = useState(true);
  const [fileName, setFileName] = useState('Alice_Developer_CV.pdf');

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
      candidate_id: 'cand-' + Math.random().toString(36).substring(2, 9),
      full_name: candidateName,
      primary_email: candidateEmail,
      github_usernames: ['alicedev'],
      github_repositories: githubRepos,
      deployment_urls: deploymentUrls,
      portfolio_urls: deploymentUrls,
      declared_skills: ['Python', 'FastAPI', 'PostgreSQL', 'Docker'],
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
