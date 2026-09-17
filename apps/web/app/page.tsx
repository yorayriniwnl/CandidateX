'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence, Variants } from 'framer-motion';
import {
  Users,
  Play,
  Award,
  GitCompare,
  GraduationCap,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Search,
  Sparkles,
  AlertTriangle,
} from 'lucide-react';
import { SystemNotice } from '../components/SystemNotice';
import { EvaluationWizard } from '../components/EvaluationWizard';
import { CandidateDirectory } from '../components/CandidateDirectory';
import { CandidateComparison } from '../components/CandidateComparison';
import { ResearchTheoremsExplorer } from '../components/ResearchTheoremsExplorer';
import { DossierView } from '../components/dossier/DossierView';
import { HowItWorksModal } from '../components/HowItWorksModal';
import { GlowBadge } from '../components/ui/GlowBadge';
import {
  checkBackendHealth,
  triggerPipelineRun,
  fetchCandidateDossier,
  fetchCandidateGraph,
} from '../lib/api';
import { CanonicalRole, CandidateManifest, NormalizedRequirement, Dossier, CEGGraph } from '../types/cci';

type TabKey = 'directory' | 'new_eval' | 'dossier' | 'compare' | 'research';

const NAV_ITEMS: { key: TabKey; label: string; icon: React.ReactNode; description: string }[] = [
  { key: 'directory', label: 'Candidates', icon: <Users className="w-5 h-5" />, description: 'Browse verified runs' },
  { key: 'new_eval', label: 'New Evaluation', icon: <Play className="w-5 h-5" />, description: 'Run pipeline' },
  { key: 'dossier', label: 'Dossier', icon: <Award className="w-5 h-5" />, description: 'Inspect evidence' },
  { key: 'compare', label: 'Compare', icon: <GitCompare className="w-5 h-5" />, description: 'Side by side' },
  { key: 'research', label: 'Methodology', icon: <GraduationCap className="w-5 h-5" />, description: 'Math & simulation' },
];

