"""Research and methodology API for Candidate Capability Intelligence (CCI).

This router deliberately separates two evidence layers:
1. the headline controlled benchmark reported in the submitted conference paper; and
2. the repository's supplementary implementation ablation harness.

The two must never be presented as the same experiment. All results are synthetic
research evidence and are not claims of real-world hiring validity.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/research", tags=["Research & Methodology"])

REPO_ROOT = Path(__file__).resolve().parents[6]
RESULTS_PATH = REPO_ROOT / "research" / "results" / "ablation_results.json"

CANONICAL_ROLES = [
    "backend",
    "frontend",
    "fullstack",
    "ml_engineer",
    "devops_cloud",
    "data_engineer",
]


class TheoremMetadata(BaseModel):
    id: int
    name: str
    category: str
    latex_formula: str
    description: str
    bound_statement: str
    physical_intuition: str
    key_properties: List[str]


class PaperMetric(BaseModel):
    name: str
    mean: float
    std: float


class PaperBenchmarkResponse(BaseModel):
    evidence_layer: str
    deterministic_seeds: int
    candidate_profiles_per_seed: int
    canonical_roles: List[str]
    candidate_role_evaluations: int
    metrics: List[PaperMetric]
    validation_boundary: str


class AblationRow(BaseModel):
    model_name: str
    display_name: str
    mae: float
    rmse: float
    spearman_rho: float
    kendall_tau: float
    statistical_significance: str
    is_baseline: bool = False


class RoleBreakdownRow(BaseModel):
    role: str
    display_name: str
    full_cci_mae: float
    no_decay_mae: float
    no_ownership_mae: float
    uniform_weights_mae: float


class AblationStudyResponse(BaseModel):
    total_candidates: int
    total_seeds: int
    roles_count: int
    models: List[AblationRow]
    role_breakdown: List[RoleBreakdownRow]
    latex_table: str
    markdown_table: str
    notes: str


class CalculationRequest(BaseModel):
    theorem_id: int = Field(..., ge=1, le=10)
    parameters: Dict[str, Any]


class CalculationResponse(BaseModel):
    theorem_id: int
    theorem_name: str
    formula: str
    result: float
    intermediate_steps: Dict[str, Any]
    bounds_satisfied: bool
    explanation: str


THEOREMS_CATALOG: List[TheoremMetadata] = [
    TheoremMetadata(
        id=1,
        name="Recency Decay Monotonicity & Asymptotics",
        category="Calibration & Recency",
        latex_formula=r"t_{e,k}=\exp(-\lambda_k\Delta t_e)",
        description="Capability-specific temporal discount applied to evidence recency.",
        bound_statement=r"t_{e,k}\in(0,1],\ t(0)=1,\ \lim_{\Delta t\to\infty}t=0",
        physical_intuition="Recent evidence receives more weight, with faster-moving domains allowed to decay more quickly.",
        key_properties=["monotone decay", "identity at zero age", "capability-specific rate"],
    ),
    TheoremMetadata(
        id=2,
        name="Six-Factor Evidence Confidence",
        category="Scoring & Calibration",
        latex_formula=r"c_{e,k}=(a_eo_et_{e,k}v_ex_er_{s(e)})^{1/6}",
        description="Geometric-mean confidence over integrity, ownership, recency, verification, depth and source reliability.",
        bound_statement=r"c_{e,k}\in[0,1]",
        physical_intuition="No single strong signal can fully compensate for a critically weak evidence factor.",
        key_properties=["bounded", "monotone in each factor", "zero-factor collapse"],
    ),
    TheoremMetadata(
        id=3,
        name="Capability Estimate Range Preservation",
        category="Scoring & Calibration",
        latex_formula=r"q_k=\frac{\sum_e c_{e,k}z_{e,k}}{\sum_e c_{e,k}}",
        description="Observed capability is a confidence-weighted estimate over supporting evidence.",
        bound_statement=r"q_k\in[\min z_e,\max z_e]\subseteq[0,100]",
        physical_intuition="The estimate stays inside the range of actual observed support values.",
        key_properties=["convex combination", "range preserving", "missing evidence remains UNKNOWN"],
    ),
    TheoremMetadata(
        id=4,
        name="Kish Effective Evidence Count",
        category="Uncertainty",
        latex_formula=r"n_{eff,k}=\frac{(\sum_e c_{e,k})^2}{\sum_e c_{e,k}^2}",
        description="Effective sample size discounts collections dominated by uneven evidence weights.",
        bound_statement=r"1\le n_{eff,k}\le N_k",
        physical_intuition="Many weak observations should not create false precision.",
        key_properties=["bounded by raw count", "equality for equal weights", "uncertainty-aware"],
    ),
    TheoremMetadata(
        id=5,
        name="Softmax Role Weights",
        category="Role Calibration",
        latex_formula=r"w_k=\frac{\exp(u_k/T)}{\sum_j\exp(u_j/T)}",
        description="Job requirements are normalized into a positive role-weight distribution.",
        bound_statement=r"w_k>0,\ \sum_k w_k=1",
        physical_intuition="Role emphasis changes smoothly while preserving a normalized capability budget.",
        key_properties=["positive", "normalized", "shift invariant"],
    ),
    TheoremMetadata(
        id=6,
        name="Role Capability Index",
        category="Scoring & Aggregation",
        latex_formula=r"RCI=\frac{\sum_{k\in\mathcal O}w_kq_k}{\sum_{k\in\mathcal O}w_k}",
        description="RCI summarizes capability only over observed dimensions; coverage is reported separately.",
        bound_statement=r"RCI\in[0,100]",
        physical_intuition="Unobserved dimensions reduce coverage rather than being converted into artificial zero scores.",
        key_properties=["observed-only aggregation", "bounded", "coverage separated"],
    ),
    TheoremMetadata(
        id=7,
        name="Contradiction Diagnostic",
        category="Uncertainty & Contradiction",
        latex_formula=r"D_k=\frac{P_k-N_k}{P_k+N_k+\epsilon}",
        description="Directional balance between positive and contradictory evidence.",
        bound_statement=r"D_k\in[-1,1]",
        physical_intuition="Conflicting evidence is surfaced for interview review instead of silently averaged away.",
        key_properties=["bounded", "neutral at balanced support", "conflict visible"],
    ),
    TheoremMetadata(
        id=8,
        name="Interview Probe Priority",
        category="Interview Probes",
        latex_formula=r"I_k=w_k[\alpha(1-Cov_k)+\beta\,CIwidth_k+\gamma\,Conf_k]",
        description="Paper-aligned information-gain heuristic for prioritizing technical interview probes.",
        bound_statement=r"I_k\ge0",
        physical_intuition="High-role-weight gaps with uncertainty or contradiction are probed first.",
        key_properties=["role-weighted", "coverage-gap sensitive", "uncertainty and conflict sensitive"],
    ),
    TheoremMetadata(
        id=9,
        name="Beta-Binomial Source Reliability",
        category="Calibration & Bayesian Updates",
        latex_formula=r"E[r_s|\alpha_s,\beta_s,k,n]=\frac{\alpha_s+k}{\alpha_s+\beta_s+n}",
        description="Source-family reliability is updated with a conjugate Bayesian posterior.",
        bound_statement=r"E[r_s]\in[0,1]",
        physical_intuition="Source trust can adapt from verification outcomes without discarding prior information.",
        key_properties=["closed form", "bounded", "converges toward empirical rate"],
    ),
    TheoremMetadata(
        id=10,
        name="Security & Governance Invariants",
        category="Security & Governance",
        latex_formula=r"Exec(C_{untrusted})=\emptyset\ \land\ Decision(CCI)=SupportOnly",
        description="Candidate code is not executed and the platform does not autonomously decide employment outcomes.",
        bound_statement=r"Status(e_{missing})=UNKNOWN\ne0",
        physical_intuition="Security, provenance and human review are system invariants rather than UI disclaimers.",
        key_properties=["no untrusted code execution", "missing != zero", "human decision support only"],
    ),
]


@router.get("/theorems", response_model=List[TheoremMetadata])
def get_all_theorems() -> List[TheoremMetadata]:
    return THEOREMS_CATALOG


@router.get("/paper-benchmark", response_model=PaperBenchmarkResponse)
def get_paper_benchmark() -> PaperBenchmarkResponse:
    return PaperBenchmarkResponse(
        evidence_layer="paper_reported_controlled_benchmark",
        deterministic_seeds=16,
        candidate_profiles_per_seed=300,
        canonical_roles=CANONICAL_ROLES,
        candidate_role_evaluations=28_800,
        metrics=[
            PaperMetric(name="spearman_rho", mean=0.928, std=0.013),
            PaperMetric(name="kendall_tau", mean=0.774, std=0.019),
            PaperMetric(name="ndcg_at_20", mean=0.970, std=0.011),
        ],
        validation_boundary=(
            "Synthetic controlled-experiment evidence only; these values do not establish "
            "real-world hiring accuracy, fairness, or candidate performance."
        ),
    )


def _load_supplementary_results() -> Dict[str, Any]:
    if not RESULTS_PATH.exists():
        raise HTTPException(status_code=503, detail="Supplementary ablation artifact is unavailable")
    with RESULTS_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _significance_for(model_name: str, payload: Dict[str, Any]) -> str:
    if model_name == "FULL_CCI":
        return "Supplementary baseline"
    stats_payload = payload.get("statistical_tests", {}).get(model_name, {})
    p_value = stats_payload.get("two_sided_p_value", stats_payload.get("p_value"))
    is_significant = bool(stats_payload.get("is_significant", False))
    if p_value is None:
        return "supplementary diagnostic"
    return f"two-sided p={p_value:.3g}" + (" (significant)" if is_significant else " (not significant)")


@router.get("/ablation-study", response_model=AblationStudyResponse)
def get_ablation_study() -> AblationStudyResponse:
    payload = _load_supplementary_results()
    summary = payload.get("ablation_summary", {})
    display_names = {
        "FULL_CCI": "Full CCI",
        "NO_RECENCY_DECAY": "Without recency decay",
        "NO_OWNERSHIP_DISCOUNT": "Without ownership discount",
        "UNIFORM_WEIGHTS": "Uniform role weights",
        "UNCALIBRATED_SOURCES": "Uncalibrated sources",
    }

    models: List[AblationRow] = []
    for model_name in [
        "FULL_CCI",
        "NO_RECENCY_DECAY",
        "NO_OWNERSHIP_DISCOUNT",
        "UNIFORM_WEIGHTS",
        "UNCALIBRATED_SOURCES",
    ]:
        row = summary.get(model_name)
        if not row:
            continue
        models.append(
            AblationRow(
                model_name=model_name,
                display_name=display_names[model_name],
                mae=float(row["rci_mae"]),
                rmse=float(row["rci_rmse"]),
                spearman_rho=float(row["spearman_rho"]),
                kendall_tau=float(row["kendall_tau"]),
                statistical_significance=_significance_for(model_name, payload),
                is_baseline=model_name == "FULL_CCI",
            )
        )

    markdown_lines = [
        "| Model | MAE | RMSE | Spearman rho | Kendall tau |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in models:
        markdown_lines.append(
            f"| {row.display_name} | {row.mae:.3f} | {row.rmse:.3f} | {row.spearman_rho:.3f} | {row.kendall_tau:.3f} |"
        )

    metadata = payload.get("metadata", {})
    return AblationStudyResponse(
        total_candidates=int(metadata.get("total_candidates", 0)),
        total_seeds=len(metadata.get("seeds", [])),
        roles_count=len(metadata.get("roles", [])),
        models=models,
        role_breakdown=[],
        latex_table="",
        markdown_table="\n".join(markdown_lines),
        notes=(
            "Supplementary implementation ablation harness generated by the repository. "
            "It is distinct from the conference paper's 28,800 candidate-role controlled benchmark "
            "and must not be presented as real-world hiring validation."
        ),
    )


@router.post("/calculate", response_model=CalculationResponse)
def calculate_theorem_math(request: CalculationRequest) -> CalculationResponse:
    p = request.parameters

    if request.theorem_id == 1:
        delta_t = float(p.get("delta_t_months", 0.0))
        lambda_rate = float(p.get("lambda_rate", 0.03))
        if delta_t < 0 or lambda_rate < 0:
            raise HTTPException(status_code=400, detail="delta_t_months and lambda_rate must be non-negative")
        value = math.exp(-lambda_rate * delta_t)
        return CalculationResponse(
            theorem_id=1,
            theorem_name=THEOREMS_CATALOG[0].name,
            formula="exp(-lambda * delta_t)",
            result=round(value, 4),
            intermediate_steps={"exponent": -lambda_rate * delta_t},
            bounds_satisfied=0.0 < value <= 1.0,
            explanation="Recency discount calculated from the paper-aligned exponential decay function.",
        )

    if request.theorem_id == 2:
        keys = ["authority", "ownership", "recency", "verifiability", "complexity", "reliability"]
        factors = [float(p.get(key, 1.0)) for key in keys]
        if any(value < 0.0 or value > 1.0 for value in factors):
            raise HTTPException(status_code=400, detail="All six confidence factors must be in [0,1]")
        product = math.prod(factors)
        value = product ** (1.0 / 6.0) if product > 0 else 0.0
        return CalculationResponse(
            theorem_id=2,
            theorem_name=THEOREMS_CATALOG[1].name,
            formula="(a*o*t*v*x*r)^(1/6)",
            result=round(value, 4),
            intermediate_steps={"factors": dict(zip(keys, factors)), "product": product, "zero_collapsed": 0.0 in factors},
            bounds_satisfied=0.0 <= value <= 1.0,
            explanation="Six-factor geometric-mean confidence.",
        )

    if request.theorem_id == 4:
        confidences = p.get("confidences")
        if not isinstance(confidences, list) or not confidences:
            raise HTTPException(status_code=400, detail="confidences must be a non-empty list")
        values = [float(value) for value in confidences]
        if any(value < 0 for value in values):
            raise HTTPException(status_code=400, detail="confidence weights must be non-negative")
        sum_c = sum(values)
        sum_sq = sum(value * value for value in values)
        n_eff = (sum_c * sum_c) / sum_sq if sum_sq else 0.0
        return CalculationResponse(
            theorem_id=4,
            theorem_name=THEOREMS_CATALOG[3].name,
            formula="(sum c)^2/sum(c^2)",
            result=round(n_eff, 4),
            intermediate_steps={"raw_count": len(values), "sum_c": sum_c, "sum_sq": sum_sq},
            bounds_satisfied=(n_eff == 0.0 and sum_c == 0.0) or (1.0 <= n_eff <= len(values) + 1e-9),
            explanation="Kish effective evidence count.",
        )

    if request.theorem_id == 6:
        weights = [float(v) for v in p.get("weights", [])]
        estimates = [float(v) for v in p.get("estimates", [])]
        if not weights or len(weights) != len(estimates):
            raise HTTPException(status_code=400, detail="weights and estimates must be non-empty equal-length lists")
        if any(q < 0 or q > 100 for q in estimates) or any(w < 0 for w in weights):
            raise HTTPException(status_code=400, detail="invalid score or weight range")
        weight_sum = sum(weights)
        if weight_sum <= 0:
            raise HTTPException(status_code=400, detail="sum of weights must be positive")
        rci = sum(w * q for w, q in zip(weights, estimates)) / weight_sum
        return CalculationResponse(
            theorem_id=6,
            theorem_name=THEOREMS_CATALOG[5].name,
            formula="sum(w*q)/sum(w)",
            result=round(rci, 4),
            intermediate_steps={"observed_weight_mass": weight_sum},
            bounds_satisfied=0.0 <= rci <= 100.0,
            explanation="RCI normalized over observed capability weight mass.",
        )

    if request.theorem_id == 7:
        positive = float(p.get("positive_support", 0.0))
        negative = float(p.get("negative_support", 0.0))
        epsilon = float(p.get("epsilon", 1e-5))
        if positive < 0 or negative < 0 or epsilon <= 0:
            raise HTTPException(status_code=400, detail="support values must be non-negative and epsilon positive")
        value = (positive - negative) / (positive + negative + epsilon)
        return CalculationResponse(
            theorem_id=7,
            theorem_name=THEOREMS_CATALOG[6].name,
            formula="(P-N)/(P+N+epsilon)",
            result=round(value, 4),
            intermediate_steps={"P": positive, "N": negative, "epsilon": epsilon},
            bounds_satisfied=-1.0 <= value <= 1.0,
            explanation="Directional contradiction diagnostic.",
        )

    if request.theorem_id == 8:
        role_weight = float(p.get("role_weight", 0.2))
        coverage = float(p.get("coverage", 0.5))
        ci_width = float(p.get("ci_width", 0.1))
        conflict = float(p.get("conflict", 0.0))
        alpha = float(p.get("alpha", 0.40))
        beta = float(p.get("beta", 0.35))
        gamma = float(p.get("gamma", 0.25))
        if not all(0.0 <= v <= 1.0 for v in [role_weight, coverage, ci_width, conflict, alpha, beta, gamma]):
            raise HTTPException(status_code=400, detail="Theorem 8 normalized parameters must be in [0,1]")
        gap = 1.0 - coverage
        inner = alpha * gap + beta * ci_width + gamma * conflict
        value = role_weight * inner
        return CalculationResponse(
            theorem_id=8,
            theorem_name=THEOREMS_CATALOG[7].name,
            formula="w_k[alpha(1-Cov_k)+beta*CIwidth_k+gamma*Conf_k]",
            result=round(value, 4),
            intermediate_steps={
                "coverage_gap": gap,
                "weighted_gap_term": alpha * gap,
                "uncertainty_term": beta * ci_width,
                "conflict_term": gamma * conflict,
                "inner_bracket": inner,
            },
            bounds_satisfied=value >= 0.0,
            explanation="Paper-aligned interview probe priority calculation.",
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Theorem {request.theorem_id} has no interactive calculator in this prototype.",
    )
