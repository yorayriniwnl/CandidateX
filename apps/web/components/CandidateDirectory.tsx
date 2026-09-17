'use client';

import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Award,
  Check,
  CheckCircle2,
  ExternalLink,
  Filter,
  GitCompare,
  Plus,
  Search,
  Sparkles,
  Users,
  X,
} from 'lucide-react';
import { CandidateSummary, fetchCandidatesList } from '../lib/api';
import { CanonicalRole } from '../types/cci';

const FALLBACK_CANDIDATES: CandidateSummary[] = [
  {
    id: '11111111-1111-1111-1111-111111111111',
    display_name: 'Alice Chen',
    primary_email: 'alice.chen@example.com',
    has_completed_dossier: true,
    rci: 90.0,
    coverage: 0.18,
    role: 'backend',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '22222222-2222-2222-2222-222222222222',
    display_name: 'Elena Rostova',
    primary_email: 'elena.rostova@example.com',
    has_completed_dossier: true,
    rci: 86.0,
    coverage: 0.182,
    role: 'frontend',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '33333333-3333-3333-3333-333333333333',
    display_name: 'Dr. Marcus Thorne',
    primary_email: 'marcus.thorne@example.com',
    has_completed_dossier: true,
    rci: 88.0,
    coverage: 0.18,
    role: 'ml_engineer',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '44444444-4444-4444-4444-444444444444',
    display_name: 'Tariq Mansour',
    primary_email: 'tariq.mansour@example.com',
    has_completed_dossier: true,
    rci: 89.0,
    coverage: 0.18,
    role: 'devops_cloud',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '55555555-5555-5555-5555-555555555555',
    display_name: "Samuel O'Connor",
    primary_email: 'samuel.oconnor@example.com',
    has_completed_dossier: true,
    rci: 89.0,
    coverage: 0.18,
    role: 'fullstack',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '66666666-6666-6666-6666-666666666666',
    display_name: 'Jordan Blake',
    primary_email: 'jordan.blake@example.com',
    has_completed_dossier: true,
    rci: 62.0,
    coverage: 0.0,
    role: 'backend',
    has_meaningful_conflict: false,
    created_at: new Date().toISOString(),
  },
  {
    id: '77777777-7777-7777-7777-777777777777',
    display_name: 'Devin Vance',
    primary_email: 'devin.vance@example.com',
    has_completed_dossier: true,
    rci: 69.9,
    coverage: 0.0,
    role: 'backend',
    has_meaningful_conflict: true,
    created_at: new Date().toISOString(),
  },
];

