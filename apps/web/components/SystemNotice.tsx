import React from 'react';
import { AlertTriangle, ShieldCheck, Cpu, FlaskConical } from 'lucide-react';

export const SystemNotice: React.FC = () => {
  return (
    <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-xs text-amber-200/90 flex flex-col gap-2 shadow-sm">
      <div className="flex flex-col xl:flex-row items-start xl:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-amber-400 shrink-0" />
          <span className="font-semibold text-amber-300">Decision Support System:</span>
          <span>CCI provides grounded evidence for human technical interviewers; it does NOT make autonomous hiring decisions.</span>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-amber-400/80 shrink-0">
          <span className="flex items-center gap-1">
            <Cpu className="w-3.5 h-3.5" /> Zero Code Execution
          </span>
          <span className="flex items-center gap-1">
            <AlertTriangle className="w-3.5 h-3.5" /> Missing != Zero Capability
          </span>
        </div>
      </div>
      <div className="flex items-start gap-2 border-t border-amber-500/20 pt-2 text-amber-100/75">
        <FlaskConical className="w-3.5 h-3.5 text-amber-400 mt-0.5 shrink-0" />
        <span><strong className="text-amber-300">Research boundary:</strong> the N=4,800 ablation cohort is a synthetic Monte Carlo simulation for internal model-behavior testing. It is not validation on real applicants, hiring outcomes, job performance, or fairness.</span>
      </div>
    </div>
  );
};
