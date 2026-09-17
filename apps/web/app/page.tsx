'use client';

import React, { useState } from 'react';
import { Briefcase, Layers, UserCheck, Shield, Sparkles, ArrowRight, Award, Users } from 'lucide-react';
import { SystemNotice } from '../components/SystemNotice';
import { JobIntakeForm } from '../components/JobIntakeForm';
import { CandidateIntakeForm } from '../components/CandidateIntakeForm';
import { PipelineTracker } from '../components/PipelineTracker';
import { CandidateDirectory } from '../components/CandidateDirectory';
import { DossierView } from '../components/dossier/DossierView';
import { MOCK_DOSSIER, MOCK_GRAPH } from '../data/mockDossier';
import { checkBackendHealth, triggerPipelineRun, fetchPipelineStatus, fetchCandidateDossier, fetchCandidateGraph } from '../lib/api';
import { CanonicalRole, CandidateManifest, NormalizedRequirement, Dossier, CEGGraph } from '../types/cci';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<'directory' | 'job' | 'candidate' | 'pipeline' | 'dossier'>('directory');
  const [currentRole, setCurrentRole] = useState<CanonicalRole>('backend');
  const [manifest, setManifest] = useState<CandidateManifest | null>(null);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pipelineStageIndex, setPipelineStageIndex] = useState(9);
  const [isPipelineComplete, setIsPipelineComplete] = useState(true);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [currentDossier, setCurrentDossier] = useState<Dossier>(MOCK_DOSSIER);
  const [currentGraph, setCurrentGraph] = useState<CEGGraph>(MOCK_GRAPH);

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
    setActiveTab('candidate');
  };

  const handleCandidateSubmit = async (candManifest: CandidateManifest) => {
    setManifest(candManifest);
    setIsPipelineRunning(true);
    setActiveTab('pipeline');

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
              <span className="text-xs text-slate-400 font-mono ml-2">v0.1.0-paper</span>
            </div>
            {/* Live Backend Connection Indicator */}
            <div className="hidden sm:flex items-center gap-2 text-xs border border-slate-800 bg-slate-900/80 px-2.5 py-1 rounded-full ml-3">
              <span className={`w-2 h-2 rounded-full ${isBackendOnline ? 'bg-emerald-400 shadow-sm shadow-emerald-400/50' : 'bg-amber-400'}`} />
              <span className="text-slate-300 font-mono text-[11px]">
                {isBackendOnline === null ? 'Probing API...' : isBackendOnline ? 'Backend: Live' : 'Demo Mode (Mock)'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-1 bg-slate-900 p-1 border border-slate-800 rounded-lg text-xs">
            <button
              onClick={() => setActiveTab('directory')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'directory' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Users className="w-3.5 h-3.5" /> Directory
            </button>
            <button
              onClick={() => setActiveTab('job')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'job' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Briefcase className="w-3.5 h-3.5" /> 1. Job Intake
            </button>
            <button
              onClick={() => setActiveTab('candidate')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'candidate' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <UserCheck className="w-3.5 h-3.5" /> 2. Candidate Intake
            </button>
            <button
              onClick={() => setActiveTab('pipeline')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'pipeline' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" /> 3. Pipeline
            </button>
            <button
              onClick={() => setActiveTab('dossier')}
              className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === 'dossier' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Award className="w-3.5 h-3.5" /> 4. Candidate Dossier
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
            onNewCandidate={() => setActiveTab('candidate')}
            isBackendOnline={isBackendOnline}
          />
        )}

        {activeTab === 'job' && (
          <JobIntakeForm onComplete={handleJobComplete} />
        )}

        {activeTab === 'candidate' && (
          <CandidateIntakeForm onSubmit={handleCandidateSubmit} />
        )}

        {activeTab === 'pipeline' && (
          <PipelineTracker
            currentStageIndex={pipelineStageIndex}
            isComplete={isPipelineComplete}
            onViewDossier={() => setActiveTab('dossier')}
          />
        )}

        {activeTab === 'dossier' && (
          <DossierView
            initialDossier={currentDossier}
            graph={currentGraph}
            candidateName={manifest?.full_name || 'Alice Developer'}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950 py-4 text-center text-xs text-slate-500">
        Candidate Capability Intelligence (CCI) Platform — Decision Support System for Technical Hiring Teams
      </footer>
    </div>
  );
}
