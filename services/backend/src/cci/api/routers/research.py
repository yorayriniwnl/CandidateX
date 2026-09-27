"""Research, Theorems, and Formal Math Router for Candidate Capability Intelligence (CCI).

Provides endpoints to inspect prototype mathematical properties and access
archived executable prototype experiment results, and execute live
pure-functional mathematical calculations.
"""

from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/research", tags=["Research & Formal Theorems"])

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class TheoremMetadata(BaseModel):
    id: int
    name: str
    category: str
    latex_formula: str
    description: str
    bound_statement: str
    physical_intuition: str
    key_properties: list[str]


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
    no_decay_mae: float | None = None
    no_ownership_mae: float | None = None
    uniform_weights_mae: float | None = None


class AblationStudyResponse(BaseModel):
    total_candidates: int
    total_seeds: int
    roles_count: int
    models: list[AblationRow]
    role_breakdown: list[RoleBreakdownRow]
    latex_table: str
    markdown_table: str
    notes: str


class PaperMetric(BaseModel):
    name: str
    mean: float
    std: float


class PaperBenchmarkResponse(BaseModel):
    evidence_layer: str
    provenance: str
    deterministic_seeds: int
    candidate_profiles_per_seed: int
    canonical_roles: list[str]
    candidate_role_evaluations: int
    metrics: list[PaperMetric]
    validation_boundary: str


class CalculationRequest(BaseModel):
    theorem_id: int = Field(
        ..., ge=1, le=10, description="Theorem ID to evaluate (1..10)"
    )
    parameters: dict[str, Any] = Field(
        ..., description="Parameter map for the theorem formula"
    )


class CalculationResponse(BaseModel):
    theorem_id: int
    theorem_name: str
    formula: str
    result: float
    intermediate_steps: dict[str, Any]
    bounds_satisfied: bool
    explanation: str


CANONICAL_ROLES = [
    "backend",
    "frontend",
    "fullstack",
    "ml_engineer",
    "devops_cloud",
    "data_engineer",
]

SUPPLEMENTARY_ABLATION_ROWS = [
    {"model_name": "FULL_CCI", "display_name": "Full CCI", "mae": 1.9426, "rmse": 2.4686, "rho": 0.9434, "tau": 0.7945, "p_one_sided": None, "p_two_sided": None},
    {"model_name": "NO_RECENCY_DECAY", "display_name": "Without recency decay", "mae": 1.9753, "rmse": 2.5045, "rho": 0.9432, "tau": 0.7940, "p_one_sided": 2.0364078412682406e-72, "p_two_sided": 4.072815682536481e-72},
    {"model_name": "NO_OWNERSHIP_DISCOUNT", "display_name": "Without ownership discount", "mae": 2.2192, "rmse": 2.8126, "rho": 0.9327, "tau": 0.7753, "p_one_sided": 0.0, "p_two_sided": 0.0},
    {"model_name": "UNIFORM_WEIGHTS", "display_name": "Uniform role weights", "mae": 3.1716, "rmse": 3.7610, "rho": 0.9386, "tau": 0.7854, "p_one_sided": 0.0, "p_two_sided": 0.0},
    {"model_name": "UNCALIBRATED_SOURCES", "display_name": "Uncalibrated sources", "mae": 1.9224, "rmse": 2.4455, "rho": 0.9424, "tau": 0.7925, "p_one_sided": 1.0, "p_two_sided": 4.104265665660845e-29},
]

RECORDED_ROLE_BREAKDOWN = [
    {"role": "backend", "display_name": "Backend", "full_cci_mae": 1.935},
    {"role": "frontend", "display_name": "Frontend", "full_cci_mae": 1.900},
    {"role": "fullstack", "display_name": "Full-stack", "full_cci_mae": 1.894},
    {"role": "ml_engineer", "display_name": "ML Engineer", "full_cci_mae": 1.986},
    {"role": "devops_cloud", "display_name": "DevOps / Cloud", "full_cci_mae": 1.957},
    {"role": "data_engineer", "display_name": "Data Engineer", "full_cci_mae": 1.982},
]


