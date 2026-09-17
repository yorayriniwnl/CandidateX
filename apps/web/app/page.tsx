'use client';

import React, { useState } from 'react';
import {
  Briefcase,
  Layers,
  UserCheck,
  Shield,
  Sparkles,
  ArrowRight,
  Award,
  Users,
  GitCompare,
  GraduationCap,
  HelpCircle,
  Play,
  FileCheck2,
} from 'lucide-react';
import { SystemNotice } from '../components/SystemNotice';
import { EvaluationWizard } from '../components/EvaluationWizard';
import { CandidateDirectory } from '../components/CandidateDirectory';
import { CandidateComparison } from '../components/CandidateComparison';
import { ResearchTheoremsExplorer } from '../components/ResearchTheoremsExplorer';
import { DossierView } from '../components/dossier/DossierView';
import { HowItWorksModal } from '../components/HowItWorksModal';
import { MOCK_DOSSIER, MOCK_GRAPH } from '../data/mockDossier';
import {
  checkBackendHealth,
  triggerPipelineRun,
  fetchPipelineStatus,
  fetchCandidateDossier,
  fetchCandidateGraph,
} from '../lib/api';
import { CanonicalRole, CandidateManifest, NormalizedRequirement, Dossier, CEGGraph } from '../types/cci';

