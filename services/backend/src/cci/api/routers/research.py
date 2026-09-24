"""Research, Theorems, and Formal Math Router for Candidate Capability Intelligence (CCI).

Provides endpoints to inspect prototype mathematical properties and access
archived executable prototype experiment results, and execute live
pure-functional mathematical calculations.
"""

from __future__ import annotations

import math
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from cci.scoring.confidence import compute_evidence_confidence

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
    paired_sample_count: int
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
    experiment_scope: str
    headline_reproduced: bool
    scoring_config_version: str
    evidence_family_decay: float
    cluster_artifact_decay: float
    minimum_capability_coverage: float
    total_candidates: int
    total_seeds: int
    roles_count: int
    models: list[AblationRow]
    role_breakdown: list[RoleBreakdownRow]
    latex_table: str
    markdown_table: str
    notes: str


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
        name="Attribution-Gated Evidence Weight Boundedness",
        category="Scoring & Calibration",
        latex_formula=r"c_{e,k} = o_e \cdot (a_e \cdot t_{e,k} \cdot v_e \cdot x_e \cdot r_s(e))^{1/5}",
        description="A direct candidate-attribution gate multiplied by the geometric mean of five evidence-quality factors.",
        bound_statement=r"c_{e,k} \in [0, 1], \quad c_{e,k} \le o_e, \quad o_e=0 \implies c_{e,k}=0",
        physical_intuition="Weak attribution cannot be softened by taking a root: confidence weight is capped at the share of path commits linked to the declared account.",
        key_properties=[
            "Direct gate: zero attribution forces zero confidence weight",
            "The confidence weight never exceeds the attribution factor",
            "Monotonically increasing in attribution and every evidence-quality factor",
            "Only the five evidence-quality factors are symmetric under permutation",
        ],
    ),
    TheoremMetadata(
        id=3,
        name="Point Estimate Convexity & Range Preservation",
        category="Scoring & Calibration",
        latex_formula=r"q_k = \frac{\sum_{e} c_{e,k} z_{e,k}}{\sum_{e} c_{e,k}}",
        description="Candidate point estimation is a normalized confidence-weighted convex combination gated by cluster-aware attributed coverage.",
        bound_statement=r"q_k \in [\min z_e, \max z_e] \subseteq [0, 100]",
        physical_intuition="Point estimate is strictly bounded within the support of concrete empirical evidence scores.",
        key_properties=[
            "Convex combination ensures stability against extreme outlier amplification",
            "Constant inputs z_e = z_0 produce q_k = z_0",
            "Unique artifacts count once per source-family cluster, with geometric diminishing returns",
            "Missing or undercovered evidence produces UNKNOWN, never 0.0",
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
        description="The pure softmax transform normalizes any finite importance vector; automatic production role profiles first add bounded JD adjustments and then enforce configured probability bounds.",
        bound_statement=r"\sum_{k=1}^{12} w_k = 1.0, \quad w_k > 0, \quad w_k(u + C) = w_k(u)",
        physical_intuition="Translates hiring committee priorities smoothly without numerical instability or arbitrary scaling bias.",
        key_properties=[
            "Shift-invariance under uniform utility shifts (u_k + C)",
            "Temperature parameter T controls peakiness vs uniformity",
            "The pure transform gives positive weight to all 12 capabilities; production profiles apply explicit minimum and maximum bounds after softmax",
        ],
    ),
    TheoremMetadata(
        id=6,
        name="Role Capability Index (RCI) Boundedness",
        category="Scoring & Aggregation",
        latex_formula=r"\text{RCI} = 100 \cdot \frac{\sum_{k \in \mathcal{O}} w_k q_k}{\sum_{k \in \mathcal{O}} w_k}",
        description="Composite score aggregating capabilities whose attribution-gated coverage meets the configured minimum.",
        bound_statement=r"\text{RCI} \in [0, 100], \quad \forall k \in \mathcal{O}: q_k = q_0 \implies \text{RCI} = q_0",
        physical_intuition="Provides a comparable scalar indicator while explicitly separating capability depth from evidence coverage.",
        key_properties=[
            "Only sufficiently supported candidate estimates enter the observed role weight mass",
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
        description="Bayesian update model tracking repository and platform source reliability over time.",
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


@router.get(
    "/ablation-study",
    response_model=AblationStudyResponse,
    summary="Get archived executable prototype experiment results",
    description="Returns the archived synthetic prototype results across N=4,800 candidates for Full CCI vs 4 ablated architectures.",
)
def get_ablation_study() -> AblationStudyResponse:
    artifact_dir = Path(__file__).resolve().parents[6] / "research" / "results"
    try:
        artifact = json.loads((artifact_dir / "ablation_results.json").read_text(encoding="utf-8"))
        markdown = (artifact_dir / "table_ablation_study.md").read_text(encoding="utf-8")
        latex = (artifact_dir / "table_ablation_study.tex").read_text(encoding="utf-8")
    except (OSError, ValueError) as error:
        raise HTTPException(503, "Archived prototype experiment artifacts unavailable") from error
    models = []
    for mode, values in artifact["ablation_summary"].items():
        comparison = artifact["statistical_tests"].get(mode)
        significance = "Baseline" if comparison is None else f"One-sided p={comparison['p_value']:.3g}; two-sided p={comparison['two_sided_p_value']:.3g}"
        models.append(AblationRow(model_name=mode, display_name=mode.replace("_", " ").title(),
            paired_sample_count=(comparison.get("paired_sample_count", 0) if comparison else values.get("sample_count", 0)),
            mae=round(values["rci_mae"], 3), rmse=round(values["rci_rmse"], 3),
            spearman_rho=round(values["spearman_rho"], 3), kendall_tau=round(values["kendall_tau"], 3),
            statistical_significance=significance, is_baseline=mode == "FULL_CCI"))
    role_breakdown = [RoleBreakdownRow(role=role, display_name=role.replace("_", " ").title(),
                      full_cci_mae=values["rci_mae"])
                      for role, values in artifact["per_role_summary"].items()]
    method_version = artifact["metadata"].get("scoring_config_version", "unknown")
    confidence_formula = artifact["metadata"].get("confidence_formula", "not recorded")
    minimum_coverage = artifact["metadata"].get("minimum_capability_coverage", "not recorded")
    cluster_decay = artifact["metadata"].get("cluster_artifact_decay", "not recorded")
    family_decay = artifact["metadata"].get("evidence_family_decay", "not recorded")
    return AblationStudyResponse(
        experiment_scope=artifact["metadata"]["experiment_scope"],
        headline_reproduced=artifact["metadata"]["headline_reproduced"],
        scoring_config_version=method_version,
        evidence_family_decay=family_decay,
        cluster_artifact_decay=cluster_decay,
        minimum_capability_coverage=minimum_coverage,
        total_candidates=artifact["metadata"]["total_candidates"],
        total_seeds=len(artifact["metadata"]["seeds"]), roles_count=len(artifact["metadata"]["roles"]),
        models=models, role_breakdown=role_breakdown, latex_table=latex, markdown_table=markdown,
        notes=(f"Scoring config {method_version}; confidence formula {confidence_formula}; "
               f"Minimum capability coverage {minimum_coverage}; within-cluster artifact decay {cluster_decay}; "
               f"evidence family decay {family_decay}. "
               "Paired significance tests use candidates with estimates in both modes; paired counts are archived. "
               "Separate executable prototype experiment: 16 seeds, six roles, 50 distinct candidates per role per seed. "
               "Not a reproduction of the manuscript's 28,800-pair headline benchmark. Per-role ablation metrics were not archived and are unavailable. "
               "Source reliability uses configured priors. These synthetic results do not establish real-world hiring accuracy."))


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
        # Theorem 2: Direct attribution gate over five-factor evidence quality.
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

        quality_product = a * t * v * x * r
        evidence_quality = math.pow(quality_product, 1.0 / 5.0) if quality_product > 0 else 0.0
        composite = compute_evidence_confidence(a, o, t, v, x, r)

        return CalculationResponse(
            theorem_id=2,
            theorem_name="Attribution-Gated Evidence Weight",
            formula="o * (a * t * v * x * r)^(1/5)",
            result=round(composite, 4),
            intermediate_steps={
                "factors": {"a": a, "o": o, "t": t, "v": v, "x": x, "r": r},
                "attribution_gate": o,
                "quality_product": quality_product,
                "evidence_quality": evidence_quality,
                "zero_collapsed": any(f == 0.0 for f in factors),
            },
            bounds_satisfied=0.0 <= composite <= 1.0,
            explanation=(f"Confidence weight is {composite:.4f} from attribution gate {o:.4f} and evidence quality {evidence_quality:.4f}. "
                         f"The weight cannot exceed attribution. {'Zero-factor collapse triggered.' if any(f == 0.0 for f in factors) else 'No zero factor was present.'}"),
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
        c_k = float(p.get("contradiction", 0.0))
        if not all(math.isfinite(v) and 0 <= v <= 1 for v in (w_k, cov_k, width, c_k)):
            raise HTTPException(400, "Weight, coverage, normalized CI width and conflict must be in [0, 1]")
        cfg = ScoringConfig()
        gap_term = w_k * cfg.probe_alpha * (1 - cov_k)
        uncert_term = w_k * cfg.probe_beta * width
        contra_term = w_k * cfg.probe_gamma * c_k
        i_k = probe_priority_score(w_k, 1 - cov_k, width, c_k, cfg)

        return CalculationResponse(
            theorem_id=8,
            theorem_name="Information-Theoretic Probe Priority",
            formula="w_k * [0.40 * (1 - Cov_k) + 0.35 * normalized_CI_width + 0.25 * conflict]",
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
