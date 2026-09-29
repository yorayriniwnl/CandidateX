'use client';

import { useState } from 'react';
import { AlertCircle, CheckCircle2, ChevronRight, GitFork, Loader2, Play, Sparkles } from 'lucide-react';
import { fetchCandidateDossier, fetchCandidateGraph, saveCandidateBackend, triggerPipelineRun } from '../../lib/api';
import type {
  CandidateManifest,
  CanonicalRole,
  CEGGraph,
  Dossier,
} from '../../types/cci';
import { ROLE_LABELS, saveReviewToHR, type HRCandidate } from './hr-data';
import { GlassModal } from '@/components/ui/GlassModal';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassSelect } from '@/components/ui/GlassSelect';
import { GlassButton } from '@/components/ui/GlassButton';
import { GlassCard } from '@/components/ui/GlassCard';

const AUDIT_STAGES = [
  'Source Ingestion & Identity Validation',
  'AST Code Parsing & Structure Extraction',
  'Candidate Evidence Graph (CEG) Synthesis',
  'Non-Parametric Bootstrap Uncertainty Modeling',
  'Contradiction Invariant & Discordance Checking',
  'Role Capability Index (RCI) Calculation & Final Dossier',
];

const DEFAULT_ROLE_SKILLS: Record<string, string> = {
  fullstack: 'TypeScript, React, Python, FastAPI, PostgreSQL, Docker, Git',
  frontend: 'TypeScript, React, Next.js, Tailwind CSS, Redux, Jest, Accessibility',
  ml_engineer: 'Python, PyTorch, Scikit-learn, Transformers, Vector Search, FastAPI',
  devops_cloud: 'Kubernetes, Docker, Terraform, AWS, CI/CD, Monitoring, Linux',
  backend: 'Python, Go, FastAPI, PostgreSQL, Redis, Docker, Microservices, REST',
  data_engineer: 'Python, SQL, Apache Spark, Kafka, Airflow, dbt, PostgreSQL',
};