type TabKey = 'directory' | 'new_eval' | 'dossier' | 'compare' | 'research';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabKey>('directory');
  const [currentRole, setCurrentRole] = useState<CanonicalRole>('backend');
  const [manifest, setManifest] = useState<CandidateManifest | null>({
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
  });
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pipelineStageIndex, setPipelineStageIndex] = useState(9);
  const [isPipelineComplete, setIsPipelineComplete] = useState(true);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [currentDossier, setCurrentDossier] = useState<Dossier>(MOCK_DOSSIER);
  const [currentGraph, setCurrentGraph] = useState<CEGGraph>(MOCK_GRAPH);
  const [isHowItWorksOpen, setIsHowItWorksOpen] = useState(false);
  const [comparisonCandidateIds, setComparisonCandidateIds] = useState<string[]>([
    '11111111-1111-1111-1111-111111111111',
    '77777777-7777-7777-7777-777777777777',
  ]);

  // Probe backend server connectivity on mount
  React.useEffect(() => {
    checkBackendHealth().then((online) => setIsBackendOnline(online));
  }, []);

  // Animate 10-stage execution pipeline upon candidate intake submission
  React.useEffect(() => {
    if (!isPipelineRunning) return;

    setPipelineStageIndex(0);
    setIsPipelineComplete(false);

    const interval = setInterval(() => {
      setPipelineStageIndex((prev) => {
        if (prev >= 9) {
          clearInterval(interval);
          setIsPipelineRunning(false);
          setIsPipelineComplete(true);
          return 9;
        }
        return prev + 1;
      });
    }, 350);

    return () => clearInterval(interval);
  }, [isPipelineRunning]);

  const handleJobComplete = (role: CanonicalRole, jdText: string, reqs: NormalizedRequirement[]) => {
    setCurrentRole(role);
  };

  const handleCandidateSubmit = async (candManifest: CandidateManifest) => {
    setManifest(candManifest);
    setIsPipelineRunning(true);

    // Attempt live pipeline run if backend is responsive
    if (isBackendOnline) {
      try {
        const runRes = await triggerPipelineRun(
          candManifest.candidate_id,
          currentRole,
          candManifest
        );
        if (runRes.status === 'completed' || runRes.dossier_id) {
          const liveDossier = await fetchCandidateDossier(candManifest.candidate_id);
          const liveGraph = await fetchCandidateGraph(candManifest.candidate_id);
          setCurrentDossier(liveDossier);
          setCurrentGraph(liveGraph);
        }
      } catch (err) {
        console.warn('Backend execution fallback to mock data:', err);
      }
    }
  };

  const handleSelectCandidateFromDirectory = async (candidateId: string, name: string) => {
    try {
      const liveDossier = await fetchCandidateDossier(candidateId);
      let liveGraph: CEGGraph = MOCK_GRAPH;
      try {
        liveGraph = await fetchCandidateGraph(candidateId);
      } catch {
        // Fallback to mock graph if CEG not cached
      }
      setCurrentDossier(liveDossier);
      setCurrentGraph(liveGraph);
      setManifest({
        candidate_id: candidateId,
        full_name: name,
        primary_email: '',
        github_usernames: [],
        github_repositories: [],
        deployment_urls: [],
        portfolio_urls: [],
        declared_skills: [],
        extraction_metadata: {},
      });
      setActiveTab('dossier');
    } catch (err) {
      console.warn('Failed to load live candidate dossier, falling back to mock:', err);
      setActiveTab('dossier');
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-600/30">
              C
            </div>
            <div>
              <span className="font-bold tracking-tight text-white text-base">Candidate Capability Intelligence</span>
              <span className="text-xs text-slate-400 font-mono ml-2 hidden sm:inline">v0.1.0-paper</span>
            </div>

            {/* Active Candidate Context Pill */}
            {manifest?.full_name && (
              <button
                type="button"
                onClick={() => setActiveTab('dossier')}
                className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 rounded-full text-xs text-slate-300 ml-2 transition-colors"
                title="Click to view candidate dossier"
              >
                <span className="text-slate-500 font-normal">Active:</span>
                <span className="font-semibold text-indigo-300">{manifest.full_name}</span>
              </button>
            )}

            {/* Live Backend Connection Indicator */}
            <div className="hidden md:flex items-center gap-2 text-xs border border-slate-800 bg-slate-900/80 px-2.5 py-1 rounded-full ml-1">
              <span className={`w-2 h-2 rounded-full ${isBackendOnline ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-amber-400'}`} />
              <span className="text-slate-300 font-mono text-[11px]">
                {isBackendOnline === null ? 'Probing...' : isBackendOnline ? 'Backend: Live' : 'Demo Mode'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Primary Navigation Tabs */}
            <nav className="flex items-center gap-1 bg-slate-900 p-1 border border-slate-800 rounded-lg text-xs">
              <button
                onClick={() => setActiveTab('directory')}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                  activeTab === 'directory' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Users className="w-3.5 h-3.5" />
                <span>Candidates</span>
              </button>

              <button
                onClick={() => setActiveTab('new_eval')}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                  activeTab === 'new_eval' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Play className="w-3.5 h-3.5 text-indigo-300" />
                <span>New Evaluation</span>
              </button>

              <button
                onClick={() => setActiveTab('dossier')}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                  activeTab === 'dossier' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Award className="w-3.5 h-3.5" />
                <span>Candidate Dossier</span>
              </button>

              <button
                onClick={() => setActiveTab('compare')}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                  activeTab === 'compare' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <GitCompare className="w-3.5 h-3.5" />
                <span>Compare</span>
              </button>

              <button
                onClick={() => setActiveTab('research')}
                className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                  activeTab === 'research' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <GraduationCap className="w-3.5 h-3.5" />
                <span>Methodology &amp; Math</span>
              </button>
            </nav>

            {/* How It Works Button */}
            <button
              type="button"
              onClick={() => setIsHowItWorksOpen(true)}
              className="px-2.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 shrink-0"
              title="Learn how CCI works and understand evaluation metrics"
            >
              <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
              <span className="hidden sm:inline">How It Works</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 w-full">
        <SystemNotice />

        {activeTab === 'directory' && (
          <CandidateDirectory
            onSelectCandidate={handleSelectCandidateFromDirectory}
            onNewCandidate={() => setActiveTab('new_eval')}
            isBackendOnline={isBackendOnline}
            initialSelectedForComparison={comparisonCandidateIds}
            onCompareCandidates={(ids) => {
              setComparisonCandidateIds(ids);
              setActiveTab('compare');
            }}
          />
        )}

        {activeTab === 'new_eval' && (
          <EvaluationWizard
            currentRole={currentRole}
            pipelineStageIndex={pipelineStageIndex}
            isPipelineRunning={isPipelineRunning}
            isPipelineComplete={isPipelineComplete}
            onJobComplete={handleJobComplete}
            onCandidateSubmit={handleCandidateSubmit}
            onViewDossier={() => setActiveTab('dossier')}
          />
        )}

        {activeTab === 'dossier' && (
          <DossierView
            initialDossier={currentDossier}
            graph={currentGraph}
            candidateName={manifest?.full_name || 'Alice Chen'}
            onSelectCandidate={handleSelectCandidateFromDirectory}
          />
        )}

        {activeTab === 'compare' && (
          <CandidateComparison
            onSelectCandidateDossier={handleSelectCandidateFromDirectory}
            isBackendOnline={isBackendOnline}
            selectedCandidateIds={comparisonCandidateIds}
            onSelectedIdsChange={setComparisonCandidateIds}
          />
        )}

        {activeTab === 'research' && (
          <ResearchTheoremsExplorer isBackendOnline={isBackendOnline} />
        )}
      </main>

      {/* Interactive How It Works Onboarding Modal */}
      <HowItWorksModal
        isOpen={isHowItWorksOpen}
        onClose={() => setIsHowItWorksOpen(false)}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        Candidate Capability Intelligence (CCI) Platform — Decision Support System for Technical Hiring Teams
      </footer>
    </div>
  );
}
