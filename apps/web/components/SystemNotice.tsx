import React from 'react';
import { AlertTriangle, Cpu, FlaskConical, ShieldCheck } from 'lucide-react';

export const SystemNotice: React.FC = () => {
  return (
    <div className="mb-5 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-100/90 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex items-start gap-2">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
          <div>
            <span className="font-semibold text-amber-200">Human decision support only.</span>{' '}
            <span>CandidateX surfaces evidence, uncertainty, contradictions and interview probes. It does not autonomously hire or reject candidates.</span>
            <div className="mt-1 flex items-start gap-1.5 text-amber-100/70">
              <FlaskConical className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                Public demo candidates are controlled synthetic / demonstration records whenever a live backend is unavailable. Demo data must not be presented as a real candidate analysis.
              </span>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-amber-200/70 lg:shrink-0">
          <span className="flex items-center gap-1">
            <Cpu className="h-3.5 w-3.5" /> No untrusted code execution
          </span>
          <span className="flex items-center gap-1">
            <AlertTriangle className="h-3.5 w-3.5" /> Missing evidence ≠ zero capability
          </span>
        </div>
      </div>
    </div>
  );
};
