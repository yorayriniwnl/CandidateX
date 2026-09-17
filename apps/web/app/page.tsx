'use client';

import React, { useState } from 'react';
import { Briefcase, Layers, UserCheck, Shield, Sparkles, ArrowRight, Award } from 'lucide-react';
import { SystemNotice } from '../components/SystemNotice';
import { JobIntakeForm } from '../components/JobIntakeForm';
import { CandidateIntakeForm } from '../components/CandidateIntakeForm';
import { PipelineTracker } from '../components/PipelineTracker';
import { DossierView } from '../components/dossier/DossierView';
import { MOCK_DOSSIER, MOCK_GRAPH } from '../data/mockDossier';
import { CanonicalRole, CandidateManifest, NormalizedRequirement } from '../types/cci';

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<'job' | 'candidate' | 'pipeline' | 'dossier'>('job');
  const [currentRole, setCurrentRole] = useState<CanonicalRole>('backend');
  const [manifest, setManifest] = useState<CandidateManifest | null>(null);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);

  const handleJobComplete = (role: CanonicalRole, jdText: string, reqs: NormalizedRequirement[]) => {
    setCurrentRole(role);
    setActiveTab('candidate');
  };

  const handleCandidateSubmit = (candManifest: CandidateManifest) => {
    setManifest(candManifest);
    setIsPipelineRunning(true);
    setActiveTab('pipeline');
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
          </div>

          <div className="flex items-center gap-1 bg-slate-900 p-1 border border-slate-800 rounded-lg text-xs">
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

        {activeTab === 'job' && (
          <JobIntakeForm onComplete={handleJobComplete} />
        )}

        {activeTab === 'candidate' && (
          <CandidateIntakeForm onSubmit={handleCandidateSubmit} />
        )}

        {activeTab === 'pipeline' && (
          <PipelineTracker
            currentStageIndex={9}
            isComplete={true}
            onViewDossier={() => setActiveTab('dossier')}
          />
        )}

        {activeTab === 'dossier' && (
          <DossierView
            initialDossier={MOCK_DOSSIER}
            graph={MOCK_GRAPH}
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
