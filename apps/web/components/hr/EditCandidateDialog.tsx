'use client';

import { useState, type FormEvent } from 'react';
import { UserCheck, X } from 'lucide-react';
import type { CandidateManifest, CanonicalRole } from '../../types/cci';
import { ROLE_LABELS, saveHRCandidate, type HRCandidate } from './hr-data';
import { saveCandidateBackend } from '../../lib/api';
import { GlassModal } from '@/components/ui/GlassModal';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassSelect } from '@/components/ui/GlassSelect';
import { GlassButton } from '@/components/ui/GlassButton';

export function EditCandidateDialog({
  candidate,
  onClose,
  onSave,
}: {
  candidate: HRCandidate;
  onClose: () => void;
  onSave: (updated: HRCandidate) => void;
}) {
  const [name, setName] = useState(candidate.display_name);
  const [email, setEmail] = useState(candidate.primary_email || '');
  const [role, setRole] = useState<CanonicalRole>((candidate.role as CanonicalRole) || 'backend');
  const [roleLabel, setRoleLabel] = useState(candidate.role_label || '');
  const [workUrl, setWorkUrl] = useState(candidate.manifest?.github_repositories?.[0] || '');
  const [skills, setSkills] = useState<string[]>(candidate.manifest?.declared_skills || []);
  const [skillInput, setSkillInput] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

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
    setSkills(skills.filter((s) => s !== skillToRemove));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    const trimmedName = name.trim();
    const trimmedEmail = email.trim();
    const trimmedUrl = workUrl.trim();

    if (!trimmedName) {
      setError('Please enter the student or candidate’s name.');
      return;
    }

    if (trimmedUrl) {
      try {
        const parsed = new URL(trimmedUrl);
        if (!['https:', 'http:'].includes(parsed.protocol)) throw new Error();
      } catch {
        setError('Please use a valid URL starting with https:// or http://.');
        return;
      }
    }

    setSaving(true);
    try {
      const isRepo = trimmedUrl && trimmedUrl.includes('github.com');
      const manifest: CandidateManifest = {
        candidate_id: candidate.id,
        full_name: trimmedName,
        primary_email: trimmedEmail || undefined,
        github_usernames: [],
        github_repositories: isRepo ? [trimmedUrl] : candidate.manifest?.github_repositories || [],
        deployment_urls: !isRepo && trimmedUrl ? [trimmedUrl] : candidate.manifest?.deployment_urls || [],
        portfolio_urls: candidate.manifest?.portfolio_urls || [],
        declared_skills: skills,
        extraction_metadata: { source: 'edit_profile', role },
      };

      const updatedCandidate: HRCandidate = {
        ...candidate,
        display_name: trimmedName,
        primary_email: trimmedEmail || undefined,
        role: role,
        role_label: roleLabel.trim() || ROLE_LABELS[role] || role,
        manifest: manifest,
      };

      // Persist to local storage
      saveHRCandidate(updatedCandidate);

      // Persist to backend API
      try {
        await saveCandidateBackend(updatedCandidate);
      } catch (backendErr) {
        console.warn('Backend candidate update failed, saved locally', backendErr);
      }

      onSave(updatedCandidate);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update candidate profile.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <GlassModal
      isOpen={true}
      onClose={onClose}
      title={`Edit Profile: ${candidate.display_name}`}
      subtitle="Update student information, target role specialization, code repositories, and declared skills."
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <GlassInput
          label="Full Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Demo Member One"
          required
        />

        <GlassInput
          label="Email Address"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="e.g. member1@example.test"
        />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <GlassSelect
            label="Target Technical Role"
            value={role}
            onChange={(e) => setRole(e.target.value as CanonicalRole)}
            options={roleOptions}
          />

          <GlassInput
            label="Specialization / Title"
            value={roleLabel}
            onChange={(e) => setRoleLabel(e.target.value)}
            placeholder="e.g. Fullstack, SDE or SRE"
          />
        </div>

        <GlassInput
          label="Code Repository / Work Sample URL"
          value={workUrl}
          onChange={(e) => setWorkUrl(e.target.value)}
          placeholder="https://github.com/username/project"
        />

        <div>
          <GlassInput
            label="Skills (Press Enter or comma to add)"
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={handleAddSkill}
            placeholder="Type skill and press Enter..."
          />
          {skills.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              {skills.map((skill) => (
                <span
                  key={skill}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-brand-500/10 border border-brand-500/20 text-xs font-medium text-brand-300"
                >
                  {skill}
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(skill)}
                    className="hover:text-white transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {error && (
          <p role="alert" className="text-sm text-rose-400 font-medium pt-1">
            {error}
          </p>
        )}

        <div className="flex flex-wrap items-center justify-end gap-3 pt-4 border-t border-white/10 mt-6">
          <GlassButton type="button" variant="ghost" onClick={onClose} disabled={saving}>
            Cancel
          </GlassButton>
          <GlassButton type="submit" variant="primary" icon={<UserCheck className="w-4 h-4" />} disabled={saving}>
            {saving ? 'Saving…' : 'Save Changes'}
          </GlassButton>
        </div>
      </form>
    </GlassModal>
  );
}
