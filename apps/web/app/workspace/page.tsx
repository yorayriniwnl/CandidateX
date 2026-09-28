'use client';

import React, { useState } from 'react';
import { PlatformHeader } from '../../components/navigation/PlatformHeader';
import { StudioHeading } from '../../components/studio/StudioHeading';
import { StudioFooter } from '../../components/studio/StudioFooter';
import styles from './workspace.module.css';
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
  saveCandidateBackend,
} from '../../lib/api';
import { saveReviewToHR } from '../../components/hr/hr-data';
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
  const [comparisonCandidateIds, setComparisonCandidateIds] = useState<string[]>([]);

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

      // Auto-save candidate profile to HR at the end of the review
      try {
        const candidateId = candidate.candidate_id;
        const candidateName = candidate.full_name || 'Candidate';
        const candidateRole = dossier.role || currentRole;
        const score = dossier.rci;
        const coverage = dossier.coverage;
        const hasConflict = dossier.capability_conflicts
          ? Object.values(dossier.capability_conflicts).some(item => item.has_meaningful_conflict)
          : false;

        saveReviewToHR({
          candidateId,
          displayName: candidateName,
          email: candidate.primary_email,
          role: candidateRole,
          rci: score,
          coverage,
          hasMeaningfulConflict: hasConflict,
          manifest: candidate,
          dossier,
          graph,
        });

        saveCandidateBackend({
          id: candidateId,
          display_name: candidateName,
          primary_email: candidate.primary_email,
          role: candidateRole,
          rci: score ?? undefined,
          coverage,
          has_meaningful_conflict: hasConflict,
          has_completed_dossier: true,
          created_at: dossier.generated_at || new Date().toISOString(),
          manifest: candidate,
        }).catch(() => {});
      } catch (saveErr) {
        console.error('Failed to auto-save workspace candidate to HR', saveErr);
      }
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
      <div className="min-h-screen flex items-center justify-center bg-[#09070e] font-[family-name:var(--font-sans)]" suppressHydrationWarning>
        <div className="flex flex-col items-center gap-3" suppressHydrationWarning>
          <div className="w-8 h-8 rounded-full border-2 border-brand-500/20 border-t-brand-500 animate-spin" suppressHydrationWarning />
          <div className="text-xs text-slate-500 font-mono tracking-wide" suppressHydrationWarning>Initializing workspace...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="studio-surface">
      <PlatformHeader surface="workspace" />
      <div className="studio-page">
        <StudioHeading eyebrow="02 / THE PROTOTYPE WORKSPACE" title="A different perspective." description="Bring the people, the evidence, and the questions into one considered workspace.">
          <GlowBadge variant={isBackendOnline ? 'success' : 'warning'} size="sm">{isBackendOnline === null ? 'Checking API...' : isBackendOnline ? 'API connected' : 'API unavailable'}</GlowBadge>
          {manifest?.full_name && <button type="button" className={styles.candidatePill} onClick={() => setActiveTab('dossier')}><span>{manifest.full_name.charAt(0)}</span>{manifest.full_name}</button>}
        </StudioHeading>
        <div className={styles.shell} data-collapsed={!sidebarExpanded}>
          <aside className={styles.rail} aria-label="Workspace tools">
            <div className={styles.railHeading}><span>CX / WORKSPACE</span><span>02</span></div>
            <nav className={styles.tools} aria-label="Workspace views">
              {NAV_ITEMS.map(item => <button key={item.key} type="button" onClick={() => setActiveTab(item.key)} aria-pressed={activeTab === item.key} aria-label={`${item.label} ${item.description}`} title={sidebarExpanded ? undefined : item.label}>
                <span className={styles.toolIcon}>{item.icon}</span><span className={styles.toolCopy}><strong>{item.label}</strong><span>{item.description}</span></span><i />
              </button>)}
            </nav>
            <div className={styles.railFoot}><span className={styles.railOrb} aria-hidden="true"><i /><i /><i /></span><p>Every signal.<br /><strong>A clearer picture.</strong></p></div>
            <div className={styles.railActions}>
              <button type="button" onClick={() => setIsHowItWorksOpen(true)} aria-label="How It Works"><HelpCircle size={15} /><span>How it works</span></button>
              <button className={styles.collapseButton} type="button" onClick={() => setSidebarExpanded(value => !value)} aria-label={sidebarExpanded ? 'Collapse workspace tools' : 'Expand workspace tools'}>{sidebarExpanded ? <ChevronLeft size={15} /> : <ChevronRight size={15} />}<span>Collapse</span></button>
            </div>
          </aside>
          <main className={styles.content}>
            <SystemNotice />
            <div className={styles.prototype}><span>RESEARCH PROTOTYPE</span><p>URL and CV declarations alone produce unknown capabilities; automated acquisition is not enabled here. <a href="/research-demo">Explore the executable paper demonstration.</a></p></div>
            {loadError && <div role="alert" className={styles.error}>{loadError}</div>}
            <AnimatePresence mode="wait">
              <motion.div key={activeTab} variants={pageVariants} initial="initial" animate="animate" exit="exit" className={styles.view}>
                {activeTab === 'directory' && <CandidateDirectory onSelectCandidate={handleSelectCandidateFromDirectory} onNewCandidate={() => setActiveTab('new_eval')} isBackendOnline={isBackendOnline} initialSelectedForComparison={comparisonCandidateIds} onCompareCandidates={ids => { setComparisonCandidateIds(ids); setActiveTab('compare'); }} />}
                {activeTab === 'new_eval' && <EvaluationWizard currentRole={currentRole} pipelineStageIndex={pipelineStageIndex} isPipelineRunning={isPipelineRunning} isPipelineComplete={isPipelineComplete} onJobComplete={handleJobComplete} onCandidateSubmit={handleCandidateSubmit} onViewDossier={() => setActiveTab('dossier')} />}
                {activeTab === 'dossier' && currentDossier && currentGraph && <DossierView initialDossier={currentDossier} graph={currentGraph} candidateName={manifest?.full_name || 'Candidate'} candidatePicture={manifest?.picture} onSelectCandidate={handleSelectCandidateFromDirectory} />}
                {activeTab === 'dossier' && !currentDossier && <div className={styles.empty}><div className={styles.emptyIcon}><Award size={32} strokeWidth={1} /></div><span>THE CANDIDATE DOSSIER</span><h2>A person behind every profile.</h2><p role="status">No candidate dossier selected or available.</p><button type="button" onClick={() => setActiveTab('directory')}>Explore candidates <ChevronRight size={14} /></button></div>}
                {activeTab === 'compare' && <CandidateComparison onSelectCandidateDossier={handleSelectCandidateFromDirectory} isBackendOnline={isBackendOnline} selectedCandidateIds={comparisonCandidateIds} onSelectedIdsChange={setComparisonCandidateIds} />}
                {activeTab === 'research' && <ResearchTheoremsExplorer isBackendOnline={isBackendOnline} />}
              </motion.div>
            </AnimatePresence>
          </main>
        </div>
        <StudioFooter />
      </div>
      <HowItWorksModal isOpen={isHowItWorksOpen} onClose={() => setIsHowItWorksOpen(false)} />
    </div>
  );
}
