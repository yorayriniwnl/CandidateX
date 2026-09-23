# Paper Reproducibility: Table 1 - Model Architecture Ablation Study

Total simulated candidates: $N = 4,800$ across 6 canonical engineering roles.

| Evaluation Model | RCI MAE ↓ | RCI RMSE ↓ | Spearman's $\rho$ ↑ | Kendall's $\tau$ ↑ | Stat. Sig. ($p < 0.001$) |
|:-----------------|:---------:|:----------:|:-------------------:|:-----------------:|:------------------------:|
| **FULL_CCI** | 1.256 | 1.620 | 0.979 | 0.876 | Baseline |
| **NO_RECENCY_DECAY** | 1.260 | 1.615 | 0.976 | 0.869 | p=1.482e-03 |
| **NO_OWNERSHIP_DISCOUNT** | 2.313 | 2.954 | 0.940 | 0.791 | Yes (***) |
| **UNIFORM_WEIGHTS** | 1.958 | 2.513 | 0.963 | 0.836 | Yes (***) |
| **UNCALIBRATED_SOURCES** | 1.325 | 1.721 | 0.976 | 0.869 | Yes (***) |

*Scoring config 4.0.0; candidate estimates require coverage >= 0.35; within-cluster artifact decay is 0.50; lower coverage is UNKNOWN.*
*Paired significance tests use candidates with estimates in both modes; paired sample counts are in the JSON artifact.*

*Note: Statistical significance tests ($p < 0.001$, marked ***) conducted via paired Wilcoxon signed-rank test against the Full CCI baseline.*
