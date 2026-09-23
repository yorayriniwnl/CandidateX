'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  BookOpen,
  Calculator,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Code,
  Download,
  ExternalLink,
  Flame,
  GraduationCap,
  Layers,
  RotateCcw,
  Scale,
  Shield,
  ShieldAlert,
  Sparkles,
  Split,
  Table,
} from 'lucide-react';
import {
  TheoremMetadata,
  AblationStudyResponse,
  AblationRow,
  RoleBreakdownRow,
} from '../types/cci';
import { fetchTheorems, fetchAblationStudy, calculateTheoremMath } from '../lib/api';

const DEFAULT_THEOREMS: TheoremMetadata[] = [
  {
    id: 1,
    name: 'Recency Decay Monotonicity & Asymptotics',
    category: 'Calibration & Recency',
    latex_formula: 't(\\Delta t, k) = \\exp(-\\lambda_k \\cdot \\Delta t)',
    description: 'Exponential decay factor discounting evidence based on elapsed months since observation.',
    bound_statement: 't \\in (0, 1], \\quad t(0) = 1.0, \\quad \\lim_{\\Delta t \\to \\infty} t = 0.0',
    physical_intuition: 'Fast-evolving domains (Frontend, ML) decay strictly faster than foundational algorithms and data structures.',
    key_properties: [
      'Strict monotonicity: dt/d(Delta t) < 0 for all Delta t > 0',
      'Identity factor 1.0 at Delta t = 0',
      'Domain-specific decay rate lambda_k > 0',
    ],
  },
  {
    id: 2,
    name: 'Attribution-Gated Evidence Weight Boundedness',
    category: 'Scoring & Calibration',
    latex_formula: 'c_{e,k} = o \\cdot (a \\cdot t \\cdot v \\cdot x \\cdot r)^{1/5}',
    description: 'Direct account-attribution gate multiplied by the geometric mean of five evidence-quality factors.',
    bound_statement: 'c_{e,k} \\in [0, o], \\quad o = 0 \\implies c_{e,k} = 0',
    physical_intuition: 'Weak path attribution remains weak: evidence quality cannot raise its weight above the attribution ratio.',
    key_properties: [
      'Zero attribution forces zero evidence weight',
      'Increasing any attribution or evidence-quality factor increases the weight',
      'The geometric mean treats the five quality factors symmetrically; attribution is the direct gate',
    ],
  },
  {
    id: 3,
    name: 'Point Estimate Convexity & Range Preservation',
    category: 'Scoring & Calibration',
    latex_formula: 'q_k = \\frac{\\sum_{e} c_{e,k} z_{e,k}}{\\sum_{e} c_{e,k}}',
    description: 'The candidate estimate is a confidence-weighted convex combination gated by cluster-aware attribution-gated coverage (0.35 minimum by default); unique artifacts count once per source-family cluster with geometric diminishing returns.',
    bound_statement: 'q_k \\in [\\min z_e, \\max z_e] \\subseteq [0, 100]',
    physical_intuition: 'Point estimate is strictly bounded within the support of concrete empirical evidence scores.',
    key_properties: [
      'Convex combination ensures stability against extreme outlier amplification',
      'Constant inputs z_e = z_0 produce q_k = z_0',
      'Missing or undercovered evidence produces UNKNOWN, never 0.0',
    ],
  },
  {
    id: 4,
    name: 'Kish Effective Sample Size',
    category: 'Uncertainty & Sample Size',
    latex_formula: 'n_{\\text{eff},k} = \\frac{(\\sum c_{e,k})^2}{\\sum c_{e,k}^2}',
    description: 'Measures statistical information content accounting for non-uniform confidence dispersion.',
    bound_statement: '1.0 \\le n_{\\text{eff},k} \\le N, \\quad n_{\\text{eff},k} = N \\iff c_1 = \\dots = c_N',
    physical_intuition: 'Kish effective count measures relative weight inequality. Equal weights have effective count N, even when every confidence is low. Coverage separately reflects absolute confidence.',
    key_properties: [
      'Reported separately from project-cluster bootstrap intervals',
      'Strictly penalized by high confidence inequality across evidence items',
      'Upper-bounded by raw observation count N',
    ],
  },
  {
    id: 5,
    name: 'Softmax Role Weights Invariance & Normalization',
    category: 'Role Calibration',
    latex_formula: 'w_k = \\frac{\\exp(u_k / T)}{\\sum_{j=1}^{12} \\exp(u_j / T)}',
    description: 'Normalizes raw requirement importance vectors into a convex role weight distribution.',
    bound_statement: '\\sum_{k=1}^{12} w_k = 1.0, \\quad w_k > 0, \\quad w_k(u + C) = w_k(u)',
    physical_intuition: 'Translates hiring committee priorities smoothly without numerical instability or arbitrary scaling bias.',
    key_properties: [
      'Shift-invariance under uniform utility shifts (u_k + C)',
      'Temperature parameter T controls peakiness vs uniformity',
      'Guarantees positive weight for all 12 canonical capabilities',
    ],
  },
  {
    id: 6,
    name: 'Role Capability Index (RCI) Boundedness',
    category: 'Scoring & Aggregation',
    latex_formula: '\\text{RCI} = 100 \\cdot \\frac{\\sum_{k \\in \\mathcal{O}} w_k q_k}{\\sum_{k \\in \\mathcal{O}} w_k}',
    description: 'Composite score aggregating capabilities that meet the configured minimum attribution-gated coverage.',
    bound_statement: '\\text{RCI} \\in [0, 100], \\quad \\forall k \\in \\mathcal{O}: q_k = q_0 \\implies \\text{RCI} = q_0',
    physical_intuition: 'Provides a comparable scalar indicator while explicitly separating capability depth from evidence coverage.',
    key_properties: [
      'Only sufficiently supported candidate estimates enter the observed role weight mass',
      'Preserves convex bounds of underlying point estimates',
      'Pure functional rescoring operates without re-crawling repositories',
    ],
  },
  {
    id: 7,
    name: 'Contradiction Diagnostic Boundedness & Neutrality',
    category: 'Uncertainty & Contradiction',
    latex_formula: 'D_k = \\frac{P_k - N_k}{P_k + N_k + \\epsilon}',
    description: 'Measures directional support balance between positive evidence (P_k) and negative/deficiency evidence (N_k).',
    bound_statement: 'D_k \\in [-1.0, +1.0], \\quad P_k = N_k \\implies D_k = 0.0',
    physical_intuition: 'Identifies conflicting technical evidence (e.g. claiming expert Go on CV vs 0 Go repositories or failed AST tests).',
    key_properties: [
      'Symmetric zero point: balanced positive and negative evidence yields D_k = 0',
      'Never silently averages away conflicting signals',
      'Simultaneous high positive and high negative support flags critical interview probe',
    ],
  },
  {
    id: 8,
    name: 'Information-Theoretic Probe Priority Monotonicity',
    category: 'Interview Probes',
    latex_formula: 'I_k = w_k [0.40(1-Cov_k) + 0.35 CIwidth_k + 0.25 Conf_k]',
    description: 'Ranks technical interview inquiries by potential information gain to maximize interview ROI.',
    bound_statement: '\\frac{\\partial I_k}{\\partial (1 - \\text{Cov}_k)} > 0, \\quad I_k \\ge 0',
    physical_intuition: 'Directs interviewers to probe high-weight unverified requirements and active contradictions first.',
    key_properties: [
      'Strictly increases with coverage gap (1 - Cov_k)',
      'Scales with candidate dispersion and contradiction severity',
      'Grounds auto-generated inquiry questions directly in concrete evidence IDs',
    ],
  },
  {
    id: 9,
    name: 'Beta-Binomial Source Reliability Consistency',
    category: 'Calibration & Bayesian Updates',
    latex_formula: '\\mathbb{E}[r_s | \\alpha_s, \\beta_s, k, n] = \\frac{\\alpha_s + k}{\\alpha_s + \\beta_s + n}',
    description: 'Empirical Bayesian update calibrating repository and platform source reliability over time.',
    bound_statement: '\\lim_{n \\to \\infty} \\mathbb{E}[r_s] = \\frac{k}{n} \\in [0, 1]',
    physical_intuition: 'Maintains prior stability while converging to empirical verification success rates.',
    key_properties: [
      'Conjugate Beta prior provides closed-form deterministic updates',
      'Immutable audit trail logs every posterior parameter change',
      'Prevents single malicious/spam repositories from poisoning global prior',
    ],
  },
  {
    id: 10,
    name: 'Platform Security & Governance Invariants',
    category: 'Security & Invariants',
    latex_formula: '\\text{Exec}(C_{\\text{untrusted}}) = \\emptyset \\quad \\land \\quad \\text{Decision}(CCI) = \\text{SupportOnly}',
    description: 'Formal commitments ensuring safe execution, candidate privacy, and decision support ethics.',
    bound_statement: '\\text{Status}(e_{\\text{missing}}) = \\text{UNKNOWN} \\ne 0.0',
    physical_intuition: 'The platform strictly parses static ASTs without code execution, never auto-rejects candidates, and treats missing evidence as unknown.',
    key_properties: [
      'Zero dynamic code execution: static deterministic AST parsers only',
      'Missing evidence produces UNKNOWN / lower coverage, never 0.0 score',
      'Employer decision support only: autonomous hire/reject is prohibited',
      'SSRF defense with DNS pinning and cloud metadata (169.254.169.254) isolation',
    ],
  },
];

