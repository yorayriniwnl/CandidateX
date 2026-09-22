# Paper Reproducibility: Table 1 - Model Architecture Ablation Study

Total simulated candidates: $N = 4,800$ across 6 canonical engineering roles.

| Evaluation Model | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\rho$ ↑ | Kendall's $\tau$ ↑ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:---------:|:----------:|:-------------------:|:-----------------:|:------------------------:|
| **FULL_CCI** | 1.435 | 1.873 | 0.961 | 0.832 | Baseline |
| **NO_RECENCY_DECAY** | 1.442 | 1.881 | 0.961 | 0.831 | Yes (***) |
| **NO_OWNERSHIP_DISCOUNT** | 2.227 | 2.822 | 0.933 | 0.776 | Yes (***) |
| **UNIFORM_WEIGHTS** | 2.346 | 2.872 | 0.953 | 0.815 | Yes (***) |
| **UNCALIBRATED_SOURCES** | 1.466 | 1.907 | 0.960 | 0.830 | Yes (***) |

*Note: Statistical significance tests ($p < 0.001$, marked ***) conducted via paired Wilcoxon signed-rank test against the Full CCI baseline.*