# ---------------------------------------------------------------------------
# Static Theorem Catalog (Theorems 1 through 10)
# ---------------------------------------------------------------------------

THEOREMS_CATALOG: list[TheoremMetadata] = [
    TheoremMetadata(
        id=1,
        name="Recency Decay Monotonicity & Asymptotics",
        category="Calibration & Recency",
        latex_formula=r"t(\Delta t, k) = \exp(-\lambda_k \cdot \Delta t)",
        description="Exponential decay factor discount based on elapsed elapsed months since artifact observation.",
        bound_statement=r"t \in (0, 1], \quad t(0) = 1.0, \quad \lim_{\Delta t \to \infty} t = 0.0",
        physical_intuition="Fast-evolving technology domains (Frontend, ML) decay strictly faster than foundational algorithms and data structures.",
        key_properties=[
            "Strict monotonicity: d/dt < 0 for all Delta t > 0",
            "Zero elapsed time yields identity factor 1.0",
            "Domain-specific decay rate lambda_k strictly positive",
        ],
    ),
    TheoremMetadata(
        id=2,
        name="6-Factor Confidence Decomposition Boundedness",
        category="Scoring & Calibration",
        latex_formula=r"c_{e,k} = (a \cdot o \cdot t \cdot v \cdot x \cdot r)^{1/6}",
        description="Geometric mean composition across Authority, Ownership, Recency, Verifiability, Complexity, and Bayesian Source Reliability.",
        bound_statement=r"c_{e,k} \in [0, 1], \quad \exists f_i = 0 \implies c_{e,k} = 0",
        physical_intuition="A single compromised or absent factor (e.g. 0% ownership on a forked repository) zeroes out composite confidence.",
        key_properties=[
            "Multiplicative coupling prevents compensating zero ownership with high stars",
            "Monotonically increasing in every individual factor",
            "Equal factor weighting guarantees symmetry under factor permutation",
        ],
    ),
    TheoremMetadata(
        id=3,
        name="Point Estimate Convexity & Range Preservation",
        category="Scoring & Calibration",
        latex_formula=r"q_k = \frac{\sum_{e} c_{e,k} z_{e,k}}{\sum_{e} c_{e,k}}",
        description="Capability point estimation formulated as a normalized confidence-weighted convex combination.",
        bound_statement=r"q_k \in [\min z_e, \max z_e] \subseteq [0, 100]",
        physical_intuition="Point estimate is strictly bounded within the support of concrete empirical evidence scores.",
        key_properties=[
            "Convex combination ensures stability against extreme outlier amplification",
            "Constant inputs z_e = z_0 produce q_k = z_0",
            "Missing evidence produces UNKNOWN / unobserved, never 0.0",
        ],
    ),
    TheoremMetadata(
        id=4,
        name="Kish Effective Sample Size",
        category="Uncertainty & Sample Size",
        latex_formula=r"n_{\text{eff},k} = \frac{(\sum c_{e,k})^2}{\sum c_{e,k}^2}",
        description="Measures statistical information content accounting for non-uniform confidence dispersion.",
        bound_statement=r"1.0 \le n_{\text{eff},k} \le N, \quad n_{\text{eff},k} = N \iff c_1 = \dots = c_N",
        physical_intuition="Kish effective count measures relative weight inequality, not absolute confidence. Equal positive weights give n_eff = N.",
        key_properties=[
            "Reported separately from project-cluster bootstrap intervals",
            "Strictly penalized by high confidence inequality across evidence items",
            "Upper-bounded by raw observation count N",
        ],
    ),
    TheoremMetadata(
        id=5,
        name="Softmax Role Weights Invariance & Normalization",
        category="Role Calibration",
        latex_formula=r"w_k = \frac{\exp(u_k / T)}{\sum_{j=1}^{12} \exp(u_j / T)}",
        description="Normalizes raw requirement importance vectors into a convex role weight distribution.",
        bound_statement=r"\sum_{k=1}^{12} w_k = 1.0, \quad w_k > 0, \quad w_k(u + C) = w_k(u)",
        physical_intuition="Translates hiring committee priorities smoothly without numerical instability or arbitrary scaling bias.",
        key_properties=[
            "Shift-invariance under uniform utility shifts (u_k + C)",
            "Temperature parameter T controls peakiness vs uniformity",
            "Guarantees positive weight for all 12 canonical capabilities",
        ],
    ),
    TheoremMetadata(
        id=6,
        name="Role Capability Index (RCI) Boundedness",
        category="Scoring & Aggregation",
        latex_formula=r"\text{RCI} = 100 \cdot \frac{\sum_{k \in \mathcal{O}} w_k q_k}{\sum_{k \in \mathcal{O}} w_k}",
        description="Composite score aggregating observed capabilities renormalized over the observed role weight mass.",
        bound_statement=r"\text{RCI} \in [0, 100], \quad \forall k \in \mathcal{O}: q_k = q_0 \implies \text{RCI} = q_0",
        physical_intuition="Provides a comparable scalar indicator while explicitly separating capability depth from evidence coverage.",
        key_properties=[
            "Coverage-normalized: unobserved capabilities never penalize observed score",
            "Preserves convex bounds of underlying point estimates",
            "Pure functional rescoring operates without re-crawling repositories",
        ],
    ),
    TheoremMetadata(
        id=7,
        name="Contradiction Diagnostic Boundedness & Neutrality",
        category="Uncertainty & Contradiction",
        latex_formula=r"D_k = \frac{P_k - N_k}{P_k + N_k + \epsilon}",
        description="Measures directional support balance between positive evidence (P_k) and negative/deficiency evidence (N_k).",
        bound_statement=r"D_k \in [-1.0, +1.0], \quad P_k = N_k \implies D_k = 0.0",
        physical_intuition="Identifies conflicting technical evidence (e.g. claiming expert Go on CV vs 0 Go repositories or failed AST tests).",
        key_properties=[
            "Symmetric zero point: balanced positive and negative evidence yields D_k = 0",
            "Never silently averages away conflicting signals",
            "Simultaneous high positive and high negative support flags critical interview probe",
        ],
    ),
    TheoremMetadata(
        id=8,
        name="Information-Theoretic Probe Priority Monotonicity",
        category="Interview Probes",
        latex_formula=r"I_k = w_k [\alpha (1 - \text{Cov}_k) + \beta\,\text{CIwidth}_k + \gamma\,\text{Conf}_k]",
        description="Ranks technical interview inquiries by potential information gain to maximize interview ROI.",
        bound_statement=r"\frac{\partial I_k}{\partial (1 - \text{Cov}_k)} > 0, \quad I_k \ge 0",
        physical_intuition="Directs interviewers to probe high-weight unverified requirements and active contradictions first.",
        key_properties=[
            "Strictly increases with coverage gap (1 - Cov_k)",
            "Scales with candidate dispersion and contradiction severity",
            "Grounds auto-generated inquiry questions directly in concrete evidence IDs",
        ],
    ),
    TheoremMetadata(
        id=9,
        name="Beta-Binomial Source Reliability Consistency",
        category="Calibration & Bayesian Updates",
        latex_formula=r"\mathbb{E}[r_s | \alpha_s, \beta_s, k, n] = \frac{\alpha_s + k}{\alpha_s + \beta_s + n}",
        description="Empirical Bayesian update calibrating repository and platform source reliability over time.",
        bound_statement=r"\lim_{n \to \infty} \mathbb{E}[r_s] = \frac{k}{n} \in [0, 1]",
        physical_intuition="Maintains prior stability while converging to empirical verification success rates.",
        key_properties=[
            "Conjugate Beta prior provides closed-form deterministic updates",
            "Immutable audit trail logs every posterior parameter change",
            "Prevents single malicious/spam repositories from poisoning global prior",
        ],
    ),
    TheoremMetadata(
        id=10,
        name="Platform Security & Governance Invariants",
        category="Security & Invariants",
        latex_formula=r"\text{Exec}(C_{\text{untrusted}}) = \emptyset \quad \land \quad \text{Decision}(CCI) = \text{SupportOnly}",
        description="Formal commitments ensuring safe execution, candidate privacy, and decision support ethics.",
        bound_statement=r"\text{Status}(e_{\text{missing}}) = \text{UNKNOWN} \ne 0.0",
        physical_intuition="The platform strictly parses static ASTs without code execution, never auto-rejects candidates, and treats missing evidence as unknown.",
        key_properties=[
            "Zero dynamic code execution: static deterministic AST parsers only",
            "Missing evidence produces UNKNOWN / lower coverage, never 0.0 score",
            "Employer decision support only: autonomous hire/reject is prohibited",
            "SSRF defense with DNS pinning and cloud metadata (169.254.169.254) isolation",
        ],
    ),
]


