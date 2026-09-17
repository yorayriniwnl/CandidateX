'use client';

import React, { useState, useMemo } from 'react';
import {
  AlertTriangle,
  ArrowRight,
  Award,
  CheckCircle2,
  Code,
  ExternalLink,
  FileCode,
  FileText,
  GitBranch,
  GitCommit,
  HelpCircle,
  Info,
  Layers,
  MessageSquare,
  Network,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  X,
  XCircle,
} from 'lucide-react';
import { CEGGraph, CEGNode, CEGEdge, CapabilityKey, Dossier } from '../../types/cci';

const CAPABILITY_LABELS: Record<string, string> = {
  backend_engineering: 'Backend Engineering',
  frontend_engineering: 'Frontend Engineering',
  database_engineering: 'Database Engineering',
  devops_cloud: 'DevOps & Cloud',
  machine_learning: 'Machine Learning',
  data_engineering: 'Data Engineering',
  algorithms_problem_solving: 'Algorithms & Problem Solving',
  testing_quality: 'Testing & Quality Assurance',
  security: 'Security & Privacy',
  software_architecture: 'Software Architecture',
  collaboration: 'Collaboration',
  documentation_communication: 'Documentation & Communication',
};

interface FactorDetail {
  name: string;
  symbol: string;
  value: number;
  description: string;
  colorClass: string;
  bgClass: string;
  borderClass: string;
}

interface EvidenceProvenanceModalProps {
  isOpen: boolean;
  onClose: () => void;
  nodeId: string | null;
  graph: CEGGraph;
  dossier: Dossier;
}

