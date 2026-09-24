'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User,
  ShieldCheck,
  FileText,
  GraduationCap,
  Cpu,
  FolderGit2,
  Briefcase,
  Award,
  BookOpen,
  Code2,
  TrendingUp,
  AlertTriangle,
  Clock,
  CheckSquare,
  Activity,
  MessageSquare,
  Network,
  GitFork,
  HelpCircle,
  FileCode,
  Download,
  Search,
  ExternalLink,
  ChevronRight,
  Layers,
  ArrowRight,
  CheckCircle2,
  XCircle,
  HelpCircle as QuestionIcon,
  Info,
  Copy,
  Check,
} from 'lucide-react';
import {
  CapabilityKey,
  CanonicalRole,
  Dossier,
  CEGGraph,
  ClaimCorroboration,
  ProjectEntity,
  CredentialEntity,
  PublicationEntity,
  CodingProfileEntity,
  QuantifiedClaim,
  TimelineEvent,
  TimelineInconsistency,
  AcademicRecord,
  TraceLink,
} from '../../types/cci';
import { RadialGauge } from '../ui/RadialGauge';
import { GlowBadge } from '../ui/GlowBadge';
import { GlassCard } from '../ui/GlassCard';
import { GlassButton } from '../ui/GlassButton';
import { GlassModal } from '../ui/GlassModal';
import { GraphViewer } from './GraphViewer';

export type EvidenceExplorerSection =
  | 'overview'
  | 'coverage'
  | 'claims_ledger'
  | 'academic_records'
  | 'skills_evidence'
  | 'project_dossiers'
  | 'experience'
  | 'credentials'
  | 'publications'
  | 'coding_profiles'
  | 'quantified_claims'
  | 'contradictions'
  | 'timeline'
  | 'role_requirements'
  | 'capability_signals'
  | 'interview_plan'
  | 'source_explorer'
  | 'evidence_graph'
  | 'methodology'
  | 'limitations'
  | 'exports';

interface SectionMeta {
  key: EvidenceExplorerSection;
  label: string;
  category: 'Overview' | 'Profile' | 'Projects' | 'Evaluation' | 'Audit';
  icon: React.ReactNode;
  badge?: string | number;
}

const SECTIONS: SectionMeta[] = [
  // 1. Overview
  { key: 'overview', label: 'Candidate Overview', category: 'Overview', icon: <User className="w-4 h-4" /> },
  { key: 'coverage', label: 'Evidence Coverage', category: 'Overview', icon: <ShieldCheck className="w-4 h-4" /> },
  { key: 'claims_ledger', label: 'Claims Ledger', category: 'Overview', icon: <FileText className="w-4 h-4" /> },

  // 2. Profile
  { key: 'academic_records', label: 'Academic Records', category: 'Profile', icon: <GraduationCap className="w-4 h-4" /> },
  { key: 'skills_evidence', label: 'Skills Evidence', category: 'Profile', icon: <Cpu className="w-4 h-4" /> },
  { key: 'experience', label: 'Experience', category: 'Profile', icon: <Briefcase className="w-4 h-4" /> },
  { key: 'credentials', label: 'Credentials', category: 'Profile', icon: <Award className="w-4 h-4" /> },
  { key: 'publications', label: 'Publications', category: 'Profile', icon: <BookOpen className="w-4 h-4" /> },
  { key: 'coding_profiles', label: 'Coding Profiles', category: 'Profile', icon: <Code2 className="w-4 h-4" /> },

  // 3. Projects & Claims
  { key: 'project_dossiers', label: 'Project Dossiers', category: 'Projects', icon: <FolderGit2 className="w-4 h-4" /> },
  { key: 'quantified_claims', label: 'Quantified Claims', category: 'Projects', icon: <TrendingUp className="w-4 h-4" /> },
  { key: 'contradictions', label: 'Contradictions', category: 'Projects', icon: <AlertTriangle className="w-4 h-4" /> },
  { key: 'timeline', label: 'Timeline', category: 'Projects', icon: <Clock className="w-4 h-4" /> },

  // 4. Role & Evaluation
  { key: 'role_requirements', label: 'Role Requirements', category: 'Evaluation', icon: <CheckSquare className="w-4 h-4" /> },
  { key: 'capability_signals', label: 'Capability Signals', category: 'Evaluation', icon: <Activity className="w-4 h-4" /> },
  { key: 'interview_plan', label: 'Interview Plan', category: 'Evaluation', icon: <MessageSquare className="w-4 h-4" /> },

  // 5. Sources & Audit
  { key: 'source_explorer', label: 'Source Explorer', category: 'Audit', icon: <Network className="w-4 h-4" /> },
  { key: 'evidence_graph', label: 'Evidence Graph', category: 'Audit', icon: <GitFork className="w-4 h-4" /> },
  { key: 'methodology', label: 'Methodology', category: 'Audit', icon: <HelpCircle className="w-4 h-4" /> },
  { key: 'limitations', label: 'Limitations', category: 'Audit', icon: <FileCode className="w-4 h-4" /> },
  { key: 'exports', label: 'Exports', category: 'Audit', icon: <Download className="w-4 h-4" /> },
];