const DEFAULT_ABLATION_MODELS: AblationRow[] = [
  {
    model_name: 'FULL_CCI',
    display_name: 'Full CCI (Proposed Architecture)',
    mae: 1.256,
    rmse: 1.620,
    spearman_rho: 0.979,
    kendall_tau: 0.876,
    statistical_significance: 'Baseline',
    is_baseline: true,
  },
  {
    model_name: 'NO_RECENCY_DECAY',
    display_name: 'Ablation A: Without Recency Decay',
    mae: 1.260,
    rmse: 1.615,
    spearman_rho: 0.976,
    kendall_tau: 0.869,
    statistical_significance: 'p = 0.0015',
  },
  {
    model_name: 'NO_OWNERSHIP_DISCOUNT',
    display_name: 'Ablation B: Without Ownership Discount',
    mae: 2.313,
    rmse: 2.954,
    spearman_rho: 0.940,
    kendall_tau: 0.791,
    statistical_significance: 'p < 0.001 (***)',
  },
  {
    model_name: 'UNIFORM_WEIGHTS',
    display_name: 'Ablation C: Uniform Role Weights (1/12)',
    mae: 1.958,
    rmse: 2.513,
    spearman_rho: 0.963,
    kendall_tau: 0.836,
    statistical_significance: 'p < 0.001 (***)',
  },
  {
    model_name: 'UNCALIBRATED_SOURCES',
    display_name: 'Ablation D: Uncalibrated Sources',
    mae: 1.325,
    rmse: 1.721,
    spearman_rho: 0.977,
    kendall_tau: 0.869,
    statistical_significance: 'p < 0.001 (***)',
  },
];