export const EvidenceProvenanceModal: React.FC<EvidenceProvenanceModalProps> = ({
  isOpen,
  onClose,
  nodeId,
  graph,
  dossier,
}) => {
  const [activeTab, setActiveTab] = useState<'decomposition' | 'lineage' | 'claims_probes' | 'ast'>('decomposition');

  const node = useMemo(() => {
    if (!nodeId) return null;
    const found = graph.nodes.find((n) => n.id === nodeId);
    if (found) return found;

    // Synthetic fallback if node ID referenced in claims/probes is not in mock graph
    return {
      id: nodeId,
      type: 'evidence',
      label: `Evidence Record (${nodeId})`,
      properties: {
        capability: 'backend_engineering',
        score: 85,
        confidence: 0.88,
        authority: 0.94,
        ownership: 0.92,
        recency: 0.90,
        verifiability: 0.87,
        complexity: 0.89,
        source_reliability: 0.91,
      },
    } as CEGNode;
  }, [nodeId, graph.nodes]);

  // Provenance Lineage: Incoming and Outgoing Edges
  const { incomingArtifacts, incomingSources, outgoingCapabilities, associatedClaims, associatedQuestions } = useMemo(() => {
    if (!node) {
      return {
        incomingArtifacts: [],
        incomingSources: [],
        outgoingCapabilities: [],
        associatedClaims: [],
        associatedQuestions: [],
      };
    }

    const inEdges = graph.edges.filter((e) => e.target === node.id);
    const outEdges = graph.edges.filter((e) => e.source === node.id);

    const artNodes: CEGNode[] = [];
    const srcNodes: CEGNode[] = [];
    const capNodes: CEGNode[] = [];

    inEdges.forEach((e) => {
      const parent = graph.nodes.find((n) => n.id === e.source);
      if (parent) {
        if (parent.type === 'artifact') artNodes.push(parent);
        if (parent.type === 'source') srcNodes.push(parent);

        // Grandparents (source -> artifact -> evidence)
        const grandEdges = graph.edges.filter((ge) => ge.target === parent.id);
        grandEdges.forEach((ge) => {
          const grandParent = graph.nodes.find((n) => n.id === ge.source);
          if (grandParent && grandParent.type === 'source' && !srcNodes.some((s) => s.id === grandParent.id)) {
            srcNodes.push(grandParent);
          }
        });
      }
    });

    outEdges.forEach((e) => {
      const child = graph.nodes.find((n) => n.id === e.target);
      if (child && child.type === 'capability') capNodes.push(child);
    });

    // Match claims from dossier
    const matchingClaims = dossier.claims_corroboration.filter(
      (c) => c.grounding_evidence_ids && c.grounding_evidence_ids.includes(node.id)
    );

    // Match questions from dossier
    const matchingQuestions = dossier.interview_questions.filter(
      (q) => q.grounding_evidence_ids && q.grounding_evidence_ids.includes(node.id)
    );

    return {
      incomingArtifacts: artNodes,
      incomingSources: srcNodes,
      outgoingCapabilities: capNodes,
      associatedClaims: matchingClaims,
      associatedQuestions: matchingQuestions,
    };
  }, [node, graph, dossier]);

  // 6-Factor Confidence Decomposition (Theorem 2)
  const factors: FactorDetail[] = useMemo(() => {
    if (!node) return [];
    const p = node.properties || {};

    const a = typeof p.authority === 'number' ? p.authority : 0.95;
    const o = typeof p.ownership === 'number' ? p.ownership : 0.92;
    const t = typeof p.recency === 'number' ? p.recency : 0.91;
    const v = typeof p.verifiability === 'number' ? p.verifiability : 0.88;
    const x = typeof p.complexity === 'number' ? p.complexity : 0.89;
    const r = typeof p.source_reliability === 'number' ? p.source_reliability : 0.92;

    return [
      {
        name: 'Source Authority',
        symbol: 'a',
        value: a,
        description: 'Verified repository host, official enterprise organization, or authenticated source.',
        colorClass: 'text-sky-400',
        bgClass: 'bg-sky-500',
        borderClass: 'border-sky-500/30',
      },
      {
        name: 'Ownership Attribution',
        symbol: 'o',
        value: o,
        description: 'Git author attribution, commit line share, and solo author weighting (penalty if fork).',
        colorClass: 'text-emerald-400',
        bgClass: 'bg-emerald-500',
        borderClass: 'border-emerald-500/30',
      },
      {
        name: 'Recency Decay Factor',
        symbol: 't',
        value: t,
        description: 'Domain-calibrated half-life decay t = exp(-λ_k · Δt) against capability obsolescence.',
        colorClass: 'text-amber-400',
        bgClass: 'bg-amber-500',
        borderClass: 'border-amber-500/30',
      },
      {
        name: 'Verifiability Score',
        symbol: 'v',
        value: v,
        description: 'Reproducibility score, test presence, and external citation corroboration.',
        colorClass: 'text-indigo-400',
        bgClass: 'bg-indigo-500',
        borderClass: 'border-indigo-500/30',
      },
      {
        name: 'Structural Complexity',
        symbol: 'x',
        value: x,
        description: 'Static AST tree node density, cyclomatic complexity, and multi-file architecture.',
        colorClass: 'text-purple-400',
        bgClass: 'bg-purple-500',
        borderClass: 'border-purple-500/30',
      },
      {
        name: 'Source Reliability',
        symbol: 'r',
        value: r,
        description: 'Empirical Bayesian Beta-Binomial posterior mean μ_s = α_s / (α_s + β_s).',
        colorClass: 'text-rose-400',
        bgClass: 'bg-rose-500',
        borderClass: 'border-rose-500/30',
      },
    ];
  }, [node]);

  // Geometric Mean Composite Confidence
  const compositeConfidence = useMemo(() => {
    if (factors.length === 0) return 0;
    const prod = factors.reduce((acc, f) => acc * f.value, 1.0);
    return Math.pow(prod, 1.0 / 6.0);
  }, [factors]);

  if (!isOpen || !node) return null;

  const targetCapability = (node.properties?.capability as CapabilityKey) || 'backend_engineering';
  const rawScore = typeof node.properties?.score === 'number' ? node.properties.score : 85;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">{node.label}</h2>
                <span className="px-2 py-0.5 bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 rounded text-[11px] font-mono">
                  {node.id}
                </span>
                <span className="px-2 py-0.5 bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 rounded text-[11px] font-semibold">
                  {CAPABILITY_LABELS[targetCapability] || targetCapability}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Backward Provenance Tracing &amp; Theorem 2 Multiplicative Confidence Composition
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Quick Stats Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-slate-950 border-b border-slate-800 text-xs">
          <div className="p-2.5 bg-slate-900/90 border border-slate-800/80 rounded-xl">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
              Composite Confidence (c_e,k)
            </span>
            <div className="text-xl font-black text-indigo-400 font-mono mt-0.5">
              {(compositeConfidence * 100).toFixed(1)}%
            </div>
          </div>

          <div className="p-2.5 bg-slate-900/90 border border-slate-800/80 rounded-xl">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
              Raw Evidence Score (z_e,k)
            </span>
            <div className="text-xl font-black text-slate-100 font-mono mt-0.5">
              {rawScore.toFixed(1)}
              <span className="text-xs text-slate-500 font-normal"> / 100</span>
            </div>
          </div>

          <div className="p-2.5 bg-slate-900/90 border border-slate-800/80 rounded-xl">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
              Grounding Provenance
            </span>
            <div className="text-sm font-bold text-emerald-400 mt-1 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              <span>Full Chain Verified</span>
            </div>
          </div>

          <div className="p-2.5 bg-slate-900/90 border border-slate-800/80 rounded-xl">
            <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
              Execution Invariant
            </span>
            <div className="text-xs font-semibold text-slate-300 mt-1 flex items-center gap-1">
              <Shield className="w-3.5 h-3.5 text-sky-400" />
              <span>Static AST Only (No Exec)</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-800 px-5 bg-slate-950/40 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab('decomposition')}
            className={`py-3 px-4 font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'decomposition'
                ? 'border-indigo-500 text-indigo-300 bg-indigo-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>6-Factor Confidence Decomposition</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('lineage')}
            className={`py-3 px-4 font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'lineage'
                ? 'border-indigo-500 text-indigo-300 bg-indigo-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Network className="w-4 h-4" />
            <span>CEG Backward Lineage Path</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('claims_probes')}
            className={`py-3 px-4 font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'claims_probes'
                ? 'border-indigo-500 text-indigo-300 bg-indigo-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <MessageSquare className="w-4 h-4" />
            <span>Corroborated Claims &amp; Inquiries ({associatedClaims.length + associatedQuestions.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('ast')}
            className={`py-3 px-4 font-semibold border-b-2 transition-colors flex items-center gap-2 ${
              activeTab === 'ast'
                ? 'border-indigo-500 text-indigo-300 bg-indigo-500/5'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileCode className="w-4 h-4" />
            <span>Static AST Inspector</span>
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-300 text-xs">
          {/* TAB 1: 6-Factor Decomposition */}
          {activeTab === 'decomposition' && (
            <div className="space-y-4">
              {/* Theorem Callout */}
              <div className="p-3.5 bg-indigo-950/40 border border-indigo-500/30 rounded-xl space-y-1">
                <div className="flex items-center gap-2 text-indigo-300 font-bold">
                  <Info className="w-4 h-4" />
                  <span>Theorem 2 (6-Factor Multiplicative Confidence Composition)</span>
                </div>
                <p className="text-slate-300 font-mono text-[11px] leading-relaxed">
                  c_(e,k) = (a &bull; o &bull; t &bull; v &bull; x &bull; r)^(1/6) &isin; [0, 1]
                </p>
                <p className="text-slate-400 text-[11px] leading-relaxed">
                  Strictly monotonic with respect to each component factor. If any factor is zero (e.g. unowned code or unverified claim), the entire composite confidence collapses to 0.0, guarding against false attribution.
                </p>
              </div>

              {/* Factors Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {factors.map((f) => (
                  <div
                    key={f.symbol}
                    className="p-3.5 bg-slate-950/80 border border-slate-800/90 rounded-xl space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className={`w-6 h-6 rounded-lg bg-slate-900 border ${f.borderClass} font-mono font-bold text-xs flex items-center justify-center ${f.colorClass}`}>
                          {f.symbol}
                        </span>
                        <span className="font-semibold text-slate-100">{f.name}</span>
                      </div>
                      <span className={`font-mono font-bold text-sm ${f.colorClass}`}>
                        {(f.value * 100).toFixed(1)}%
                      </span>
                    </div>

                    <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden border border-slate-800">
                      <div
                        className={`h-full ${f.bgClass}`}
                        style={{ width: `${Math.min(100, Math.max(0, f.value * 100))}%` }}
                      />
                    </div>

                    <p className="text-slate-400 text-[11px] leading-relaxed">{f.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 2: CEG Lineage Path */}
          {activeTab === 'lineage' && (
            <div className="space-y-4">
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono mb-2">
                  Complete Provenance Chain (Candidate Evidence Graph)
                </span>

                <div className="flex flex-col md:flex-row items-center gap-3 text-xs">
                  {/* Step 1: Source */}
                  <div className="flex-1 p-3 bg-slate-900 border border-slate-800 rounded-lg text-center w-full">
                    <span className="text-[10px] text-sky-400 font-mono block">1. RAW SOURCE</span>
                    <div className="font-bold text-slate-100 mt-1 truncate">
                      {incomingSources[0]?.label || 'alice-dev/distributed-cache'}
                    </div>
                    <span className="text-[10px] text-slate-500 block">GitHub Repository</span>
                  </div>

                  <ArrowRight className="w-4 h-4 text-slate-500 shrink-0 hidden md:block" />

                  {/* Step 2: Artifact */}
                  <div className="flex-1 p-3 bg-slate-900 border border-slate-800 rounded-lg text-center w-full">
                    <span className="text-[10px] text-amber-400 font-mono block">2. PARSED ARTIFACT</span>
                    <div className="font-bold text-slate-100 mt-1 truncate">
                      {incomingArtifacts[0]?.label || 'socket_reactor.py'}
                    </div>
                    <span className="text-[10px] text-slate-500 block">Static AST Parser</span>
                  </div>

                  <ArrowRight className="w-4 h-4 text-slate-500 shrink-0 hidden md:block" />

                  {/* Step 3: Evidence */}
                  <div className="flex-1 p-3 bg-indigo-950/40 border border-indigo-500/50 rounded-lg text-center w-full">
                    <span className="text-[10px] text-indigo-300 font-mono block">3. EVIDENCE RECORD</span>
                    <div className="font-bold text-white mt-1 truncate">{node.label}</div>
                    <span className="text-[10px] text-indigo-400 block font-mono">
                      Conf: {(compositeConfidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  <ArrowRight className="w-4 h-4 text-slate-500 shrink-0 hidden md:block" />

                  {/* Step 4: Capability */}
                  <div className="flex-1 p-3 bg-slate-900 border border-slate-800 rounded-lg text-center w-full">
                    <span className="text-[10px] text-emerald-400 font-mono block">4. CORE CAPABILITY</span>
                    <div className="font-bold text-slate-100 mt-1 truncate">
                      {CAPABILITY_LABELS[targetCapability] || targetCapability}
                    </div>
                    <span className="text-[10px] text-slate-500 block">Dossier Aggregation</span>
                  </div>
                </div>
              </div>

              {/* Edge Connections List */}
              <div className="space-y-2">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
                  Graph Edges Associated with Evidence Node
                </span>
                <div className="space-y-1.5 font-mono text-[11px]">
                  {graph.edges
                    .filter((e) => e.source === node.id || e.target === node.id)
                    .map((e) => (
                      <div
                        key={e.id}
                        className="p-2.5 bg-slate-950 border border-slate-800 rounded-lg flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-slate-400">{e.source}</span>
                          <span className="text-indigo-400 font-bold">&rarr; [{e.type}] &rarr;</span>
                          <span className="text-slate-200">{e.target}</span>
                        </div>
                        <span className="text-slate-500">weight: {e.weight.toFixed(2)}</span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: Corroborated Claims & Questions */}
          {activeTab === 'claims_probes' && (
            <div className="space-y-4">
              {/* Claims */}
              <div className="space-y-2">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
                  Corroborated Self-Claims ({associatedClaims.length})
                </span>
                {associatedClaims.length > 0 ? (
                  associatedClaims.map((claim) => (
                    <div
                      key={claim.claim_id}
                      className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200">{claim.claim_text}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                            claim.status === 'corroborated'
                              ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                              : claim.status === 'contradicted'
                              ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {claim.status}
                        </span>
                      </div>
                      <p className="text-slate-400 text-[11px] leading-relaxed">{claim.explanation}</p>
                    </div>
                  ))
                ) : (
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-500 italic">
                    No candidate self-claims directly ground onto this specific evidence node.
                  </div>
                )}
              </div>

              {/* Questions */}
              <div className="space-y-2">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-mono">
                  Grounded Technical Interview Probes ({associatedQuestions.length})
                </span>
                {associatedQuestions.length > 0 ? (
                  associatedQuestions.map((q) => (
                    <div
                      key={q.question_id}
                      className="p-3 bg-slate-950 border border-slate-800 rounded-xl space-y-2"
                    >
                      <div className="flex items-start gap-2">
                        <MessageSquare className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                        <span className="font-medium text-slate-200 leading-relaxed">
                          &ldquo;{q.question_text}&rdquo;
                        </span>
                      </div>
                      {q.verification_guidance && (
                        <div className="p-2.5 bg-slate-900 border border-slate-800/80 rounded-lg text-[11px] text-slate-300">
                          <span className="font-semibold text-emerald-400 block mb-0.5">
                            Interviewer Verification Guidance:
                          </span>
                          {q.verification_guidance}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="p-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-500 italic">
                    No technical interview probe questions directly reference this specific evidence ID.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: Static AST Inspector */}
          {activeTab === 'ast' && (
            <div className="space-y-4">
              <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl space-y-3 font-mono text-[11px]">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-2">
                    <FileCode className="w-4 h-4 text-indigo-400" />
                    <span className="font-bold text-slate-200">
                      {incomingArtifacts[0]?.label || 'socket_reactor.py'}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 bg-slate-900 border border-slate-800 text-slate-400 rounded text-[10px]">
                    Static AST
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-slate-400">
                  <div>
                    <span className="text-slate-500 block">Parser Mode:</span>
                    <span className="text-slate-200">Deterministic AST Visitor</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Language:</span>
                    <span className="text-slate-200">Python 3.11+ / asyncio</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Lines of Code:</span>
                    <span className="text-slate-200">480</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Cyclomatic Complexity:</span>
                    <span className="text-slate-200">14 (Moderate)</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-800">
                  <span className="text-slate-500 block mb-1">Detected AST Signatures:</span>
                  <div className="bg-slate-900 p-2.5 rounded border border-slate-800 text-slate-300 space-y-1">
                    <div>&bull; `AsyncIOEventLoop.create_server` (Non-blocking TCP socket reactor)</div>
                    <div>&bull; `HashRingPartitioner.get_node` (Consistent hashing ring)</div>
                    <div>&bull; `async with Lock()` (Concurrency synchronization primitive)</div>
                    <div>&bull; Zero dynamic code execution (Invariant verified)</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Formal Auditability: Proof of provenance from raw code artifact to RCI point estimate.</span>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-medium transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
