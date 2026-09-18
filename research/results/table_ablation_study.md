# Repository Supplementary Implementation Ablation Study

Candidate-role samples: $N = 4,800$ across the six canonical engineering roles.

> This artifact is a repository implementation diagnostic. It is **not** an exact regeneration of the submitted paper's headline benchmark, which reports 28,800 candidate-role evaluations under a broader controlled experimental design. See `research/paper_benchmark_manifest.json`.

| Evaluation Model | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\rho$ ↑ | Kendall's $\tau$ ↑ | Comparison vs Full CCI |
|:-----------------|:---------:|:----------:|:-------------------:|:-----------------:|:-----------------------:|
| **FULL_CCI** | 1.943 | 2.469 | 0.943 | 0.794 | Supplementary baseline |
| **NO_RECENCY_DECAY** | 1.975 | 2.505 | 0.943 | 0.794 | Paired Wilcoxon significant |
| **NO_OWNERSHIP_DISCOUNT** | 2.219 | 2.813 | 0.933 | 0.775 | Paired Wilcoxon significant |
| **UNIFORM_WEIGHTS** | 3.172 | 3.761 | 0.939 | 0.785 | Paired Wilcoxon significant |
| **UNCALIBRATED_SOURCES** | 1.922 | 2.446 | 0.942 | 0.792 | Supplementary diagnostic |

These values are synthetic implementation-ablation evidence, not real-world hiring accuracy or fairness validation.