const pageVariants: Variants = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.3, ease: 'easeOut' } },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15 } },
};

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<TabKey>('directory');
  const [sidebarExpanded, setSidebarExpanded] = useState(true);
  const [currentRole, setCurrentRole] = useState<CanonicalRole>('backend');
  const [currentJdText, setCurrentJdText] = useState('');
  const [manifest, setManifest] = useState<CandidateManifest | null>(null);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pipelineStageIndex, setPipelineStageIndex] = useState(0);
  const [isPipelineComplete, setIsPipelineComplete] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [currentDossier, setCurrentDossier] = useState<Dossier | null>(null);
  const [currentGraph, setCurrentGraph] = useState<CEGGraph | null>(null);
  const [isHowItWorksOpen, setIsHowItWorksOpen] = useState(false);
  const [comparisonCandidateIds, setComparisonCandidateIds] = useState<string[]>([]);

  React.useEffect(() => {
    checkBackendHealth().then((online) => setIsBackendOnline(online));
  }, []);

  const handleJobComplete = (role: CanonicalRole, jdText: string, _reqs: NormalizedRequirement[]) => {
    setCurrentRole(role);
    setCurrentJdText(jdText);
  };

  const handleCandidateSubmit = async (candManifest: CandidateManifest) => {
    setManifest(candManifest);
    setCurrentDossier(null);
    setCurrentGraph(null);
    setPipelineError(null);
    setPipelineStageIndex(0);
    setIsPipelineComplete(false);

    if (!isBackendOnline) {
      setPipelineError('The analysis backend is unavailable. No dossier or score was generated.');
      return;
    }

    setIsPipelineRunning(true);
    try {
      const runRes = await triggerPipelineRun(
        candManifest.candidate_id,
        currentRole,
        candManifest,
        currentJdText,
      );

      if (runRes.status !== 'completed' || !runRes.dossier_id) {
        throw new Error(runRes.error || `Pipeline ended with status: ${runRes.status}`);
      }

      const [liveDossier, liveGraph] = await Promise.all([
        fetchCandidateDossier(candManifest.candidate_id),
        fetchCandidateGraph(candManifest.candidate_id),
      ]);

      setCurrentDossier(liveDossier);
      setCurrentGraph(liveGraph);
      setPipelineStageIndex(9);
      setIsPipelineComplete(true);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown pipeline failure';
      setPipelineError(`Analysis failed. No mock result was substituted. ${message}`);
      setCurrentDossier(null);
      setCurrentGraph(null);
      setIsPipelineComplete(false);
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const handleSelectCandidateFromDirectory = async (candidateId: string, name: string) => {
    setPipelineError(null);
    setCurrentDossier(null);
    setCurrentGraph(null);
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

    if (!isBackendOnline) {
      setPipelineError('The analysis backend is unavailable, so this dossier cannot be loaded.');
      setActiveTab('dossier');
      return;
    }

    try {
      const [liveDossier, liveGraph] = await Promise.all([
        fetchCandidateDossier(candidateId),
        fetchCandidateGraph(candidateId),
      ]);
      setCurrentDossier(liveDossier);
      setCurrentGraph(liveGraph);
      setActiveTab('dossier');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown dossier load failure';
      setPipelineError(`Live dossier unavailable. No sample result was substituted. ${message}`);
      setActiveTab('dossier');
    }
  };

  return (
    <div className="min-h-screen flex font-[family-name:var(--font-sans)]">
      <aside
        className={`
          fixed top-0 left-0 h-screen z-40
          glass-strong border-r border-white/[0.06]
          flex flex-col transition-all duration-300 ease-in-out
          ${sidebarExpanded ? 'w-[220px]' : 'w-[68px]'}
        `}
      >
        <div className="p-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-violet-500 flex items-center justify-center font-bold text-white text-sm shadow-lg shadow-brand-500/25 shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          {sidebarExpanded && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="overflow-hidden"
            >
              <div className="text-sm font-bold text-white tracking-tight whitespace-nowrap">CandidateX</div>
              <div className="text-[10px] text-slate-500 font-mono whitespace-nowrap">research prototype</div>
            </motion.div>
          )}
        </div>

        <nav className="flex-1 px-2.5 py-2 space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive = activeTab === item.key;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => setActiveTab(item.key)}
                className={`
                  w-full flex items-center gap-3 rounded-xl transition-all duration-200 group relative
                  ${sidebarExpanded ? 'px-3 py-2.5' : 'px-0 py-2.5 justify-center'}
                  ${isActive
                    ? 'bg-brand-500/15 text-white shadow-glow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]'
                  }
                `}
              >
                {isActive && (
                  <motion.div
                    layoutId="sidebar-indicator"
                    className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-brand-400 rounded-r-full shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                    transition={{ type: 'spring', stiffness: 380, damping: 30 }}
                  />
                )}
                <span className={`shrink-0 ${isActive ? 'text-brand-400' : ''}`}>
                  {item.icon}
                </span>
                {sidebarExpanded && (
                  <div className="text-left min-w-0">
                    <div className="text-sm font-medium truncate">{item.label}</div>
                    <div className="text-[10px] text-slate-500 truncate">{item.description}</div>
                  </div>
                )}
                {!sidebarExpanded && (
                  <div className="absolute left-full ml-2 px-2.5 py-1.5 glass-strong rounded-lg text-xs text-white whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-xl">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        <div className="p-2.5 space-y-1 border-t border-white/[0.04]">
          <button
            type="button"
            onClick={() => setIsHowItWorksOpen(true)}
            className={`
              w-full flex items-center gap-3 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-white/[0.04] transition-all duration-200
              ${sidebarExpanded ? 'px-3 py-2.5' : 'px-0 py-2.5 justify-center'}
            `}
          >
            <HelpCircle className="w-5 h-5 shrink-0" />
            {sidebarExpanded && <span className="text-sm font-medium">How It Works</span>}
          </button>

          <button
            type="button"
            onClick={() => setSidebarExpanded(!sidebarExpanded)}
            className={`
              w-full flex items-center gap-3 rounded-xl text-slate-500 hover:text-slate-300 hover:bg-white/[0.04] transition-all duration-200
              ${sidebarExpanded ? 'px-3 py-2.5' : 'px-0 py-2.5 justify-center'}
            `}
          >
            {sidebarExpanded ? <ChevronLeft className="w-5 h-5 shrink-0" /> : <ChevronRight className="w-5 h-5 shrink-0" />}
            {sidebarExpanded && <span className="text-sm font-medium">Collapse</span>}
          </button>
        </div>
      </aside>

      <div
        className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${
          sidebarExpanded ? 'ml-[220px]' : 'ml-[68px]'
        }`}
      >
        <header className="sticky top-0 z-30 glass-strong border-b border-white/[0.04]">
          <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-500 text-sm cursor-default">
                <Search className="w-3.5 h-3.5" />
                <span className="text-xs">Candidate evidence workspace</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {manifest?.full_name && (
                <button
                  type="button"
                  onClick={() => setActiveTab('dossier')}
                  className="flex items-center gap-2 px-3 py-1.5 glass rounded-full text-xs transition-all hover:bg-white/[0.06] group"
                >
                  <div className="w-5 h-5 rounded-full bg-gradient-to-br from-brand-400 to-violet-400 flex items-center justify-center text-[10px] font-bold text-white">
                    {manifest.full_name.charAt(0)}
                  </div>
                  <span className="text-slate-400 group-hover:text-slate-200 transition-colors">
                    {manifest.full_name}
                  </span>
                </button>
              )}

              <GlowBadge
                variant={isBackendOnline === null ? 'neutral' : isBackendOnline ? 'success' : 'warning'}
                size="sm"
                pulse={isBackendOnline === true}
              >
                {isBackendOnline === null ? 'Probing API' : isBackendOnline ? 'Backend live' : 'Backend offline'}
              </GlowBadge>
            </div>
          </div>
        </header>

        <main className="flex-1 max-w-7xl mx-auto px-6 py-6 w-full">
          <SystemNotice />

          {pipelineError && (
            <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100 flex items-start gap-3">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-400" />
              <div>
                <div className="font-semibold text-amber-300">Evidence unavailable</div>
                <div className="mt-1 text-amber-100/80">{pipelineError}</div>
              </div>
            </div>
          )}

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className="mt-5"
            >
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
                  isBackendOnline={isBackendOnline}
                  onJobComplete={handleJobComplete}
                  onCandidateSubmit={handleCandidateSubmit}
                  onViewDossier={() => {
                    if (currentDossier && currentGraph) setActiveTab('dossier');
                  }}
                />
              )}

              {activeTab === 'dossier' && currentDossier && currentGraph && (
                <DossierView
                  initialDossier={currentDossier}
                  graph={currentGraph}
                  candidateName={manifest?.full_name || 'Candidate'}
                  onSelectCandidate={handleSelectCandidateFromDirectory}
                />
              )}

              {activeTab === 'dossier' && (!currentDossier || !currentGraph) && (
                <div className="glass-strong border border-white/[0.06] rounded-2xl p-10 text-center">
                  <Award className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                  <h2 className="text-lg font-semibold text-white">No verified dossier loaded</h2>
                  <p className="text-sm text-slate-400 mt-2 max-w-xl mx-auto">
                    CandidateX only renders a dossier after the backend returns the analyzed evidence and graph. Backend failure does not substitute sample scores.
                  </p>
                  <button
                    type="button"
                    onClick={() => setActiveTab('new_eval')}
                    className="mt-5 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold transition-colors"
                  >
                    Start an evaluation
                  </button>
                </div>
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
            </motion.div>
          </AnimatePresence>
        </main>

        <footer className="border-t border-white/[0.04] py-4 text-center text-xs text-slate-600">
          <span className="text-gradient-brand font-semibold">CandidateX</span>
          {' '}· evidence-grounded decision support for technical interviewers
        </footer>
      </div>

      <HowItWorksModal
        isOpen={isHowItWorksOpen}
        onClose={() => setIsHowItWorksOpen(false)}
      />
    </div>
  );
}
