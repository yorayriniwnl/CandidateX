# Paper Reproducibility: Table 1 - Model Architecture Ablation Study

Total simulated candidates: $N = 4,800$ across 6 canonical engineering roles.

| Evaluation Model | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\rho$ ↑ | Kendall's $\tau$ ↑ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:---------:|:----------:|:-------------------:|:-----------------:|:------------------------:|
| **FULL_CCI** | 1.210 | 1.543 | 0.978 | 0.875 | Baseline |
| **NO_RECENCY_DECAY** | 1.219 | 1.550 | 0.978 | 0.872 | Yes (***) |
| **NO_OWNERSHIP_DISCOUNT** | 2.319 | 2.949 | 0.940 | 0.790 | Yes (***) |
| **UNIFORM_WEIGHTS** | 1.967 | 2.491 | 0.963 | 0.837 | Yes (***) |
| **UNCALIBRATED_SOURCES** | 1.282 | 1.635 | 0.977 | 0.870 | Yes (***) |

*Scoring config 3.0.0; candidate estimates require coverage >= 0.35; lower coverage is UNKNOWN.*

*Note: Statistical significance tests ($p < 0.001$, marked ***) conducted via paired Wilcoxon signed-rank test against the Full CCI baseline.*
