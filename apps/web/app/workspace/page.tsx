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
  Zap,
} from 'lucide-react';
import { SystemNotice } from '../../components/SystemNotice';
import { EvaluationWizard } from '../../components/EvaluationWizard';
import { CandidateDirectory } from '../../components/CandidateDirectory';
import { CandidateComparison } from '../../components/CandidateComparison';
import { ResearchTheoremsExplorer } from '../../components/ResearchTheoremsExplorer';
import { DossierView } from '../../components/dossier/DossierView';
import { HowItWorksModal } from '../../components/HowItWorksModal';
import { GlowBadge } from '../../components/ui/GlowBadge';

import {
  checkBackendHealth,
  triggerPipelineRun,
  fetchCandidateDossier,
  fetchCandidateGraph,
} from '../../lib/api';
import { CanonicalRole, CandidateManifest, NormalizedRequirement, Dossier, CEGGraph } from '../../types/cci';

type TabKey = 'directory' | 'new_eval' | 'dossier' | 'compare' | 'research';

const NAV_ITEMS: { key: TabKey; label: string; icon: React.ReactNode; description: string }[] = [
  { key: 'directory', label: 'Candidates', icon: <Users className="w-5 h-5" />, description: 'Browse & search' },
  { key: 'new_eval', label: 'New Evaluation', icon: <Play className="w-5 h-5" />, description: 'Run pipeline' },
  { key: 'dossier', label: 'Dossier', icon: <Award className="w-5 h-5" />, description: 'Deep analysis' },
  { key: 'compare', label: 'Compare', icon: <GitCompare className="w-5 h-5" />, description: 'Side by side' },
  { key: 'research', label: 'Methodology', icon: <GraduationCap className="w-5 h-5" />, description: 'Math & proofs' },
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
  const [manifest, setManifest] = useState<CandidateManifest | null>(null);
  const [jdText, setJdText] = useState('');
  const [loadError, setLoadError] = useState('');
  const requestSequence = React.useRef(0);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [pipelineStageIndex, setPipelineStageIndex] = useState(0);
  const [isPipelineComplete, setIsPipelineComplete] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [currentDossier, setCurrentDossier] = useState<Dossier | null>(null);
  const [currentGraph, setCurrentGraph] = useState<CEGGraph | null>(null);
  const [isHowItWorksOpen, setIsHowItWorksOpen] = useState(false);
  const [comparisonCandidateIds, setComparisonCandidateIds] = useState<string[]>([
    '11111111-1111-1111-1111-111111111111',
    '77777777-7777-7777-7777-777777777777',
  ]);

  const [mounted, setMounted] = useState(false);

  React.useEffect(() => {
    setMounted(true);
    checkBackendHealth().then((online) => setIsBackendOnline(online));
  }, []);

  const handleJobComplete = (role: CanonicalRole, text: string, _requirements: NormalizedRequirement[]) => {
    setCurrentRole(role);
    setJdText(text);
  };

  const handleCandidateSubmit = async (candidate: CandidateManifest) => {
    const sequence = ++requestSequence.current;
    setManifest(candidate); setCurrentDossier(null); setCurrentGraph(null); setLoadError('');
    setIsPipelineRunning(true); setIsPipelineComplete(false); setPipelineStageIndex(0);
    try {
      const run = await triggerPipelineRun(candidate.candidate_id, currentRole, candidate, jdText);
      if (run.status !== 'completed') throw new Error(run.error || 'Analysis did not complete.');
      const [dossier, graph] = await Promise.all([fetchCandidateDossier(candidate.candidate_id), fetchCandidateGraph(candidate.candidate_id)]);
      if (sequence !== requestSequence.current) return;
      if (dossier.candidate_id !== candidate.candidate_id || graph.analysis_run_id !== dossier.analysis_run_id) throw new Error('Result identity mismatch.');
      setCurrentDossier(dossier); setCurrentGraph(graph); setPipelineStageIndex(9); setIsPipelineComplete(true);
    } catch (error) {
      if (sequence === requestSequence.current) setLoadError(error instanceof Error ? error.message : 'Analysis unavailable. No sample dossier substituted.');
    } finally { if (sequence === requestSequence.current) setIsPipelineRunning(false); }
  };

  const handleSelectCandidateFromDirectory = async (candidateId: string, name: string) => {
    const sequence = ++requestSequence.current;
    setCurrentDossier(null); setCurrentGraph(null); setManifest(null); setLoadError(''); setActiveTab('dossier');
    try {
      const [dossier, graph] = await Promise.all([fetchCandidateDossier(candidateId), fetchCandidateGraph(candidateId)]);
      if (sequence !== requestSequence.current) return;
      if (dossier.candidate_id !== candidateId || graph.candidate_id !== candidateId || graph.analysis_run_id !== dossier.analysis_run_id) throw new Error('Result identity mismatch.');
      setCurrentDossier(dossier); setCurrentGraph(graph);
      setManifest({ candidate_id: candidateId, full_name: name, primary_email: '', github_usernames: [], github_repositories: [], deployment_urls: [], portfolio_urls: [], declared_skills: [], extraction_metadata: {} });
    } catch (error) {
      if (sequence === requestSequence.current) setLoadError(error instanceof Error ? error.message : 'Dossier unavailable.');
    }
  };

  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#030712] font-[family-name:var(--font-sans)]" suppressHydrationWarning>
        <div className="flex flex-col items-center gap-3" suppressHydrationWarning>
          <div className="w-8 h-8 rounded-full border-2 border-brand-500/20 border-t-brand-500 animate-spin" suppressHydrationWarning />
          <div className="text-xs text-slate-500 font-mono tracking-wide" suppressHydrationWarning>Initializing workspace...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex font-[family-name:var(--font-sans)]">
      {/* ============================================================
          Sidebar Navigation
          ============================================================ */}
      <aside
        className={`
          fixed top-0 left-0 h-screen z-40
          glass-strong border-r border-white/[0.06]
          flex flex-col transition-all duration-300 ease-in-out
          ${sidebarExpanded ? 'w-[220px]' : 'w-[68px]'}
        `}
      >
        {/* Logo */}
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
              <div className="text-[10px] text-slate-500 font-mono whitespace-nowrap">v1.0.0</div>
            </motion.div>
          )}
        </div>

        {/* Nav Items */}
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
                {/* Active indicator bar */}
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

                {/* Tooltip for collapsed state */}
                {!sidebarExpanded && (
                  <div className="absolute left-full ml-2 px-2.5 py-1.5 glass-strong rounded-lg text-xs text-white whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-xl">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {/* Bottom actions */}
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

      {/* ============================================================
          Main Content Area
          ============================================================ */}
      <div
        className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${
          sidebarExpanded ? 'ml-[220px]' : 'ml-[68px]'
        }`}
      >
        {/* Top Command Bar */}
        <header className="sticky top-0 z-30 glass-strong border-b border-white/[0.04]">
          <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
            <div className="flex items-center gap-3">
              {/* Search trigger */}
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06] text-slate-500 text-sm cursor-default">
                <Search className="w-3.5 h-3.5" />
                <span className="text-xs">Search candidates...</span>
                <kbd className="ml-4 px-1.5 py-0.5 rounded bg-white/[0.06] text-[10px] font-mono text-slate-500 border border-white/[0.08]">
                  Ctrl+K
                </kbd>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Active candidate pill */}
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

              {/* Backend status */}
              <GlowBadge
                variant={isBackendOnline === null ? 'neutral' : isBackendOnline ? 'success' : 'warning'}
                size="sm"
                pulse={isBackendOnline === true}
              >
                {isBackendOnline === null ? 'Checking API...' : isBackendOnline ? 'API connected' : 'API unavailable'}
              </GlowBadge>
            </div>
          </div>
        </header>

        {/* Page Content with Transitions */}
        <main className="flex-1 max-w-7xl mx-auto px-6 py-6 w-full">
          <SystemNotice />
          <div className="mb-5 rounded-xl border border-indigo-400/30 bg-indigo-950/40 p-4 text-sm text-indigo-100">
            Prototype workspace. URL and CV declarations alone produce unknown capabilities; automated acquisition is not enabled here.
            {' '}<a href="/research-demo" className="underline">Open the executable paper demonstration</a>.
          </div>
          {loadError && <div role="alert" className="mb-5 rounded-xl border border-red-400/40 p-4 text-red-200">{loadError}</div>}

          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
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
                  onJobComplete={handleJobComplete}
                  onCandidateSubmit={handleCandidateSubmit}
                  onViewDossier={() => setActiveTab('dossier')}
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

              {activeTab === 'dossier' && !currentDossier && <p role="status" className="p-6 text-slate-300">No candidate dossier selected or available.</p>}
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

        {/* Footer */}
        <footer className="border-t border-white/[0.04] py-4 text-center text-xs text-slate-600">
          <span className="text-gradient-brand font-semibold">CandidateX</span>
          {' '}&mdash; AI-Powered Capability Intelligence for Technical Hiring
        </footer>
      </div>

      {/* How It Works Modal */}
      <HowItWorksModal
        isOpen={isHowItWorksOpen}
        onClose={() => setIsHowItWorksOpen(false)}
      />
    </div>
  );
}