const DEFAULT_ROLE_BREAKDOWN: RoleBreakdownRow[] = [];

export const ResearchTheoremsExplorer: React.FC<{
  isBackendOnline?: boolean | null;
}> = ({ isBackendOnline }) => {
  const [subTab, setSubTab] = useState<'theorems' | 'ablation'>('theorems');
  const [theorems, setTheorems] = useState<TheoremMetadata[]>(DEFAULT_THEOREMS);
  const [ablationData, setAblationData] = useState<AblationStudyResponse | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [expandedTheoremId, setExpandedTheoremId] = useState<number | null>(2);

  // Live Theorem 1 (Recency) Simulator State
  const [t1DeltaT, setT1DeltaT] = useState<number>(18.0);
  const [t1Domain, setT1Domain] = useState<'fast' | 'mid' | 'foundational'>('fast');
  const t1Lambda = t1Domain === 'fast' ? 0.05 : t1Domain === 'mid' ? 0.03 : 0.01;
  const t1DecayFactor = Math.exp(-t1Lambda * t1DeltaT);

  // Live Theorem 2 (Attribution-Gated Confidence) Simulator State
  const [t2Authority, setT2Authority] = useState<number>(0.92);
  const [t2Ownership, setT2Ownership] = useState<number>(0.88);
  const [t2Recency, setT2Recency] = useState<number>(0.85);
  const [t2Verifiability, setT2Verifiability] = useState<number>(0.90);
  const [t2Complexity, setT2Complexity] = useState<number>(0.82);
  const [t2Reliability, setT2Reliability] = useState<number>(0.94);

  const t2QualityProduct = t2Authority * t2Recency * t2Verifiability * t2Complexity * t2Reliability;
  const t2EvidenceQuality = t2QualityProduct > 0 ? Math.pow(t2QualityProduct, 1 / 5) : 0;
  const t2Composite = t2Ownership * t2EvidenceQuality;
  const t2ZeroCollapsed = t2Composite === 0;

  // Live Theorem 7 (Contradiction D_k) Simulator State
  const [t7Positive, setT7Positive] = useState<number>(3.5);
  const [t7Negative, setT7Negative] = useState<number>(0.8);
  const t7Denom = t7Positive + t7Negative + 0.0001;
  const t7Dk = (t7Positive - t7Negative) / t7Denom;

  // Load from backend if available
  useEffect(() => {
    if (isBackendOnline) {
      fetchTheorems()
        .then((res) => setTheorems(res))
        .catch(() => {});

      fetchAblationStudy()
        .then((res) => setAblationData(res))
        .catch(() => {});
    }
  }, [isBackendOnline]);

  const categories = useMemo(() => {
    const set = new Set(theorems.map((t) => t.category));
    return ['all', ...Array.from(set)];
  }, [theorems]);

  const filteredTheorems = useMemo(() => {
    if (selectedCategory === 'all') return theorems;
    return theorems.filter((t) => t.category === selectedCategory);
  }, [theorems, selectedCategory]);

  const handleDownloadLatex = () => {
    const content =
      ablationData?.latex_table ||
      `\\begin{table}[t]
\\centering
\\caption{Model Architecture Ablation Study ($N = 4,800$, 6 roles, 16 seeds).}
\\label{tab:ablation_study}
\\begin{tabular}{lcccc}
\\toprule
\\textbf{Evaluation Model} & \\textbf{MAE} $\\downarrow$ & \\textbf{RMSE} $\\downarrow$ & \\textbf{Spearman $\\rho$} $\\uparrow$ & \\textbf{Kendall $\\tau$} $\\uparrow$ \\\\
\\midrule
Full CCI (Proposed) & \\textbf{1.256} & \\textbf{1.620} & \\textbf{0.979} & \\textbf{0.876} \\\\
w/o Recency Decay & 1.260 & 1.615 & 0.976 & 0.869 \\\\
w/o Ownership Discount & 2.313$^{\\ast\\ast\\ast}$ & 2.954 & 0.940 & 0.791 \\\\
Uniform Role Weights (1/12) & 1.958$^{\\ast\\ast\\ast}$ & 2.513 & 0.963 & 0.836 \\\\
Uncalibrated Sources & 1.325$^{\\ast\\ast\\ast}$ & 1.721 & 0.976 & 0.869 \\\\
\\multicolumn{5}{l}{\\footnotesize $^{\\ast\\ast\\ast}p < 0.001$ via candidate-paired Wilcoxon signed-rank test against Full CCI.}\\\\
\\multicolumn{5}{l}{\\footnotesize Scoring config 4.0.0; candidate estimates require $\\mathrm{Cov}_k \\ge 0.35$; within-cluster artifact decay $\\delta=0.50$; lower coverage is UNKNOWN.}
\\bottomrule
\\end{tabular}
\\end{table}`;

    const blob = new Blob([content], { type: 'text/x-tex;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'table_ablation_study.tex');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadMarkdown = () => {
    const content =
      ablationData?.markdown_table ||
      `# Executable Prototype Experiment - Model Architecture Ablation Study

Total simulated candidates: $N = 4,800$ across 6 canonical engineering roles.

| Evaluation Model | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\\rho$ ↑ | Kendall's $\\tau$ ↑ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:---------:|:----------:|:-------------------:|:-----------------:|:------------------------:|
| **FULL_CCI** | 1.256 | 1.620 | 0.979 | 0.876 | Baseline |
| **NO_RECENCY_DECAY** | 1.260 | 1.615 | 0.976 | 0.869 | p=1.482e-03 |
| **NO_OWNERSHIP_DISCOUNT** | 2.313 | 2.954 | 0.940 | 0.791 | Yes (***) |
| **UNIFORM_WEIGHTS** | 1.958 | 2.513 | 0.963 | 0.836 | Yes (***) |
| **UNCALIBRATED_SOURCES** | 1.325 | 1.721 | 0.976 | 0.869 | Yes (***) |

*Note: Scoring config 4.0.0; candidate estimates require cluster-aware coverage >= 0.35, otherwise they are UNKNOWN. Within-cluster artifact decay is 0.50. Significance tests use candidate-paired Wilcoxon signed-rank tests; paired sample counts are archived with the JSON results.*
`;

    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'table_ablation_study.md');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
            <GraduationCap className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-white tracking-tight">
                Prototype Methodology &amp; Research Context
              </h1>
              <span className="px-2 py-0.5 bg-indigo-500/15 border border-indigo-500/30 text-indigo-300 rounded font-mono text-[10px] font-bold">
                10 THEOREMS
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Interactive method illustrations and the separate executable prototype experiment (4,800 simulated candidates per mode). This is not the manuscript Table 1 benchmark.
            </p>
          </div>
        </div>

        {/* Sub-Tab Selector */}
        <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-1 text-xs shrink-0">
          <button
            onClick={() => setSubTab('theorems')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
              subTab === 'theorems'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>Method Properties &amp; Math Sandbox</span>
          </button>
          <button
            onClick={() => setSubTab('ablation')}
            className={`px-3 py-1.5 rounded-md font-medium transition-colors flex items-center gap-1.5 ${
              subTab === 'ablation'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Table className="w-3.5 h-3.5" />
            <span>Prototype Ablation Study</span>
          </button>
        </div>
      </div>

      {/* Mode 1: 10 Theorems & Live Math Sandbox */}
      {subTab === 'theorems' && (
        <div className="space-y-6">
          {/* Category Filter Pills */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 font-medium mr-1">Filter Theorems:</span>
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 rounded-lg text-xs font-medium capitalize transition-colors ${
                  selectedCategory === cat
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200'
                }`}
              >
                {cat.replace(/_/g, ' ')}
              </button>
            ))}
          </div>

          {/* Interactive Live Simulators Card */}
          <div className="bg-slate-900 border border-indigo-500/30 rounded-xl p-6 shadow-xl space-y-5 ring-1 ring-indigo-500/20">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Calculator className="w-5 h-5 text-indigo-400" />
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  Interactive Mathematical Simulators
                </h2>
              </div>
              <span className="text-[11px] font-mono text-indigo-300 bg-indigo-950/60 border border-indigo-500/30 px-2 py-0.5 rounded">
                Real-Time Bound Verification
              </span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Simulator 1: Theorem 2 - Attribution-Gated Confidence */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-emerald-400" />
                    Theorem 2: Attribution-Gated Confidence
                  </span>
                  <span className="font-mono text-xs text-slate-400">
                    c_e,k = o·(a·t·v·x·r)^(1/5)
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span>Authority (a):</span>
                      <span className="text-indigo-300 font-bold">{t2Authority.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.01"
                      value={t2Authority}
                      onChange={(e) => setT2Authority(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span>Ownership (o):</span>
                      <span className="text-indigo-300 font-bold">{t2Ownership.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.01"
                      value={t2Ownership}
                      onChange={(e) => setT2Ownership(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span>Recency (t):</span>
                      <span className="text-indigo-300 font-bold">{t2Recency.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.01"
                      value={t2Recency}
                      onChange={(e) => setT2Recency(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span>Verifiability (v):</span>
                      <span className="text-indigo-300 font-bold">{t2Verifiability.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.01"
                      value={t2Verifiability}
                      onChange={(e) => setT2Verifiability(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span>Complexity (x):</span>
                      <span className="text-indigo-300 font-bold">{t2Complexity.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.01"
                      value={t2Complexity}
                      onChange={(e) => setT2Complexity(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px] text-slate-400">
                      <span>Reliability (r):</span>
                      <span className="text-indigo-300 font-bold">{t2Reliability.toFixed(2)}</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.01"
                      value={t2Reliability}
                      onChange={(e) => setT2Reliability(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
                    />
                  </div>
                </div>

                {/* Live Output Gauge */}
                <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-between">
                  <div>
                    <span className="text-[11px] text-slate-400 block">Composite Confidence c_e,k:</span>
                    <span
                      className={`text-xl font-bold font-mono ${
                        t2ZeroCollapsed ? 'text-rose-400' : 'text-emerald-400'
                      }`}
                    >
                      {t2Composite.toFixed(4)}
                    </span>
                  </div>

                  {t2ZeroCollapsed ? (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-rose-500/10 border border-rose-500/30 text-rose-300 rounded text-[11px] font-semibold">
                      <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
                      <span>Zero-Factor Collapse Triggered</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 rounded text-[11px] font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Bounded in [0, 1]</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Simulator 2: Theorem 1 - Recency Decay Curve */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                    <Scale className="w-4 h-4 text-amber-400" />
                    Theorem 1: Recency Decay Curve
                  </span>
                  <span className="font-mono text-xs text-slate-400">
                    t = exp(-lambda_k · Delta t)
                  </span>
                </div>

                <div className="space-y-3">
                  <div>
                    <span className="text-[11px] text-slate-400 block mb-1">Select Domain Velocity (lambda_k):</span>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        onClick={() => setT1Domain('fast')}
                        className={`px-2 py-1 rounded text-xs font-mono font-medium transition-colors ${
                          t1Domain === 'fast'
                            ? 'bg-amber-500/20 border border-amber-500 text-amber-300'
                            : 'bg-slate-900 border border-slate-800 text-slate-400'
                        }`}
                      >
                        Fast (Frontend/ML: 0.05)
                      </button>
                      <button
                        onClick={() => setT1Domain('mid')}
                        className={`px-2 py-1 rounded text-xs font-mono font-medium transition-colors ${
                          t1Domain === 'mid'
                            ? 'bg-indigo-500/20 border border-indigo-500 text-indigo-300'
                            : 'bg-slate-900 border border-slate-800 text-slate-400'
                        }`}
                      >
                        Mid (Backend/Cloud: 0.03)
                      </button>
                      <button
                        onClick={() => setT1Domain('foundational')}
                        className={`px-2 py-1 rounded text-xs font-mono font-medium transition-colors ${
                          t1Domain === 'foundational'
                            ? 'bg-emerald-500/20 border border-emerald-500 text-emerald-300'
                            : 'bg-slate-900 border border-slate-800 text-slate-400'
                        }`}
                      >
                        Stable (Algorithms: 0.01)
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-slate-400">Elapsed Time (Delta t):</span>
                      <span className="text-amber-300 font-bold">{t1DeltaT.toFixed(0)} months</span>
                    </div>
                    <input
                      type="range"
                      min="0"
                      max="60"
                      step="1"
                      value={t1DeltaT}
                      onChange={(e) => setT1DeltaT(parseFloat(e.target.value))}
                      className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
                    />
                  </div>

                  {/* Visual Decay Bar */}
                  <div className="space-y-1 pt-1">
                    <div className="flex justify-between text-[11px] font-mono text-slate-400">
                      <span>Evidence Weight Retention:</span>
                      <span className="text-slate-200 font-bold">{(t1DecayFactor * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-amber-500 transition-all duration-200"
                        style={{ width: `${t1DecayFactor * 100}%` }}
                      />
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 bg-slate-900/60 p-2.5 rounded border border-slate-800 font-mono">
                    exp(-{t1Lambda} * {t1DeltaT}) = <strong className="text-amber-300">{t1DecayFactor.toFixed(4)}</strong> discount factor.
                  </p>
                </div>
              </div>
            </div>

            {/* Simulator 3: Theorem 7 - Contradiction Diagnostic D_k */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                  <Split className="w-4 h-4 text-purple-400" />
                  Theorem 7: Contradiction Diagnostic D_k Simulator
                </span>
                <span className="font-mono text-xs text-slate-400">
                  D_k = (P_k - N_k) / (P_k + N_k + epsilon)
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-emerald-400">Positive Support Mass (P_k):</span>
                    <span className="font-bold text-emerald-300">{t7Positive.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="10.0"
                    step="0.1"
                    value={t7Positive}
                    onChange={(e) => setT7Positive(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                  />
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-rose-400">Negative / Deficiency Mass (N_k):</span>
                    <span className="font-bold text-rose-300">{t7Negative.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min="0.0"
                    max="10.0"
                    step="0.1"
                    value={t7Negative}
                    onChange={(e) => setT7Negative(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-rose-500"
                  />
                </div>
              </div>

              <div className="p-3 bg-slate-900 border border-slate-800 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400 font-mono">D_k Diagnostic Value:</span>
                  <span
                    className={`text-lg font-bold font-mono ${
                      t7Dk > 0.2 ? 'text-emerald-400' : t7Dk < -0.2 ? 'text-rose-400' : 'text-amber-400'
                    }`}
                  >
                    {t7Dk > 0 ? '+' : ''}
                    {t7Dk.toFixed(3)}
                  </span>
                </div>

                <div className="text-xs text-slate-300 font-sans">
                  {t7Positive > 1.0 && t7Negative > 1.0 ? (
                    <span className="inline-flex items-center gap-1 text-amber-400 font-semibold">
                      <Flame className="w-3.5 h-3.5" /> High Conflict: Triggers Prioritized Interview Probe
                    </span>
                  ) : t7Dk > 0.3 ? (
                    <span className="text-emerald-400 font-medium">Strong positive evidence dominance</span>
                  ) : t7Dk < -0.3 ? (
                    <span className="text-rose-400 font-medium">Critical negative / deficiency dominance</span>
                  ) : (
                    <span className="text-slate-400">Neutral directional balance</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Catalog of All 10 Theorems */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
              Prototype Mathematical Properties (not numbered paper theorems)
            </h3>

            {filteredTheorems.map((theorem) => {
              const isExpanded = expandedTheoremId === theorem.id;

              return (
                <div
                  key={theorem.id}
                  className="bg-slate-900 border border-slate-800 rounded-lg p-4 space-y-3 transition-colors hover:border-slate-700"
                >
                  <div
                    className="flex items-center justify-between cursor-pointer select-none"
                    onClick={() => setExpandedTheoremId(isExpanded ? null : theorem.id)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-bold font-mono text-xs">
                        {theorem.id}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-semibold text-white">{theorem.name}</h4>
                          <span className="px-2 py-0.5 bg-slate-950 border border-slate-800 text-slate-400 rounded text-[10px] font-mono">
                            {theorem.category}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 mt-0.5">{theorem.description}</p>
                      </div>
                    </div>

                    <button
                      type="button"
                      className="text-slate-400 hover:text-slate-200 p-1"
                    >
                      {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                    </button>
                  </div>

                  {isExpanded && (
                    <div className="pt-3 border-t border-slate-800 space-y-3 text-xs">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="bg-slate-950 p-3 rounded border border-slate-800 font-mono">
                          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">
                            Mathematical Formulation:
                          </span>
                          <span className="text-indigo-300 font-bold block">{theorem.latex_formula}</span>
                        </div>

                        <div className="bg-slate-950 p-3 rounded border border-slate-800 font-mono">
                          <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">
                            Formal Bound &amp; Limits:
                          </span>
                          <span className="text-emerald-300 font-semibold block">{theorem.bound_statement}</span>
                        </div>
                      </div>

                      <div className="bg-slate-950/60 p-3 rounded border border-slate-800">
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1 font-mono">
                          Physical &amp; Engineering Intuition:
                        </span>
                        <p className="text-slate-300 leading-relaxed">{theorem.physical_intuition}</p>
                      </div>

                      <div>
                        <span className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1 font-mono">
                          Key Theoretical Properties:
                        </span>
                        <ul className="list-disc list-inside space-y-1 text-slate-400 font-mono text-[11px]">
                          {theorem.key_properties.map((prop, idx) => (
                            <li key={idx}>{prop}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Mode 2: Prototype Ablation Study & Reproduction */}
      {subTab === 'ablation' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
              <div>
                <h2 className="text-base font-bold text-white">
                  Prototype Experiment: Model Architecture Ablation Study
                </h2>
                <p className="text-xs text-slate-400">
                  Empirical benchmarks across N = 4,800 simulated candidates and 6 canonical roles (16 seeds).
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleDownloadLatex}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Download prototype results (.tex)</span>
                </button>
                <button
                  type="button"
                  onClick={handleDownloadMarkdown}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  <Download className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Download prototype results (.md)</span>
                </button>
              </div>
            </div>

            {/* Publication Table 1 */}
            <div className="overflow-x-auto pt-1">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                    <th className="pb-3 pl-2">Evaluation Model</th>
                    <th className="pb-3 text-center">RCI MAE ↓</th>
                    <th className="pb-3 text-center">RCI RMSE ↓</th>
                    <th className="pb-3 text-center">Spearman ρ ↑</th>
                    <th className="pb-3 text-center">Kendall τ ↑</th>
                    <th className="pb-3 text-center">Stat. Sig. (p &lt; 0.001)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {(ablationData?.models || DEFAULT_ABLATION_MODELS).map((row) => (
                    <tr
                      key={row.model_name}
                      className={`transition-colors ${
                        row.is_baseline ? 'bg-indigo-950/20 font-bold' : 'hover:bg-slate-800/30'
                      }`}
                    >
                      <td className="py-3 pl-2 text-slate-100 flex items-center gap-2">
                        {row.is_baseline && (
                          <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded text-[10px] uppercase font-bold">
                            Proposed
                          </span>
                        )}
                        <span>{row.display_name}</span>
                      </td>
                      <td className="py-3 text-center text-slate-200">{row.mae.toFixed(3)}</td>
                      <td className="py-3 text-center text-slate-200">{row.rmse.toFixed(3)}</td>
                      <td className="py-3 text-center text-slate-200">{row.spearman_rho.toFixed(3)}</td>
                      <td className="py-3 text-center text-slate-200">{row.kendall_tau.toFixed(3)}</td>
                      <td className="py-3 text-center">
                        {row.is_baseline ? (
                          <span className="text-slate-400 font-medium">Baseline</span>
                        ) : row.statistical_significance.includes('***') ? (
                          <span className="px-2 py-0.5 bg-amber-500/10 text-amber-300 border border-amber-500/30 rounded text-[10px] font-bold">
                            Yes (p &lt; 0.001)***
                          </span>
                        ) : (
                          <span className="text-slate-500 text-[11px]">{row.statistical_significance}</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="pt-2 text-[11px] text-slate-500 flex items-center justify-between border-t border-slate-800/80">
              <span>* Candidate-paired Wilcoxon test against Full CCI. Only candidates with estimates in both modes are included; significant differences are marked ***.</span>
              <span>N = 4,800 candidates simulated across 16 deterministic seeds.</span>
            </div>
          </div>

          {/* Role Breakdown Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
            <div className="border-b border-slate-800 pb-3">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Role-by-Role Error Breakdown (RCI MAE)
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Comparison of capability estimation errors across canonical software engineering archetypes.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 text-[11px] uppercase tracking-wider">
                    <th className="pb-3 pl-2">Canonical Role</th>
                    <th className="pb-3 text-center">Full CCI (MAE)</th>
                    <th className="pb-3 text-center">w/o Recency</th>
                    <th className="pb-3 text-center">w/o Ownership</th>
                    <th className="pb-3 text-center">Uniform Weights</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {(ablationData?.role_breakdown || DEFAULT_ROLE_BREAKDOWN).map((row) => (
                    <tr key={row.role} className="hover:bg-slate-800/30">
                      <td className="py-2.5 pl-2 font-medium text-slate-100">{row.display_name}</td>
                      <td className="py-2.5 text-center text-emerald-400 font-bold">{row.full_cci_mae.toFixed(3)}</td>
                      <td className="py-2.5 text-center text-slate-300">{row.no_decay_mae?.toFixed(3) ?? 'Not archived'}</td>
                      <td className="py-2.5 text-center text-slate-300">{row.no_ownership_mae?.toFixed(3) ?? 'Not archived'}</td>
                      <td className="py-2.5 text-center text-rose-400">{row.uniform_weights_mae?.toFixed(3) ?? 'Not archived'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