export function AuditStudentDialog({
  candidate,
  onClose,
  onAuditComplete,
  onViewDossier,
}: {
  candidate: HRCandidate;
  onClose: () => void;
  onAuditComplete: (updated: HRCandidate) => void;
  onViewDossier: (candidate: HRCandidate) => void;
}) {
  const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }));

  const [name, setName] = useState(candidate.display_name);
  const [email, setEmail] = useState(candidate.primary_email || '');
  const [role, setRole] = useState<CanonicalRole>((candidate.role as CanonicalRole) || 'backend');
  const [repoUrl, setRepoUrl] = useState(
    candidate.manifest?.github_repositories?.[0] || ''
  );
  const [skills, setSkills] = useState(
    candidate.manifest?.declared_skills?.join(', ') || DEFAULT_ROLE_SKILLS[candidate.role || 'backend'] || ''
  );
  const [cvText, setCvText] = useState('');

  const [running, setRunning] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [error, setError] = useState('');
  const [result, setResult] = useState<HRCandidate | null>(null);

  async function handleRunAudit() {
    setRunning(true);
    setError('');
    setCurrentStage(0);

    const stageTimer = setInterval(() => {
      setCurrentStage((prev) => (prev < AUDIT_STAGES.length - 1 ? prev + 1 : prev));
    }, 600);

    try {
      const skillsArray = skills
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      const reposArray = repoUrl.trim() ? [repoUrl.trim()] : [];

      const manifest: CandidateManifest = {
        candidate_id: candidate.id,
        full_name: name.trim() || candidate.display_name,
        primary_email: email.trim() || candidate.primary_email,
        github_usernames: [],
        github_repositories: reposArray,
        deployment_urls: [],
        portfolio_urls: [],
        declared_skills: skillsArray,
        extraction_metadata: { source: 'hr_audit', role },
      };

      // Trigger real analysis pipeline on backend
      const runRes = await triggerPipelineRun(candidate.id, role, manifest, undefined, cvText.trim() || undefined);
      if (!runRes) {
        throw new Error('Analysis pipeline failed to start.');
      }

      if (runRes.error) {
        throw new Error(runRes.error);
      }

      // Fetch real resulting dossier and graph
      let dossier: Dossier | undefined;
      let graph: CEGGraph | undefined;

      try {
        const [d, g] = await Promise.all([
          fetchCandidateDossier(candidate.id),
          fetchCandidateGraph(candidate.id),
        ]);
        dossier = d;
        graph = g;
      } catch (fetchErr) {
        console.warn('Could not fetch updated dossier after pipeline completion', fetchErr);
      }

      const score = dossier?.rci ?? runRes.rci ?? null;
      const coverage = dossier?.coverage ?? runRes.coverage ?? 0;
      const hasConflict = dossier?.capability_conflicts
        ? Object.values(dossier.capability_conflicts).some((c) => c.has_meaningful_conflict)
        : false;
      const observedCount = dossier?.capability_estimates
        ? Object.values(dossier.capability_estimates).filter((e) => e.is_observed && e.estimate != null).length
        : 0;

      // Persist real evaluation to HR Storage
      const updated = saveReviewToHR({
        candidateId: candidate.id,
        displayName: name.trim() || candidate.display_name,
        email: email.trim() || candidate.primary_email,
        role: role,
        rci: score ?? undefined,
        jdFitScore: score ?? undefined,
        observedCapabilities: observedCount,
        coverage: coverage,
        hasMeaningfulConflict: hasConflict,
        manifest: manifest,
        dossier: dossier,
        graph: graph,
      });

      // Also persist to backend API
      saveCandidateBackend({
        id: candidate.id,
        display_name: name.trim() || candidate.display_name,
        primary_email: email.trim() || candidate.primary_email,
        role: role,
        rci: score ?? undefined,
        jd_fit_score: score ?? undefined,
        observed_capabilities: observedCount,
        coverage: coverage,
        has_meaningful_conflict: hasConflict,
        has_completed_dossier: true,
        created_at: new Date().toISOString(),
        manifest: manifest,
      }).catch((backendSaveErr) => {
        console.warn('Backend candidate save warning:', backendSaveErr);
      });

      setResult(updated);
      onAuditComplete(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Audit pipeline could not be executed.');
    } finally {
      clearInterval(stageTimer);
      setRunning(false);
    }
  }

  return (
    <GlassModal
      isOpen={true}
      onClose={onClose}
      title={`Audit Student: ${candidate.display_name}`}
      subtitle={
        result
          ? result.rci != null
            ? `Technical capability evaluation finalized with score ${result.rci.toFixed(1)} / 100.`
            : `Audit completed. No verified AST code observations found in provided repositories.`
          : `Run a formal multi-stage technical audit on code repositories and verified skills.`
      }
      size="lg"
    >
      {result ? (
        <div className="space-y-6">
          <GlassCard glow="indigo" className="p-6 border-brand-500/30 bg-brand-500/10 text-center">
            <CheckCircle2 className="w-12 h-12 text-brand-400 mx-auto mb-3" />
            <h3 className="text-xl font-bold text-white">Student Audit Successful</h3>
            <p className="text-sm text-slate-300 mt-1">
              {candidate.display_name} has been evaluated and their dossier is saved to the HR directory.
            </p>

            <div className="flex flex-wrap items-center justify-center gap-4 mt-6">
              <div className="px-5 py-3 rounded-2xl bg-white/[0.06] border border-white/10 text-center">
                <span className="text-xs text-slate-400 uppercase font-mono block">RCI / Score</span>
                <span className="text-2xl font-black text-brand-400 font-mono">
                  {result.rci != null ? (
                    <>
                      {result.rci.toFixed(1)}{' '}
                      <span className="text-xs text-slate-500 font-normal">/ 100</span>
                    </>
                  ) : (
                    <span className="text-slate-500 text-lg">Pending Evidence</span>
                  )}
                </span>
              </div>
              <div className="px-5 py-3 rounded-2xl bg-white/[0.06] border border-white/10 text-center">
                <span className="text-xs text-slate-400 uppercase font-mono block">Observed Capabilities</span>
                <span className="text-2xl font-black text-indigo-400 font-mono">
                  {result.observed_capabilities ?? 0} <span className="text-xs text-slate-500 font-normal">/ 12</span>
                </span>
              </div>
              <div className="px-5 py-3 rounded-2xl bg-white/[0.06] border border-white/10 text-center">
                <span className="text-xs text-slate-400 uppercase font-mono block">Evidence Coverage</span>
                <span className="text-2xl font-black text-emerald-400 font-mono">
                  {(((result.coverage ?? 0)) * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </GlassCard>

          <div className="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-white/10">
            <GlassButton variant="ghost" onClick={onClose}>
              Done
            </GlassButton>
            {result.dossier && (
              <GlassButton
                variant="primary"
                onClick={() => {
                  onClose();
                  onViewDossier(result);
                }}
                icon={<Sparkles className="w-4 h-4" />}
              >
                View Full Dossier
              </GlassButton>
            )}
          </div>
        </div>
      ) : running ? (
        <div className="space-y-6 py-6">
          <div className="text-center">
            <Loader2 className="w-10 h-10 text-brand-400 animate-spin mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white">Running Technical Audit</h3>
            <p className="text-sm text-slate-400 mt-1">
              Extracting AST evidence, computing bootstrap uncertainty bounds, and synthesizing RCI...
            </p>
          </div>

          <div className="space-y-2 max-w-md mx-auto">
            {AUDIT_STAGES.map((stage, idx) => {
              const isPast = idx < currentStage;
              const isCurrent = idx === currentStage;
              return (
                <div
                  key={stage}
                  className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border text-xs transition-colors ${
                    isPast
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                      : isCurrent
                      ? 'bg-brand-500/15 border-brand-500/30 text-brand-300 font-medium'
                      : 'bg-white/[0.02] border-white/5 text-slate-500'
                  }`}
                >
                  {isPast ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 className="w-4 h-4 text-brand-400 animate-spin shrink-0" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-slate-600 shrink-0" />
                  )}
                  <span>{stage}</span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleRunAudit();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <GlassInput
              label="Student Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Candidate full name"
              required
            />
            <GlassInput
              label="Student Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. student@kiit.ac.in"
            />
          </div>

          <GlassSelect
            label="Evaluation Target Role"
            value={role}
            onChange={(e) => {
              const newRole = e.target.value as CanonicalRole;
              setRole(newRole);
              if (!skills || Object.values(DEFAULT_ROLE_SKILLS).includes(skills)) {
                setSkills(DEFAULT_ROLE_SKILLS[newRole] || '');
              }
            }}
            options={roleOptions}
          />

          <GlassInput
            label="Code Repository / Work Sample URL"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="https://github.com/username/project"
            leadingIcon={<GitFork className="w-4 h-4 text-slate-400" />}
          />
          <span className="block -mt-3 text-xs text-slate-500">
            Source repository used for AST static verification and capability extraction.
          </span>

          <GlassInput
            label="Declared Skills (comma-separated)"
            value={skills}
            onChange={(e) => setSkills(e.target.value)}
            placeholder="Go, PostgreSQL, Kafka, Distributed Systems"
          />

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Resume Text / Project Summary (Optional)
            </label>
            <textarea
              value={cvText}
              onChange={(e) => setCvText(e.target.value)}
              placeholder="Paste candidate resume text, project summaries, or technical achievements..."
              rows={3}
              className="w-full rounded-xl bg-white/[0.04] border border-white/10 px-3.5 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/40 transition-colors"
            />
          </div>

          {error && (
            <div role="alert" className="flex items-center gap-2 rounded-xl bg-rose-500/10 border border-rose-500/20 p-4 text-sm text-rose-300">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-white/10 mt-6">
            <GlassButton type="button" variant="ghost" onClick={onClose}>
              Cancel
            </GlassButton>
            <GlassButton type="submit" variant="primary" icon={<Play className="w-4 h-4" />}>
              Start Student Audit
            </GlassButton>
          </div>
        </form>
      )}
    </GlassModal>
  );
}