const ROLE_LABELS: Record<string, { label: string; color: string }> = {
  backend: { label: 'Backend', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30' },
  frontend: { label: 'Frontend', color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30' },
  ml_engineer: { label: 'ML Engineer', color: 'bg-purple-500/20 text-purple-300 border-purple-500/30' },
  devops_cloud: { label: 'DevOps / SRE', color: 'bg-sky-500/20 text-sky-300 border-sky-500/30' },
  fullstack: { label: 'Fullstack', color: 'bg-teal-500/20 text-teal-300 border-teal-500/30' },
  data_engineer: { label: 'Data Engineer', color: 'bg-amber-500/20 text-amber-300 border-amber-500/30' },
};

export const CandidateDirectory: React.FC<{
  onSelectCandidate: (candidateId: string, name: string) => void;
  onNewCandidate: () => void;
  isBackendOnline: boolean | null;
  onCompareCandidates?: (candidateIds: string[]) => void;
  initialSelectedForComparison?: string[];
}> = ({
  onSelectCandidate,
  onNewCandidate,
  isBackendOnline,
  onCompareCandidates,
  initialSelectedForComparison,
}) => {
  const [candidates, setCandidates] = useState<CandidateSummary[]>(FALLBACK_CANDIDATES);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRole, setSelectedRole] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<
    'rci_desc' | 'rci_asc' | 'coverage_desc' | 'name_asc' | 'conflict_first'
  >('rci_desc');
  const [selectedForComparison, setSelectedForComparison] = useState<string[]>(
    initialSelectedForComparison || []
  );
  const [loadingCandidateId, setLoadingCandidateId] = useState<string | null>(null);

  useEffect(() => {
    if (initialSelectedForComparison && initialSelectedForComparison.length > 0) {
      setSelectedForComparison(initialSelectedForComparison);
    }
  }, [initialSelectedForComparison]);

  useEffect(() => {
    if (isBackendOnline) {
      fetchCandidatesList()
        .then((data) => {
          if (data && data.length > 0) {
            setCandidates(data);
          }
        })
        .catch(() => {
          // Graceful fallback to default candidates
        });
    }
  }, [isBackendOnline]);

  const toggleSelectForComparison = (id: string) => {
    setSelectedForComparison((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      }
      if (prev.length >= 3) {
        // Max 3 candidates for side-by-side comparison: drop oldest, add new
        return [...prev.slice(1), id];
      }
      return [...prev, id];
    });
  };

  const filteredCandidates = candidates
    .filter((c) => {
      const matchesSearch =
        c.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (c.primary_email && c.primary_email.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesRole = selectedRole === 'all' || c.role === selectedRole;

      let matchesStatus = true;
      if (selectedStatus === 'conflict') {
        matchesStatus = c.has_meaningful_conflict;
      } else if (selectedStatus === 'sparse') {
        matchesStatus = c.coverage !== undefined && c.coverage < 0.10;
      } else if (selectedStatus === 'robust') {
        matchesStatus = !c.has_meaningful_conflict && (c.coverage === undefined || c.coverage >= 0.10);
      }

      return matchesSearch && matchesRole && matchesStatus;
    })
    .sort((a, b) => {
      if (sortBy === 'rci_desc') {
        return (b.rci ?? -1) - (a.rci ?? -1);
      }
      if (sortBy === 'rci_asc') {
        return (a.rci ?? 999) - (b.rci ?? 999);
      }
      if (sortBy === 'coverage_desc') {
        return (b.coverage ?? 0) - (a.coverage ?? 0);
      }
      if (sortBy === 'name_asc') {
        return a.display_name.localeCompare(b.display_name);
      }
      if (sortBy === 'conflict_first') {
        return (b.has_meaningful_conflict ? 1 : 0) - (a.has_meaningful_conflict ? 1 : 0);
      }
      return 0;
    });

  const handleInspect = async (candidateId: string, name: string) => {
    setLoadingCandidateId(candidateId);
    try {
      await onSelectCandidate(candidateId, name);
    } finally {
      setLoadingCandidateId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/10 rounded-lg text-indigo-400">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">Candidate Evaluation Directory</h2>
            <p className="text-xs text-slate-400">
              Evaluated technical cohorts with immutable dossiers, RCI ratings, and contradiction diagnostics
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onNewCandidate}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition-colors flex items-center gap-2 shadow-lg shadow-indigo-600/20 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          Intake New Candidate
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by candidate name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedRole}
              onChange={(e) => setSelectedRole(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Canonical Roles</option>
              <option value="backend">Backend</option>
              <option value="frontend">Frontend</option>
              <option value="ml_engineer">ML Engineer</option>
              <option value="devops_cloud">DevOps / SRE</option>
              <option value="fullstack">Fullstack</option>
            </select>

            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Evidence States</option>
              <option value="robust">Robust Evidence</option>
              <option value="sparse">Sparse Warning</option>
              <option value="conflict">Conflict Flagged (D_k &lt; 0)</option>
            </select>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="rci_desc">Sort: RCI (High &rarr; Low)</option>
              <option value="rci_asc">Sort: RCI (Low &rarr; High)</option>
              <option value="coverage_desc">Sort: Coverage (High &rarr; Low)</option>
              <option value="name_asc">Sort: Name (A &rarr; Z)</option>
              <option value="conflict_first">Sort: Contradictions First</option>
            </select>
          </div>
        </div>
      </div>

      {/* Candidate Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredCandidates.map((candidate) => {
          const roleMeta = ROLE_LABELS[candidate.role || 'backend'] || {
            label: candidate.role || 'Unknown',
            color: 'bg-slate-800 text-slate-300 border-slate-700',
          };
          const isInspecting = loadingCandidateId === candidate.id;
          const isSelectedForCompare = selectedForComparison.includes(candidate.id);

          return (
            <div
              key={candidate.id}
              className={`bg-slate-900 border transition-all rounded-xl p-5 space-y-4 flex flex-col justify-between shadow-lg ${
                isSelectedForCompare
                  ? 'border-indigo-500 ring-2 ring-indigo-500/40 bg-slate-900/90'
                  : 'border-slate-800 hover:border-slate-700'
              }`}
            >
              <div>
                {/* Header with Name, Compare Toggle & Role Badge */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div>
                    <h3 className="text-base font-semibold text-slate-100">{candidate.display_name}</h3>
                    <p className="text-xs text-slate-400">{candidate.primary_email || 'No email declared'}</p>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => toggleSelectForComparison(candidate.id)}
                      className={`px-2 py-0.5 rounded text-[10px] font-medium border flex items-center gap-1 transition-all ${
                        isSelectedForCompare
                          ? 'bg-indigo-600 border-indigo-400 text-white shadow-sm'
                          : 'bg-slate-950/80 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                      }`}
                      title={isSelectedForCompare ? 'Remove from comparison' : 'Add to side-by-side comparison (max 3)'}
                    >
                      <GitCompare className="w-3 h-3" />
                      <span>{isSelectedForCompare ? 'Selected' : 'Compare'}</span>
                    </button>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase border ${roleMeta.color}`}>
                      {roleMeta.label}
                    </span>
                  </div>
                </div>

                {/* Score & Diagnostics Badges */}
                <div className="mt-4 grid grid-cols-2 gap-2 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                  <div>
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Role Capability Index</span>
                    <span className="text-lg font-bold text-slate-100">
                      {candidate.rci !== null && candidate.rci !== undefined ? `${candidate.rci.toFixed(1)}` : 'UNKNOWN'}
                    </span>
                    <span className="text-[11px] text-slate-500"> / 100</span>
                  </div>

                  <div>
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Evidence Coverage</span>
                    <span className="text-lg font-bold text-indigo-400">
                      {candidate.coverage !== null && candidate.coverage !== undefined ? `${(candidate.coverage * 100).toFixed(1)}%` : '0.0%'}
                    </span>
                  </div>
                </div>

                {/* Conflict or Warning Notice */}
                {candidate.has_meaningful_conflict && (
                  <div className="mt-3 flex items-center gap-2 p-2 bg-rose-500/10 border border-rose-500/30 rounded-lg text-xs text-rose-300">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                    <span>Contradiction flagged (D_k &lt; 0) between claims and repository observations</span>
                  </div>
                )}

                {!candidate.has_meaningful_conflict && candidate.coverage !== undefined && candidate.coverage < 0.10 && (
                  <div className="mt-3 flex items-center gap-2 p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-300">
                    <Sparkles className="w-4 h-4 shrink-0 text-amber-400" />
                    <span>Sparse evidence cohort: Missing capabilities remain UNKNOWN</span>
                  </div>
                )}
              </div>

              {/* Action Button */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <span className="text-[11px] text-slate-500 font-mono">
                  ID: {candidate.id.slice(0, 8)}...
                </span>

                <button
                  type="button"
                  onClick={() => handleInspect(candidate.id, candidate.display_name)}
                  disabled={isInspecting}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5 shadow-sm shadow-indigo-600/30"
                >
                  <Award className="w-3.5 h-3.5" />
                  {isInspecting ? 'Loading Dossier...' : 'View Dossier'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {filteredCandidates.length === 0 && (
        <div className="text-center py-12 bg-slate-900 border border-slate-800 rounded-xl">
          <Users className="w-8 h-8 text-slate-500 mx-auto mb-2" />
          <p className="text-sm text-slate-300 font-medium">No candidates match the selected filters</p>
          <p className="text-xs text-slate-500 mt-1">Try broadening your search query or role filter.</p>
        </div>
      )}

      {/* Floating Comparison Action Bar */}
      {selectedForComparison.length > 0 && onCompareCandidates && (
        <div className="fixed bottom-6 inset-x-0 mx-auto max-w-2xl px-4 z-40 animate-in fade-in slide-in-from-bottom-4 duration-200">
          <div className="bg-slate-900/95 border border-indigo-500/50 rounded-2xl p-4 shadow-2xl backdrop-blur-md flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-600 text-white rounded-xl shadow-md">
                <GitCompare className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">
                    Compare Candidates ({selectedForComparison.length} / 3)
                  </span>
                  <span className="text-[11px] text-indigo-300 font-mono">
                    Side-by-Side Matrix
                  </span>
                </div>
                <div className="text-xs text-slate-400 flex flex-wrap items-center gap-1.5 mt-1">
                  {selectedForComparison.map((id) => {
                    const cand = candidates.find((c) => c.id === id);
                    return (
                      <span
                        key={id}
                        className="px-2 py-0.5 bg-slate-950 border border-slate-800 rounded text-slate-300 text-[11px] font-medium"
                      >
                        {cand?.display_name || id.slice(0, 8)}
                      </span>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => setSelectedForComparison([])}
                className="px-3 py-1.5 text-xs text-slate-400 hover:text-white rounded-lg transition-colors"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={() => onCompareCandidates(selectedForComparison)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-indigo-600/30 flex items-center gap-1.5 transition-colors"
              >
                <span>Compare Now</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
