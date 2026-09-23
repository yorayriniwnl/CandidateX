# Synthetic Prototype Ablation Study (Table 1-Style Comparison)

Total simulated candidates: $N = 4,800$ across 6 canonical engineering roles.

| Evaluation Model | Paired N | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\rho$ ↑ | Kendall's $\tau$ ↑ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:--------:|:---------:|:----------:|:-------------------:|:-----------------:|:------------------------:|
| **FULL_CCI** | 4,796 | 1.267 | 1.643 | 0.977 | 0.872 | Baseline |
| **NO_RECENCY_DECAY** | 4,796 | 1.255 | 1.626 | 0.976 | 0.868 | p=4.733e-01 |
| **NO_OWNERSHIP_DISCOUNT** | 4,796 | 2.332 | 2.996 | 0.934 | 0.780 | Yes (***) |
| **UNIFORM_WEIGHTS** | 4,796 | 1.921 | 2.455 | 0.960 | 0.831 | Yes (***) |
| **UNCALIBRATED_SOURCES** | 4,796 | 1.335 | 1.734 | 0.975 | 0.867 | Yes (***) |

*Scoring config 5.1.0; candidate estimates require coverage >= 0.35; within-cluster artifact decay is 0.50; evidence family decay is 0.50; lower coverage is UNKNOWN.*
*Paired significance tests use candidates with estimates in both modes; paired sample counts are in the JSON artifact.*

*Note: Statistical significance tests ($p < 0.001$, marked ***) conducted via paired Wilcoxon signed-rank test against the Full CCI baseline.*
