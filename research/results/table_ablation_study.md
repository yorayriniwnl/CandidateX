# Paper Reproducibility: Table 1 - Model Architecture Ablation Study

Total simulated candidates: $N = 4,800$ across 6 canonical engineering roles.

| Evaluation Model | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\rho$ ↑ | Kendall's $\tau$ ↑ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:---------:|:----------:|:-------------------:|:-----------------:|:------------------------:|
| **FULL_CCI** | 1.943 | 2.469 | 0.943 | 0.794 | Baseline |
| **NO_RECENCY_DECAY** | 1.975 | 2.505 | 0.943 | 0.794 | Yes (***) |
| **NO_OWNERSHIP_DISCOUNT** | 2.219 | 2.813 | 0.933 | 0.775 | Yes (***) |
| **UNIFORM_WEIGHTS** | 3.172 | 3.761 | 0.939 | 0.785 | Yes (***) |
| **UNCALIBRATED_SOURCES** | 1.922 | 2.446 | 0.942 | 0.792 | p=1.000e+00 |

*Note: Statistical significance tests ($p < 0.001$, marked ***) conducted via paired Wilcoxon signed-rank test against the Full CCI baseline.*