export interface EvidenceExplorerProps {
  dossier: Dossier;
  graph: CEGGraph;
  candidateName?: string;
  onInspectEvidence?: (evidenceId: string) => void;
  onOpenScorecard?: () => void;
  onOpenWeightsModal?: () => void;
}

export const EvidenceExplorer: React.FC<EvidenceExplorerProps> = ({
  dossier,
  graph,
  candidateName = 'Candidate Evaluation Snapshot',
  onInspectEvidence,
  onOpenScorecard,
  onOpenWeightsModal,
}) => {
  const [activeSection, setActiveSection] = useState<EvidenceExplorerSection>('overview');
  const [searchFilter, setSearchFilter] = useState('');
  const [activeTraceClaim, setActiveTraceClaim] = useState<ClaimCorroboration | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  // Derive counts and records
  const claims = dossier.claims_corroboration || [];
  const projects = dossier.project_entities || [];
  const credentials = dossier.credentials || [];
  const publications = dossier.publications || [];
  const codingProfiles = dossier.coding_profiles || [];
  const quantifiedClaims = dossier.quantified_claims || [];
  const academicRecords = dossier.academic_records || [];
  const timelineEvents = dossier.timeline?.events || [];
  const timelineInconsistencies = dossier.timeline?.inconsistencies || [];
  const requirements = dossier.role_requirements || [];
  const capabilities = Object.values(dossier.capability_estimates || {});
  const interviewProbes = dossier.interview_probes || [];
  const interviewQuestions = dossier.interview_questions || [];

  return (
    <div className="flex flex-col lg:flex-row gap-6 min-h-[750px] w-full">
      {/* 21-View Section Navigation Sidebar */}
      <aside className="w-full lg:w-72 flex-shrink-0 flex flex-col gap-4">
        <GlassCard className="p-3.5 space-y-3">
          <div className="px-2 py-1">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Evidence Explorer
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              21 Facets of Grounded Intelligence
            </p>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Filter views..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full bg-slate-900/60 border border-slate-700/50 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500/60"
            />
          </div>

          <div className="space-y-4 max-h-[640px] overflow-y-auto pr-1">
            {(['Overview', 'Profile', 'Projects', 'Evaluation', 'Audit'] as const).map((cat) => {
              const items = SECTIONS.filter(
                (s) =>
                  s.category === cat &&
                  s.label.toLowerCase().includes(searchFilter.toLowerCase())
              );
              if (items.length === 0) return null;

              return (
                <div key={cat} className="space-y-1">
                  <div className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                    {cat}
                  </div>
                  {items.map((sec) => {
                    const isActive = activeSection === sec.key;
                    return (
                      <button
                        key={sec.key}
                        onClick={() => setActiveSection(sec.key)}
                        className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                          isActive
                            ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/40 shadow-sm shadow-indigo-500/10'
                            : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
                        }`}
                      >
                        <div className="flex items-center gap-2 truncate">
                          <span className={isActive ? 'text-indigo-400' : 'text-slate-500'}>
                            {sec.icon}
                          </span>
                          <span className="truncate">{sec.label}</span>
                        </div>
                        {sec.key === 'claims_ledger' && claims.length > 0 && (
                          <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 text-slate-400 rounded-full font-mono">
                            {claims.length}
                          </span>
                        )}
                        {sec.key === 'project_dossiers' && projects.length > 0 && (
                          <span className="text-[10px] px-1.5 py-0.2 bg-slate-800 text-slate-400 rounded-full font-mono">
                            {projects.length}
                          </span>
                        )}
                        {sec.key === 'timeline' && timelineInconsistencies.length > 0 && (
                          <span className="text-[10px] px-1.5 py-0.2 bg-amber-500/20 text-amber-300 rounded-full font-mono">
                            {timelineInconsistencies.length}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </div>
        </GlassCard>

        {/* Decision Support Disclaimer Guard */}
        <div className="p-3 bg-amber-950/20 border border-amber-800/30 rounded-xl text-[11px] text-amber-200/80 leading-relaxed">
          <div className="flex items-center gap-1.5 font-semibold text-amber-300 mb-1">
            <Info className="w-3.5 h-3.5 flex-shrink-0" />
            Decision Support Policy
          </div>
          CandidateX does not decide whether to hire a person. Scores represent bounded,
          observed artifact patterns; missing evidence remains unknown.
        </div>
      </aside>

      {/* Main View Area */}
      <main className="flex-1 min-w-0">
        <GlassCard className="p-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeSection}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.18 }}
              className="space-y-6"
            >
              {/* 1. Candidate Overview */}
              {activeSection === 'overview' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <User className="w-5 h-5 text-indigo-400" />
                      Candidate Overview
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Target role alignment and verifiable evidence profile.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl">
                      <div className="text-xs text-slate-500 uppercase font-semibold">Candidate</div>
                      <div className="text-sm font-bold text-slate-100 mt-1">{candidateName}</div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5 truncate">
                        ID: {dossier.candidate_id}
                      </div>
                    </div>
                    <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl">
                      <div className="text-xs text-slate-500 uppercase font-semibold">Target Role</div>
                      <div className="text-sm font-bold text-indigo-300 mt-1 capitalize">
                        {dossier.role} Engineer
                      </div>
                      <div className="text-[11px] text-slate-400 mt-0.5">
                        Run: {dossier.analysis_run_id?.slice(0, 8)}...
                      </div>
                    </div>
                    <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl flex items-center justify-between">
                      <div>
                        <div className="text-xs text-slate-500 uppercase font-semibold">Observed Index (RCI)</div>
                        <div className="text-sm font-bold text-emerald-400 mt-1">
                          {dossier.rci !== null ? (dossier.rci * 100).toFixed(1) : 'Unknown'}%
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          Coverage: {(dossier.coverage * 100).toFixed(1)}%
                        </div>
                      </div>
                      <RadialGauge value={(dossier.coverage || 0) * 100} size={54} strokeWidth={5} />
                    </div>
                  </div>

                  {dossier.is_insufficient_evidence && (
                    <div className="p-4 bg-amber-950/20 border border-amber-800/40 rounded-xl text-xs text-amber-200 flex items-start gap-2.5">
                      <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-amber-300">Insufficient Evidence Coverage:</span>
                        {' '}Total observed coverage ({(dossier.coverage * 100).toFixed(1)}%) is below the configured threshold.
                        The RCI is uncalibrated and should not be used as a primary evaluation signal.
                      </div>
                    </div>
                  )}

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                    <button
                      onClick={() => setActiveSection('claims_ledger')}
                      className="p-3 bg-slate-900/40 border border-slate-800 hover:border-slate-700 rounded-lg text-left transition-all"
                    >
                      <div className="text-[11px] text-slate-400">Claims Ledger</div>
                      <div className="text-base font-bold text-white mt-1">{claims.length} claims</div>
                    </button>
                    <button
                      onClick={() => setActiveSection('project_dossiers')}
                      className="p-3 bg-slate-900/40 border border-slate-800 hover:border-slate-700 rounded-lg text-left transition-all"
                    >
                      <div className="text-[11px] text-slate-400">Project Dossiers</div>
                      <div className="text-base font-bold text-white mt-1">{projects.length} entities</div>
                    </button>
                    <button
                      onClick={() => setActiveSection('timeline')}
                      className="p-3 bg-slate-900/40 border border-slate-800 hover:border-slate-700 rounded-lg text-left transition-all"
                    >
                      <div className="text-[11px] text-slate-400">Timeline Inconsistencies</div>
                      <div className="text-base font-bold text-amber-300 mt-1">
                        {timelineInconsistencies.length} flagged
                      </div>
                    </button>
                    <button
                      onClick={() => setActiveSection('interview_plan')}
                      className="p-3 bg-slate-900/40 border border-slate-800 hover:border-slate-700 rounded-lg text-left transition-all"
                    >
                      <div className="text-[11px] text-slate-400">Interview Inquiries</div>
                      <div className="text-base font-bold text-white mt-1">{interviewQuestions.length} probes</div>
                    </button>
                  </div>
                </div>
              )}

              {/* 2. Evidence Coverage */}
              {activeSection === 'coverage' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <ShieldCheck className="w-5 h-5 text-indigo-400" />
                      Evidence Coverage Integrity
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Independent observations versus missing data across all 12 evaluated capabilities.
                    </p>
                  </div>

                  <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold text-slate-300">Overall Role Coverage</span>
                      <span className="font-mono text-emerald-400 font-bold">
                        {(dossier.coverage * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full transition-all duration-500"
                        style={{ width: `${Math.min(100, (dossier.coverage || 0) * 100)}%` }}
                      />
                    </div>
                    <p className="text-[11px] text-slate-500 leading-relaxed">
                      Core Invariant: Missing evidence remains unknown. No evidence does not equal no skill.
                      CandidateX strictly treats missing observations as unknown rather than assigning zero skill.
                    </p>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left border-collapse">
                      <thead>
                        <tr className="border-b border-slate-800 text-slate-400">
                          <th className="py-2.5 px-3">Capability</th>
                          <th className="py-2.5 px-3">Coverage (Cov_k)</th>
                          <th className="py-2.5 px-3">Raw Hits</th>
                          <th className="py-2.5 px-3">Effective Count (n_eff)</th>
                          <th className="py-2.5 px-3">Estimate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                        {capabilities.map((cap) => (
                          <tr key={cap.capability_key} className="hover:bg-slate-900/30">
                            <td className="py-2 px-3 font-sans font-medium text-slate-200">
                              {cap.capability_key.replace(/_/g, ' ')}
                            </td>
                            <td className="py-2 px-3 text-emerald-400">
                              {(cap.coverage_k * 100).toFixed(1)}%
                            </td>
                            <td className="py-2 px-3 text-slate-300">{cap.raw_evidence_count}</td>
                            <td className="py-2 px-3 text-slate-300">{cap.effective_evidence_count?.toFixed(1) || '0.0'}</td>
                            <td className="py-2 px-3 text-slate-200 font-semibold">
                              {cap.estimate !== null ? `${(cap.estimate * 100).toFixed(1)}%` : 'Unknown'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* 3. Claims Ledger with Click-through Provenance Trace */}
              {activeSection === 'claims_ledger' && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <FileText className="w-5 h-5 text-indigo-400" />
                        Claims Ledger
                      </h3>
                      <p className="text-xs text-slate-400 mt-1">
                        Self-reported CV statements cross-referenced against technical evidence.
                      </p>
                    </div>
                    <span className="text-xs font-mono px-2.5 py-1 bg-slate-800 text-slate-300 rounded-lg">
                      {claims.length} claims registered
                    </span>
                  </div>

                  <div className="p-3 bg-indigo-950/20 border border-indigo-800/30 rounded-xl text-xs text-indigo-200/90 flex items-center gap-2">
                    <Info className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                    <span>
                      Click <strong className="text-indigo-300">"Trace Evidence"</strong> on any claim to inspect the
                      5-hop drilldown: <span className="font-mono text-[11px]">Claim → Evidence → Source → Artifact → Revision</span>.
                    </span>
                  </div>

                  <div className="space-y-3">
                    {claims.map((claim) => (
                      <div
                        key={claim.claim_id}
                        className="p-4 bg-slate-900/40 border border-slate-800/80 hover:border-slate-700/80 rounded-xl transition-all"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                          <div className="space-y-1.5 flex-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span
                                className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                                  claim.status === 'corroborated'
                                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                    : claim.status === 'partial'
                                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                    : claim.status === 'contradicted'
                                    ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                                    : 'bg-slate-800 text-slate-400 border border-slate-700'
                                }`}
                              >
                                {claim.status.replace(/_/g, ' ')}
                              </span>
                              <span className="text-[11px] text-slate-400 font-medium">
                                Capability: <span className="text-slate-200">{claim.target_capability}</span>
                              </span>
                              <span className="text-[11px] font-mono text-slate-400">
                                Confidence: {(claim.confidence * 100).toFixed(0)}%
                              </span>
                            </div>
                            <div className="text-xs text-slate-100 font-medium leading-relaxed">
                              "{claim.claim_text}"
                            </div>
                            <div className="text-[11px] text-slate-400">
                              {claim.explanation}
                            </div>
                          </div>

                          <button
                            onClick={() => setActiveTraceClaim(claim)}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 rounded-lg text-xs font-medium transition-all flex-shrink-0"
                          >
                            <span>Trace Evidence</span>
                            <ArrowRight className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 4. Academic Records */}
              {activeSection === 'academic_records' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <GraduationCap className="w-5 h-5 text-indigo-400" />
                      Academic Records
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Extracted education history, degree declarations, and registrar verification caveats.
                    </p>
                  </div>

                  <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-400 leading-relaxed">
                    Note: CandidateX evaluates technical artifacts. No institution, registrar, transcript, or grade
                    verification is implied without certified primary-source documentation.
                  </div>

                  {academicRecords.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      No multi-line academic history extracted in current record scope.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 gap-3">
                      {academicRecords.map((acad, idx) => (
                        <div key={idx} className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="text-sm font-semibold text-white">{acad.institution}</div>
                              <div className="text-xs text-indigo-300 mt-0.5">
                                {acad.degree} {acad.field_of_study ? `in ${acad.field_of_study}` : ''}
                              </div>
                            </div>
                            <span className="text-[10px] px-2 py-0.5 bg-slate-800 text-slate-300 rounded font-mono">
                              {acad.verification_status || 'Self-Reported'}
                            </span>
                          </div>
                          {acad.notes && (
                            <div className="text-[11px] text-slate-400 mt-2">{acad.notes}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 5. Skills Evidence */}
              {activeSection === 'skills_evidence' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Cpu className="w-5 h-5 text-indigo-400" />
                      Skills Evidence
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Technical capabilities observed in public repositories and code artifacts.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {capabilities.map((cap) => (
                      <div
                        key={cap.capability_key}
                        className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl flex items-center justify-between"
                      >
                        <div>
                          <div className="text-xs font-semibold text-slate-200 capitalize">
                            {cap.capability_key.replace(/_/g, ' ')}
                          </div>
                          <div className="text-[11px] text-slate-400 mt-0.5">
                            {cap.raw_evidence_count} observations · Cov: {(cap.coverage_k * 100).toFixed(0)}%
                          </div>
                        </div>
                        <span className="text-xs font-mono font-bold text-indigo-300">
                          {cap.estimate !== null ? `${(cap.estimate * 100).toFixed(0)}%` : 'Unknown'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 6. Project Dossiers (16 Facets) */}
              {activeSection === 'project_dossiers' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <FolderGit2 className="w-5 h-5 text-indigo-400" />
                      16-Facet Project Dossiers
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Modeled as distinct traceable entities across repository, DB, deployment, and tests.
                    </p>
                  </div>

                  {projects.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      No explicit project entities reconstructed in the current dossier scope.
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {projects.map((proj) => (
                        <div
                          key={proj.project_id || proj.name}
                          className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl space-y-3"
                        >
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="text-sm font-bold text-white">{proj.name}</div>
                              {proj.resume_claim && (
                                <div className="text-xs text-slate-400 mt-0.5">
                                  Claim: {proj.resume_claim}
                                </div>
                              )}
                            </div>
                            <span className="text-[10px] px-2 py-0.5 bg-indigo-950/60 border border-indigo-800/40 text-indigo-300 rounded font-mono">
                              Attribution: {proj.candidate_attribution || 'Unknown'}
                            </span>
                          </div>

                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono">
                            <div className="p-2 bg-slate-950/40 border border-slate-800/60 rounded">
                              <span className="text-slate-500 block text-[9px] uppercase">Repository</span>
                              <span className="text-slate-300 truncate block">{proj.repository || 'None'}</span>
                            </div>
                            <div className="p-2 bg-slate-950/40 border border-slate-800/60 rounded">
                              <span className="text-slate-500 block text-[9px] uppercase">Deployment</span>
                              <span className="text-slate-300 truncate block">{proj.deployment || 'None'}</span>
                            </div>
                            <div className="p-2 bg-slate-950/40 border border-slate-800/60 rounded">
                              <span className="text-slate-500 block text-[9px] uppercase">Database</span>
                              <span className="text-slate-300 truncate block">{proj.db || 'None'}</span>
                            </div>
                            <div className="p-2 bg-slate-950/40 border border-slate-800/60 rounded">
                              <span className="text-slate-500 block text-[9px] uppercase">Tests</span>
                              <span className="text-slate-300 truncate block">{proj.tests || 'None'}</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 7. Experience */}
              {activeSection === 'experience' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Briefcase className="w-5 h-5 text-indigo-400" />
                      Experience & Employment
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Work history declarations and organizational role references.
                    </p>
                  </div>

                  <div className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl text-xs text-slate-300 leading-relaxed">
                    Employment history claims originate from candidate declarations. CandidateX cross-references
                    declared roles against multi-contributor organizational repositories when public traces exist.
                  </div>
                </div>
              )}

              {/* 8. Credentials */}
              {activeSection === 'credentials' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Award className="w-5 h-5 text-indigo-400" />
                      Credentials & Certifications
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Third-party verified credentials from authorized issuers (Credly, Coursera, AWS, etc.).
                    </p>
                  </div>

                  {credentials.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      No third-party verified credentials or certification claims registered.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {credentials.map((cred) => (
                        <div
                          key={cred.credential_id || cred.title}
                          className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl flex items-center justify-between"
                        >
                          <div>
                            <div className="text-xs font-semibold text-white">{cred.title}</div>
                            <div className="text-[11px] text-slate-400 mt-0.5">
                              Issuer: {cred.issuer} {cred.issue_date ? `· ${cred.issue_date}` : ''}
                            </div>
                          </div>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                              cred.verification_status === 'verified'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {cred.verification_status}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 9. Publications */}
              {activeSection === 'publications' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <BookOpen className="w-5 h-5 text-indigo-400" />
                      Publications & Research
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Peer-reviewed publications, arXiv preprints, and research index references.
                    </p>
                  </div>

                  {publications.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      No research publications or DOI indices attached to this candidate record.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {publications.map((pub) => (
                        <div key={pub.publication_id || pub.title} className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl">
                          <div className="text-xs font-semibold text-white">{pub.title}</div>
                          <div className="text-[11px] text-slate-400 mt-0.5">
                            {pub.venue} {pub.year ? `(${pub.year})` : ''} · Authors: {pub.authors?.join(', ')}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 10. Coding Profiles */}
              {activeSection === 'coding_profiles' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Code2 className="w-5 h-5 text-indigo-400" />
                      Coding Profiles & Judges
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Independent algorithmic problem-solving records from LeetCode, Codeforces, and Kaggle.
                    </p>
                  </div>

                  {codingProfiles.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      No competitive coding or judge profiles supplied or discovered.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {codingProfiles.map((cp, idx) => (
                        <div key={idx} className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl">
                          <div className="flex justify-between items-start">
                            <div>
                              <div className="text-xs font-bold text-white capitalize">{cp.platform}</div>
                              <div className="text-[11px] text-slate-400 mt-0.5">User: {cp.username}</div>
                            </div>
                            <span className="text-[10px] px-2 py-0.5 bg-indigo-950 text-indigo-300 rounded font-mono">
                              {cp.solved_count ? `${cp.solved_count} solved` : 'Observed'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 11. Quantified Claims */}
              {activeSection === 'quantified_claims' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <TrendingUp className="w-5 h-5 text-indigo-400" />
                      Quantified Claim Verification
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Rigorous grounding for numeric assertions (latency, accuracy, scale, test coverage).
                    </p>
                  </div>

                  <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-400 leading-relaxed">
                    Core Invariant: Do not verify a metric merely because the same number appears on a portfolio.
                    Artifact grounding requires verifiable tests, benchmark suites, or reachable deployment receipts.
                  </div>

                  {quantifiedClaims.length === 0 ? (
                    <div className="p-8 text-center text-xs text-slate-500">
                      No quantified metric claims found in the evaluated resume sections.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {quantifiedClaims.map((qc, idx) => (
                        <div key={idx} className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl flex items-center justify-between">
                          <div>
                            <div className="text-xs font-semibold text-white">
                              {qc.metric.replace(/_/g, ' ')}: <span className="font-mono text-indigo-300">{qc.value} {qc.unit}</span>
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5">{qc.context}</div>
                          </div>
                          <span
                            className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                              qc.verification_status === 'supported_by_artifacts'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-slate-800 text-slate-400'
                            }`}
                          >
                            {qc.verification_status}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* 12. Contradictions */}
              {activeSection === 'contradictions' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <AlertTriangle className="w-5 h-5 text-amber-400" />
                      Contradiction Diagnostics (D_k)
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Negative evidence, failing tests, or direct discrepancies between declared and observed state.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {Object.entries(dossier.capability_conflicts || {}).map(([key, conf]) => (
                      <div
                        key={key}
                        className={`p-3.5 rounded-xl border ${
                          conf.has_meaningful_conflict
                            ? 'bg-amber-950/20 border-amber-800/40'
                            : 'bg-slate-900/40 border-slate-800'
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <div className="text-xs font-semibold text-slate-200 capitalize">
                            {key.replace(/_/g, ' ')}
                          </div>
                          <span className="text-[10px] font-mono font-bold text-slate-400">
                            D_k: {conf.contradiction_diagnostic?.toFixed(2) || '0.00'}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-1">
                          Pos support: {conf.positive_support_sum?.toFixed(1) || '0.0'} · Neg support:{' '}
                          {conf.negative_support_sum?.toFixed(1) || '0.0'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 13. Timeline */}
              {activeSection === 'timeline' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Clock className="w-5 h-5 text-indigo-400" />
                      Chronology & Timeline Inconsistencies
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Unified sequence of educational, professional, and artifact milestones.
                    </p>
                  </div>

                  {timelineInconsistencies.length > 0 && (
                    <div className="p-4 bg-amber-950/20 border border-amber-800/40 rounded-xl space-y-2">
                      <div className="text-xs font-semibold text-amber-300 flex items-center gap-2">
                        <AlertTriangle className="w-4 h-4 text-amber-400" />
                        Timeline Inconsistencies Requiring Human Review
                      </div>
                      <p className="text-[11px] text-amber-200/80 leading-relaxed">
                        Core Policy Invariant: Do not infer dishonesty. Label: timeline inconsistency requiring review.
                      </p>
                      <div className="space-y-1.5 mt-2">
                        {timelineInconsistencies.map((inc, i) => (
                          <div key={i} className="text-xs text-amber-100 flex items-start gap-1.5">
                            <span className="text-amber-400 font-bold">•</span>
                            <span>{inc.description}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="border-l-2 border-slate-800 ml-3 pl-4 space-y-4">
                    {timelineEvents.map((ev, i) => (
                      <div key={ev.event_id || i} className="relative">
                        <div className="w-2.5 h-2.5 bg-indigo-500 rounded-full absolute -left-[21px] top-1" />
                        <div className="text-xs font-mono text-indigo-400 font-bold">{ev.date_or_year}</div>
                        <div className="text-xs text-slate-200 font-medium mt-0.5">{ev.description}</div>
                        <div className="text-[10px] text-slate-500 font-mono capitalize">{ev.category}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 14. Role Requirements */}
              {activeSection === 'role_requirements' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <CheckSquare className="w-5 h-5 text-indigo-400" />
                      Role Requirements
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Extracted job requirements and priority alignment against candidate observations.
                    </p>
                  </div>

                  <div className="space-y-2.5">
                    {requirements.map((req) => (
                      <div
                        key={req.requirement_id}
                        className="p-3 bg-slate-900/40 border border-slate-800 rounded-xl flex items-center justify-between"
                      >
                        <div className="text-xs text-slate-200">{req.source_text}</div>
                        <span className="text-[10px] font-mono px-2 py-0.5 bg-slate-800 text-slate-400 rounded uppercase">
                          {req.priority}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 15. Capability Signals */}
              {activeSection === 'capability_signals' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Activity className="w-5 h-5 text-indigo-400" />
                      Capability Signals
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Twelve core technical capabilities evaluated across bounded scope.
                    </p>
                  </div>

                  <div className="space-y-3">
                    {capabilities.map((cap) => (
                      <div key={cap.capability_key} className="p-3.5 bg-slate-900/40 border border-slate-800 rounded-xl space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-semibold text-slate-200 capitalize">
                            {cap.capability_key.replace(/_/g, ' ')}
                          </span>
                          <span className="font-mono text-emerald-400 font-bold">
                            {cap.estimate !== null ? `${(cap.estimate * 100).toFixed(1)}%` : 'Unknown'}
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-indigo-500 rounded-full"
                            style={{ width: `${Math.min(100, (cap.estimate || 0) * 100)}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 16. Interview Plan */}
              {activeSection === 'interview_plan' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <MessageSquare className="w-5 h-5 text-indigo-400" />
                      Interview Plan
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Ranked inquiries targeted at uncertainty, evidence gaps, and contradictory signals.
                    </p>
                  </div>

                  <div className="space-y-4">
                    {interviewQuestions.map((q) => (
                      <div
                        key={q.question_id}
                        className="p-4 bg-slate-900/40 border border-slate-800 rounded-xl space-y-2"
                      >
                        <div className="text-xs font-semibold text-indigo-300 uppercase tracking-wide">
                          {q.target_capability}
                        </div>
                        <div className="text-sm font-medium text-slate-100">{q.question_text}</div>
                        <div className="text-xs text-slate-400">{q.rationale}</div>
                        <div className="text-[11px] text-slate-500 mt-1 italic">
                          Guidance: {q.verification_guidance}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 17. Source Explorer */}
              {activeSection === 'source_explorer' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Network className="w-5 h-5 text-indigo-400" />
                      Source & Crawl Explorer
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Terminal state tracking for supplied and discovered external links.
                    </p>
                  </div>

                  <div className="p-3 bg-slate-900/60 border border-slate-800 rounded-xl text-xs text-slate-400 leading-relaxed">
                    Source Lifecycle States: supplied · resume extracted · discovered · queued · fetched · failed · blocked · deferred · not scanned.
                    Every source has a terminal state; no missing links are hidden.
                  </div>
                </div>
              )}

              {/* 18. Evidence Graph */}
              {activeSection === 'evidence_graph' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <GitFork className="w-5 h-5 text-indigo-400" />
                      Candidate Evidence Graph (CEG)
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Interactive ontology graph connecting claims, evidence, artifacts, and repositories.
                    </p>
                  </div>

                  <GraphViewer
                    graph={graph}
                    selectedCapability={null}
                    onSelectCapability={() => {}}
                    onInspectEvidence={(id) => onInspectEvidence?.(id)}
                  />
                </div>
              )}

              {/* 19. Methodology */}
              {activeSection === 'methodology' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <HelpCircle className="w-5 h-5 text-indigo-400" />
                      Methodology & Scientific Foundations
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Deterministic parsing, cluster bootstrap confidence intervals, and evidence family decay.
                    </p>
                  </div>

                  <div className="space-y-3 text-xs text-slate-300 leading-relaxed font-sans">
                    <p>
                      CandidateX is an evidence-first capability intelligence engine. It enforces strict mathematical
                      guarantees: non-linear diminishing returns within evidence families, cluster-based uncertainty
                      estimation, and non-judgmental inconsistency detection.
                    </p>
                    <p>
                      Candidate code is NEVER executed. All analysis is static and cryptographically fingerprinted.
                    </p>
                  </div>
                </div>
              )}

              {/* 20. Limitations */}
              {activeSection === 'limitations' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <FileCode className="w-5 h-5 text-indigo-400" />
                      System Limitations & Boundary Disclaimers
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Explicit acknowledgment of scope limits, heuristic priors, and observational boundaries.
                    </p>
                  </div>

                  <div className="space-y-2.5">
                    {(dossier.system_limitations || [
                      'Candidate code is never executed. Observations derive solely from static syntax, AST, and metadata inspection.',
                      'Static rule strengths are uncalibrated policy heuristics, not empirically verified ability distributions.',
                      'Missing evidence remains unknown; lack of repository evidence does not prove lack of capability.',
                      'Repository attribution does not establish human identity or sole authorship.',
                    ]).map((lim, idx) => (
                      <div key={idx} className="p-3 bg-slate-900/40 border border-slate-800 rounded-lg text-xs text-slate-300 flex items-start gap-2">
                        <span className="text-indigo-400 font-bold">•</span>
                        <span>{lim}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 21. Exports */}
              {activeSection === 'exports' && (
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      <Download className="w-5 h-5 text-indigo-400" />
                      Provenance-Preserving Exports
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      Download complete evaluation dossier in structured formats preserving all evidence IDs.
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={() => {
                        const blob = new Blob([JSON.stringify(dossier, null, 2)], { type: 'application/json' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `candidatex-dossier-${dossier.candidate_id}.json`;
                        a.click();
                      }}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 transition-all"
                    >
                      <Download className="w-4 h-4" />
                      Export Structured JSON
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </GlassCard>
      </main>

      {/* 5-Hop Provenance Trace Modal: Claim → Evidence → Source → Artifact → Revision */}
      <GlassModal
        isOpen={!!activeTraceClaim}
        onClose={() => setActiveTraceClaim(null)}
        title="Evidence Provenance Trace Link"
      >
        {activeTraceClaim && (
          <div className="space-y-6 text-xs text-slate-200">
            <div className="p-3 bg-slate-900/80 border border-slate-800 rounded-xl space-y-1">
              <div className="text-[10px] text-slate-500 uppercase font-semibold">
                Traceable Chain of Custody
              </div>
              <div className="text-xs font-mono text-indigo-300 font-bold flex items-center gap-1.5">
                <span>Claim</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                <span>Evidence</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                <span>Source</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                <span>Artifact</span>
                <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                <span>Immutable Revision</span>
              </div>
            </div>

            {/* Hop 1: Claim */}
            <div className="space-y-1.5 border-l-2 border-indigo-500 pl-3">
              <div className="text-[10px] font-bold uppercase text-indigo-400">Hop 1: Candidate Claim</div>
              <div className="text-sm font-semibold text-white">"{activeTraceClaim.claim_text}"</div>
              <div className="text-[11px] text-slate-400 font-mono">
                Status: {activeTraceClaim.status} · Capability: {activeTraceClaim.target_capability} · Claim ID: {activeTraceClaim.claim_id}
              </div>
            </div>

            {/* Hop 2: Evidence */}
            <div className="space-y-1.5 border-l-2 border-blue-500 pl-3">
              <div className="text-[10px] font-bold uppercase text-blue-400">Hop 2: Grounding Evidence</div>
              <div className="space-y-1 font-mono text-[11px] text-slate-300">
                {activeTraceClaim.grounding_evidence_ids?.map((eid) => (
                  <div key={eid} className="p-2 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-center">
                    <span>Evidence ID: {eid}</span>
                    <button
                      onClick={() => copyToClipboard(eid, eid)}
                      className="text-slate-400 hover:text-white"
                    >
                      {copiedId === eid ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Hop 3: Source */}
            <div className="space-y-1.5 border-l-2 border-purple-500 pl-3">
              <div className="text-[10px] font-bold uppercase text-purple-400">Hop 3: Originating Sources</div>
              <div className="space-y-1 font-mono text-[11px] text-slate-300">
                {activeTraceClaim.citation_urls?.map((url) => (
                  <div key={url} className="p-2 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-center">
                    <span className="truncate">{url}</span>
                    <a href={url} target="_blank" rel="noreferrer" className="text-indigo-400 hover:text-indigo-300 ml-2">
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>
                ))}
              </div>
            </div>

            {/* Hop 4: Artifact */}
            <div className="space-y-1.5 border-l-2 border-emerald-500 pl-3">
              <div className="text-[10px] font-bold uppercase text-emerald-400">Hop 4: Verified Artifact</div>
              <div className="p-2.5 bg-slate-900/60 rounded border border-slate-800 text-[11px] text-slate-300 space-y-1">
                <div>Artifact Path: <span className="font-mono text-emerald-300">Controlled Code / Schema Observation</span></div>
                <div>Attribution: <span className="font-mono text-slate-400">Attributed to Declared Identity</span></div>
              </div>
            </div>

            {/* Hop 5: Immutable Revision */}
            <div className="space-y-1.5 border-l-2 border-amber-500 pl-3">
              <div className="text-[10px] font-bold uppercase text-amber-400">Hop 5: Immutable Revision & Hash</div>
              <div className="p-2.5 bg-slate-900/60 rounded border border-slate-800 text-[11px] text-slate-300 space-y-1">
                <div>Commit SHA / Hash: <span className="font-mono text-amber-300">Pinned Git Revision</span></div>
                <div>Integrity Fingerprint: <span className="font-mono text-slate-400">SHA-256 Verified Static Record</span></div>
              </div>
            </div>
          </div>
        )}
      </GlassModal>
    </div>
  );
};
