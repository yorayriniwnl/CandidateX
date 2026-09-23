# JD Weighting Adversarial Matrix

This matrix records automatic role-profile output from scoring config `5.1.0` and the current controlled synonym parser. It is a deterministic policy check, not empirical calibration or evidence about hiring outcomes. Full weights for all 12 capabilities are in [the JSON matrix](jd-weighting-adversarial-matrix.json).

| JD scenario | Role | Parsed / mapped requirements | Highest weights | Lowest weight |
| --- | --- | ---: | --- | ---: |
| One mandatory Python requirement | Backend | 1 / 1 | Backend 36.35%, Database 14.16%, Algorithms 8.59%, Architecture 8.59% | 1.92% |
| Same Python requirement repeated 20 times | Backend | 20 / 20 | Backend 36.35%, Database 14.16%, Algorithms 8.59%, Architecture 8.59% | 1.92% |
| Balanced backend role | Backend | 9 / 9 | Backend 33.03%, Database 16.77%, Architecture 10.17%, Testing 9.92% | 1.35% |
| Security-heavy backend role | Backend | 6 / 6 | Database 22.96%, Backend 22.52%, Security 11.79%, Algorithms 8.29% | 1.85% |
| Full-stack role | Fullstack | 8 / 8 | Frontend 23.00%, Backend 17.40%, Database 11.39%, Architecture 11.39% | 1.51% |
| Generic engineering JD | Backend | 1 / 0 | Backend 26.83%, Database 16.28%, Algorithms 9.87%, Architecture 9.87% | 2.20% |
| Empty JD | Backend | 0 / 0 | Backend 26.83%, Database 16.28%, Algorithms 9.87%, Architecture 9.87% | 2.20% |
| Unmapped marketing-heavy JD | Backend | 4 / 0 | Backend 26.83%, Database 16.28%, Algorithms 9.87%, Architecture 9.87% | 2.20% |

The 20 repeated Python lines produce the same role weights as one Python requirement because they form one normalized group. Generic, empty, and unmapped marketing JDs preserve the backend role prior. The full-stack and security-heavy examples increase their corresponding dimensions while retaining all 12 capabilities above the configured floor.

The 40% maximum and 1% minimum apply to automatically generated profiles. A separately audited expert override remains an explicit manual exception.