# ---------------------------------------------------------------------------
# Router Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/theorems",
    response_model=list[TheoremMetadata],
    summary="Get All 10 Conference Paper Theorems",
    description="Returns the formal mathematical formulations, bound proofs, and physical intuitions for Theorems 1 through 10.",
)
def get_all_theorems() -> list[TheoremMetadata]:
    return THEOREMS_CATALOG


@router.get("/paper-benchmark", response_model=PaperBenchmarkResponse)
def get_paper_benchmark() -> PaperBenchmarkResponse:
    return PaperBenchmarkResponse(
        evidence_layer="paper_reported_controlled_benchmark",
        provenance="Reported in the submitted manuscript; not regenerated by the repository ablation harness.",
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


def _ablation_comparison_label(row: dict[str, Any]) -> str:
    if row["p_one_sided"] is None:
        return "Supplementary baseline"
    if row["p_one_sided"] < 0.001:
        return f"One-sided paired Wilcoxon p={row['p_one_sided']:.3g}; ablation error higher"
    if row["p_two_sided"] < 0.05:
        return (
            f"One-sided p={row['p_one_sided']:.3g}; no evidence of higher ablation error. "
            f"Two-sided p={row['p_two_sided']:.3g}; uncalibrated variant had lower error."
        )
    return f"No directional difference detected (one-sided p={row['p_one_sided']:.3g})"


@router.get(
    "/ablation-study",
    response_model=AblationStudyResponse,
    summary="Get supplementary implementation ablation results",
    description=(
        "Returns the separate 4,800-sample synthetic implementation ablation; "
        "it is not the manuscript's 28,800 candidate-role benchmark."
    ),
)
def get_ablation_study() -> AblationStudyResponse:
    models = [
        AblationRow(
            model_name=row["model_name"],
            display_name=row["display_name"],
            mae=row["mae"],
            rmse=row["rmse"],
            spearman_rho=row["rho"],
            kendall_tau=row["tau"],
            statistical_significance=_ablation_comparison_label(row),
            is_baseline=row["model_name"] == "FULL_CCI",
        )
        for row in SUPPLEMENTARY_ABLATION_ROWS
    ]
    markdown_lines = [
        "| Model | MAE | RMSE | Spearman rho | Kendall tau | Comparison |",
        "|---|---:|---:|---:|---:|---|",
    ]
    markdown_lines.extend(
        f"| {row.display_name} | {row.mae:.3f} | {row.rmse:.3f} | "
        f"{row.spearman_rho:.3f} | {row.kendall_tau:.3f} | {row.statistical_significance} |"
        for row in models
    )
    return AblationStudyResponse(
        total_candidates=4800,
        total_seeds=16,
        roles_count=len(CANONICAL_ROLES),
        models=models,
        role_breakdown=[RoleBreakdownRow(**row) for row in RECORDED_ROLE_BREAKDOWN],
        latex_table="",
        markdown_table="\n".join(markdown_lines),
        notes=(
            "Supplementary implementation ablation: 16 seeds, six role-specific cohorts, "
            "and 50 samples per role per seed. It is separate from the manuscript's "
            "28,800 candidate-role benchmark. Recorded per-role Full CCI MAE values are "
            "included; per-role ablation comparison metrics were not archived. "
            "Source reliability uses configured priors. These synthetic results do not "
            "establish real-world hiring accuracy."
        ),
    )


@router.post(
    "/calculate",
    response_model=CalculationResponse,
    summary="Execute Live Mathematical Calculation for Paper Theorem",
    description="Pure functional evaluation verifying bounds, limits, and behavior for Theorems 1, 2, 4, 6, 7, and 8.",
)
def calculate_theorem_math(request: CalculationRequest) -> CalculationResponse:
    p = request.parameters

    if request.theorem_id == 1:
        # Theorem 1: Recency Decay: exp(-lambda * delta_t)
        delta_t = float(p.get("delta_t_months", 0.0))
        lambda_val = float(p.get("lambda_rate", 0.03))
        if delta_t < 0 or lambda_val < 0:
            raise HTTPException(
                status_code=400,
                detail="delta_t_months and lambda_rate must be non-negative",
            )
        decay = math.exp(-lambda_val * delta_t)
        return CalculationResponse(
            theorem_id=1,
            theorem_name="Recency Decay Monotonicity",
            formula=f"exp(-{lambda_val:.4f} * {delta_t:.1f})",
            result=round(decay, 4),
            intermediate_steps={"exponent": -lambda_val * delta_t, "raw_exp": decay},
            bounds_satisfied=(0.0 < decay <= 1.0) if delta_t > 0 else (decay == 1.0),
            explanation=f"At {delta_t:.1f} months elapsed with decay rate {lambda_val}, evidence weight is discounted to {decay * 100:.1f}%.",
        )

    elif request.theorem_id == 2:
        # Theorem 2: Multiplicative 6-Factor Confidence
        a = float(p.get("authority", 1.0))
        o = float(p.get("ownership", 1.0))
        t = float(p.get("recency", 1.0))
        v = float(p.get("verifiability", 1.0))
        x = float(p.get("complexity", 1.0))
        r = float(p.get("reliability", 1.0))

        factors = [a, o, t, v, x, r]
        for f in factors:
            if not (0.0 <= f <= 1.0):
                raise HTTPException(
                    status_code=400,
                    detail=f"All factors must be in [0.0, 1.0], got {f}",
                )

        product = a * o * t * v * x * r
        composite = math.pow(product, 1.0 / 6.0) if product > 0 else 0.0

        return CalculationResponse(
            theorem_id=2,
            theorem_name="6-Factor Confidence Decomposition",
            formula="(a * o * t * v * x * r)^(1/6)",
            result=round(composite, 4),
            intermediate_steps={
                "factors": {"a": a, "o": o, "t": t, "v": v, "x": x, "r": r},
                "product": product,
                "zero_collapsed": any(f == 0.0 for f in factors),
            },
            bounds_satisfied=0.0 <= composite <= 1.0,
            explanation=f"Composite confidence is {composite:.4f}. {'Zero-factor collapse triggered: composite confidence is strictly zero.' if any(f == 0.0 for f in factors) else 'All factors positive, geometric mean preserved.'}",
        )

    elif request.theorem_id == 4:
        # Theorem 4: Kish Effective Sample Size: (sum c)^2 / sum(c^2)
        confidences = p.get("confidences", [0.8, 0.8, 0.8])
        if not isinstance(confidences, list) or len(confidences) == 0:
            raise HTTPException(
                status_code=400, detail="confidences must be a non-empty list of floats"
            )
        c_vals = [float(c) for c in confidences]
        sum_c = sum(c_vals)
        sum_sq = sum(c * c for c in c_vals)
        n_eff = (sum_c * sum_c) / sum_sq if sum_sq > 0 else 0.0
        n_raw = len(c_vals)

        return CalculationResponse(
            theorem_id=4,
            theorem_name="Kish Effective Sample Size",
            formula="(sum c)^2 / sum(c^2)",
            result=round(n_eff, 3),
            intermediate_steps={"raw_count_N": n_raw, "sum_c": sum_c, "sum_sq": sum_sq},
            bounds_satisfied=1.0 <= n_eff <= n_raw + 1e-6,
            explanation=f"Raw observations: N = {n_raw}. Kish effective sample size: n_eff = {n_eff:.2f} (Efficiency: {(n_eff / n_raw) * 100:.1f}%).",
        )

    elif request.theorem_id == 6:
        # Theorem 6: Role Capability Index (RCI)
        weights = p.get("weights", [0.25, 0.25, 0.25, 0.25])
        estimates = p.get("estimates", [85.0, 90.0, 75.0, 80.0])
        if len(weights) != len(estimates):
            raise HTTPException(
                status_code=400,
                detail="weights and estimates lists must have equal length",
            )

        w_sum = sum(weights)
        if w_sum <= 0:
            raise HTTPException(
                status_code=400, detail="Sum of weights must be positive"
            )
        weighted_score = sum(w * e for w, e in zip(weights, estimates))
        rci = weighted_score / w_sum

        return CalculationResponse(
            theorem_id=6,
            theorem_name="Role Capability Index (RCI)",
            formula="100 * sum(w_k * q_k) / sum(w_k)",
            result=round(rci, 2),
            intermediate_steps={
                "observed_weight_mass": w_sum,
                "weighted_sum": weighted_score,
            },
            bounds_satisfied=0.0 <= rci <= 100.0,
            explanation=f"Computed RCI = {rci:.2f}/100 normalized over observed weight mass {w_sum:.2f}.",
        )

    elif request.theorem_id == 7:
        # Theorem 7: Contradiction Diagnostic D_k
        p_k = float(p.get("positive_support", 0.0))
        n_k = float(p.get("negative_support", 0.0))
        epsilon = 0.0001
        if p_k < 0 or n_k < 0:
            raise HTTPException(
                status_code=400,
                detail="positive_support and negative_support must be non-negative",
            )

        denom = p_k + n_k + epsilon
        d_k = (p_k - n_k) / denom

        return CalculationResponse(
            theorem_id=7,
            theorem_name="Contradiction Diagnostic (D_k)",
            formula="(P_k - N_k) / (P_k + N_k + epsilon)",
            result=round(d_k, 3),
            intermediate_steps={"P_k": p_k, "N_k": n_k, "denominator": denom},
            bounds_satisfied=-1.0 <= d_k <= 1.0,
            explanation=f"D_k diagnostic: {d_k:+.3f}. {'Balanced neutral support.' if abs(d_k) < 0.1 else 'Strong positive support dominance.' if d_k > 0.3 else 'Critical negative/deficiency dominance.' if d_k < -0.3 else 'Moderate directional lean.'}",
        )

    elif request.theorem_id == 8:
        # Theorem 8: Probe Priority I_k
        w_k = float(p.get("role_weight", 0.20))
        cov_k = float(p.get("coverage", 0.50))
        from cci.domain.contracts import ScoringConfig
        from cci.probes.priority import probe_priority_score
        width = float(p.get("ci_width", p.get("dispersion", 0.10)))
        c_k = float(p.get("conflict", p.get("contradiction", 0.0)))
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (w_k, cov_k, width, c_k)):
            raise HTTPException(400, "Weight, coverage, normalized CI width and conflict must be in [0, 1]")
        cfg = ScoringConfig(
            probe_alpha=float(p.get("alpha", 0.40)),
            probe_beta=float(p.get("beta", 0.35)),
            probe_gamma=float(p.get("gamma", 0.25)),
        )
        gap_term = w_k * cfg.probe_alpha * (1 - cov_k)
        uncert_term = w_k * cfg.probe_beta * width
        contra_term = w_k * cfg.probe_gamma * c_k
        i_k = probe_priority_score(w_k, 1 - cov_k, width, c_k, cfg)

        return CalculationResponse(
            theorem_id=8,
            theorem_name="Information-Theoretic Probe Priority",
            formula="I_k = w_k * [alpha * (1 - Cov_k) + beta * CIwidth_k + gamma*Conf_k]",
            result=round(i_k, 4),
            intermediate_steps={
                "coverage_gap_term": gap_term,
                "uncertainty_term": uncert_term,
                "contradiction_term": contra_term,
            },
            bounds_satisfied=i_k >= 0.0,
            explanation=f"Probe Priority I_k = {i_k:.4f} (Gap: {gap_term:.3f}, Uncertainty: {uncert_term:.3f}, Contradiction: {contra_term:.3f}).",
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Theorem ID {request.theorem_id} calculation is either conceptual/security-only or unsupported for live calculation.",
        )
