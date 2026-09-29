'use client';

import { useState, type FormEvent } from 'react';
import { Save } from 'lucide-react';
import type { CanonicalRole } from '../../types/cci';
import { ROLE_LABELS, toTitleCase, type HRCandidate } from './hr-data';
import { GlassModal } from '@/components/ui/GlassModal';
import { GlassInput } from '@/components/ui/GlassInput';
import { GlassSelect } from '@/components/ui/GlassSelect';
import { GlassButton } from '@/components/ui/GlassButton';

export function EditMemberDialog({ member, onClose, onSave }: {
  member: HRCandidate;
  onClose: () => void;
  onSave: (updated: HRCandidate) => void;
}) {
  const [error, setError] = useState('');
  const roleOptions = Object.entries(ROLE_LABELS).map(([value, label]) => ({ value, label }));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    const form = new FormData(event.currentTarget);
    const name = String(form.get('name') || '').trim();
    const email = String(form.get('email') || '').trim();
    if (!name) {
      setError('Please enter the member\'s name.');
      return;
    }
    const role = String(form.get('role')) as CanonicalRole;
    const updated: HRCandidate = {
      ...member,
      display_name: toTitleCase(name),
      primary_email: email || undefined,
      role,
      role_label: ROLE_LABELS[role] || role,
    };
    onSave(updated);
  }

  return (
    <GlassModal isOpen={true} onClose={onClose} title="Edit Team Member" subtitle={`Editing ${member.display_name}`} size="md">
      <form onSubmit={submit} className="space-y-5">
        <div className="grid gap-5 sm:grid-cols-2">
          <GlassInput name="name" label="Full name" placeholder="e.g. Sam Taylor" required defaultValue={member.display_name} />
          <GlassInput name="email" type="email" label="Email (optional)" placeholder="name@example.com" defaultValue={member.primary_email || ''} />
        </div>
        <GlassSelect name="role" label="Role" options={roleOptions} defaultValue={member.role || 'backend'} />
        {error && <p role="alert" className="rounded-lg bg-rose-500/10 border border-rose-500/20 p-3 text-sm text-rose-400">{error}</p>}
        <div className="flex flex-wrap justify-end gap-3 pt-4 border-t border-white/10 mt-6">
          <GlassButton type="button" variant="ghost" onClick={onClose}>Cancel</GlassButton>
          <GlassButton type="submit" variant="primary" icon={<Save className="h-4 w-4" />}>Save Changes</GlassButton>
        </div>
      </form>
    </GlassModal>
  );
}
