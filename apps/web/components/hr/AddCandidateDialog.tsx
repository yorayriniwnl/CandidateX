'use client';

import { useState, type FormEvent } from 'react';
import { Info, UserPlus, X } from 'lucide-react';
import type { CandidateManifest, CanonicalRole } from '../../types/cci';
import { ROLE_LABELS, type HRCandidate } from './hr-data';
import { GlassModal } from '@/components/ui/GlassModal';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassSelect } from '@/components/ui/GlassSelect';
import { GlassButton } from '@/components/ui/GlassButton';

export function AddCandidateDialog({ onClose, onAdd }: {
  onClose: () => void;
  onAdd: (candidate: HRCandidate) => void;
}) {
  const [error, setError] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState('');

  const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }));

  function handleAddSkill(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const newSkill = skillInput.trim();
      if (newSkill && !skills.includes(newSkill)) {
        setSkills([...skills, newSkill]);
      }
      setSkillInput('');
    }
  }

  function handleRemoveSkill(skillToRemove: string) {
    setSkills(skills.filter(s => s !== skillToRemove));
  }

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
      declared_skills: skills,
      extraction_metadata: { source: 'hr_local_draft', role, consent_confirmed: true },
    };
    onAdd({
      id, display_name: name, primary_email: email || undefined, role,
      has_completed_dossier: false, has_meaningful_conflict: false,
      created_at: new Date().toISOString(), source: 'draft', manifest,
    });
  }

  return (
    <GlassModal isOpen={true} onClose={onClose} title="Add Candidate" subtitle="Create a local draft. Only a name, role, and permission are required." size="md">
      <form onSubmit={submit} className="space-y-5">
        <div className="flex gap-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 p-4 text-sm leading-6 text-indigo-200">
          <Info className="mt-0.5 h-5 w-5 shrink-0 text-indigo-400" aria-hidden="true" />
          <p><strong className="block font-semibold text-indigo-300">A draft, not a shared candidate record</strong>Your draft stays on this page only and does not start an evaluation. Download a copy from the candidate’s View action before leaving or refreshing.</p>
        </div>
        <div className="grid gap-5 sm:grid-cols-2">
          <GlassInput name="name" label="Full name" placeholder="e.g. Sam Taylor" required />
          <GlassInput name="email" type="email" label="Email (optional)" placeholder="name@example.com" />
        </div>
        <GlassSelect name="role" label="Hiring role" options={roleOptions} value="backend" />
        <GlassInput name="workUrl" type="url" label="Work sample or portfolio (optional)" placeholder="https://github.com/name/project" />
        <span className="block -mt-3 text-xs font-normal leading-5 text-slate-500">One public project or portfolio link. Leave blank if you don’t have one yet.</span>
        
        <div className="space-y-2">
          <label className="block text-sm font-medium text-slate-300">Skills shared by the candidate <span className="text-slate-500">(optional)</span></label>
          <div className="flex flex-wrap gap-2 mb-2">
            {skills.map((skill) => (
              <span key={skill} className="inline-flex items-center gap-1 rounded-full bg-white/10 px-2.5 py-1 text-xs font-medium text-slate-200 border border-white/20">
                {skill}
                <button type="button" onClick={() => handleRemoveSkill(skill)} className="text-slate-400 hover:text-white">
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
          <GlassInput
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={handleAddSkill}
            placeholder="Type a skill and press Enter..."
          />
        </div>

        <label className="flex items-start gap-3 text-sm leading-6 text-slate-400">
          <input name="consent" type="checkbox" required className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-800 text-indigo-600 focus:ring-indigo-600 focus:ring-offset-slate-900" />
          I have permission to use this candidate’s information for the hiring process.
        </label>
        {error && <p role="alert" className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-3 text-sm text-rose-400">{error}</p>}
        <div className="flex flex-wrap justify-end gap-3 pt-4 border-t border-white/10 mt-6">
          <GlassButton variant="ghost" onClick={onClose}>Cancel</GlassButton>
          <GlassButton type="submit" variant="primary" icon={<UserPlus className="h-4 w-4" />}>Add local draft</GlassButton>
        </div>
      </form>
    </GlassModal>
  );
}
