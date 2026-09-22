# Candidate Capability Intelligence (CCI) Backend

FastAPI & SQLAlchemy 2.0 implementation of the paper-aligned CCI decision support system.

## GitHub attribution boundaries

A supplied GitHub URL records a repository association. Account matches in the recent repository commit sample are recorded separately as repository contribution and do not establish authorship of every inspected file.

Live evidence receives an artifact attribution only from commit history for that exact path at the pinned repository revision. The scan requests path history for at most 24 high-signal evidence paths per analysis and reads at most the latest 30 path commits. Paths outside that budget, unavailable history, and ambiguous author metadata remain `UNKNOWN` with zero candidate attribution; repository contribution is never used as a fallback. When available, path commit ratios describe contributions linked to the declared GitHub account, not verified human identity or line-level authorship.

The evidence graph represents repository association and repository contribution separately. It emits candidate-to-artifact contribution edges only when path-specific commit history supports them. Aggregate repository activity does not create an artifact `AUTHORED_BY` edge.

Evidence confidence uses a direct attribution gate: `confidence = path_attribution × geometric_mean(integrity, recency, verification, depth, reliability)`. This choice keeps the five evidence-quality factors on their existing [0, 1] scale while ensuring the result cannot exceed the path contribution ratio. There is no per-artifact ownership cutoff; the output is a relative evidence weight, not a calibrated probability.

Candidate capability estimates and RCI use a separate sufficiency gate. An estimate is emitted only when attribution-gated capability coverage meets `ScoringConfig.low_coverage_threshold` (0.35 by default). Below it, the candidate estimate is `UNKNOWN`, not zero; evidence counts and nonzero coverage remain available. The research ablation runner uses the same gate.
