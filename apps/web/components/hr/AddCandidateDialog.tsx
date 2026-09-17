'use client';

import { useState, type FormEvent } from 'react';
import { Info, UserPlus } from 'lucide-react';
import type { CandidateManifest, CanonicalRole } from '../../types/cci';
import { HRDialog, controlClass, primaryClass, secondaryClass } from './HRDialog';
import { ROLE_LABELS, type HRCandidate } from './hr-data';

export function AddCandidateDialog({ onClose, onAdd }: {
  onClose: () => void;
  onAdd: (candidate: HRCandidate) => void;
}) {
  const [error, setError] = useState('');

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    const form = new FormData(event.currentTarget);
    const name = String(form.get('name') || '').trim();
    const email = String(form.get('email') || '').trim();
    const workUrl = String(form.get('workUrl') || '').trim();
    if (!name) { setError('Please enter the candidate’s name.'); return; }
    if (workUrl) {
      try {
        const url = new URL(workUrl);
        if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) throw new Error();
      } catch {
        setError('Please use a public website link starting with https:// or http://, without a password.');
        return;
      }
    }
    const role = String(form.get('role')) as CanonicalRole;
    const id = crypto.randomUUID();
    const isRepository = workUrl && new URL(workUrl).hostname === 'github.com' && new URL(workUrl).pathname.split('/').filter(Boolean).length === 2;
    const manifest: CandidateManifest = {
      candidate_id: id,
      full_name: name,
      primary_email: email || undefined,
      github_usernames: [],
      github_repositories: isRepository ? [workUrl] : [],
      deployment_urls: [],
      portfolio_urls: workUrl && !isRepository ? [workUrl] : [],
      declared_skills: String(form.get('skills') || '').split(',').map((skill) => skill.trim()).filter(Boolean),
      extraction_metadata: { source: 'hr_local_draft', role, consent_confirmed: true },
    };
    onAdd({
      id, display_name: name, primary_email: email || undefined, role,
      has_completed_dossier: false, has_meaningful_conflict: false,
      created_at: new Date().toISOString(), source: 'draft', manifest,
    });
  }

  return (
    <HRDialog title="Add Candidate" description="Create a local draft. Only a name, role, and permission are required." onClose={onClose} initialFocusId="hr-candidate-name">
      <form onSubmit={submit} className="space-y-5 p-6">
        <div className="flex gap-3 rounded-xl bg-indigo-50 p-4 text-sm leading-6 text-indigo-900">
          <Info className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
          <p><strong className="block font-semibold">A draft, not a shared candidate record</strong>Your draft stays on this page only and does not start an evaluation. Download a copy from the candidate’s View action before leaving or refreshing.</p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <label className="space-y-2 text-sm font-medium">Full name <span className="text-slate-500">(required)</span>
            <input id="hr-candidate-name" name="name" autoComplete="name" required maxLength={160} className={controlClass} placeholder="e.g. Sam Taylor" />
          </label>
          <label className="space-y-2 text-sm font-medium">Email <span className="text-slate-500">(optional)</span>
            <input name="email" type="email" autoComplete="email" maxLength={254} className={controlClass} placeholder="name@example.com" />
          </label>
        </div>
        <label className="block space-y-2 text-sm font-medium">Hiring role
          <select name="role" className={controlClass} defaultValue="backend">
            {Object.entries(ROLE_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        <label className="block space-y-2 text-sm font-medium">Work sample or portfolio <span className="text-slate-500">(optional)</span>
          <input name="workUrl" type="url" inputMode="url" autoCapitalize="none" spellCheck={false} aria-describedby="hr-work-hint" maxLength={2000} className={controlClass} placeholder="https://github.com/name/project" />
          <span id="hr-work-hint" className="block text-xs font-normal leading-5 text-slate-500">One public project or portfolio link. Leave blank if you don’t have one yet.</span>
        </label>
        <label className="block space-y-2 text-sm font-medium">Skills shared by the candidate <span className="text-slate-500">(optional)</span>
          <input name="skills" maxLength={1000} className={controlClass} placeholder="e.g. Python, React, SQL" />
          <span className="block text-xs font-normal text-slate-500">Separate skills with commas. These are not verified findings.</span>
        </label>
        <label className="flex items-start gap-3 text-sm leading-6 text-slate-600">
          <input name="consent" type="checkbox" required className="mt-1 h-4 w-4 accent-indigo-600" />
          I have permission to use this candidate’s information for the hiring process.
        </label>
        {error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p>}
        <div className="sticky -bottom-6 -mx-6 flex flex-wrap justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4">
          <button type="button" onClick={onClose} className={secondaryClass}>Cancel</button>
          <button type="submit" className={primaryClass}><UserPlus className="h-4 w-4" aria-hidden="true" />Add local draft</button>
        </div>
      </form>
    </HRDialog>
  );
}
