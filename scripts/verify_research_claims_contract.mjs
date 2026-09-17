import fs from 'node:fs';

const router = fs.readFileSync('services/backend/src/cci/api/routers/research.py', 'utf8');
const audit = fs.readFileSync('scripts/run_system_audit.py', 'utf8');
const table = fs.readFileSync('research/results/table_ablation_study.md', 'utf8');

const failures = [];
const assert = (condition, message) => {
  if (!condition) failures.push(message);
};

assert(/synthetic/i.test(router) && /Monte Carlo/i.test(router), 'research API must explicitly label the N=4,800 study as synthetic Monte Carlo simulation');
assert(!/empirical ablation study reproduction/i.test(router), 'research API must not call the synthetic ablation study empirical');
assert(!/empirical benchmark results across N=4,800 candidates/i.test(router), 'ablation endpoint description must not imply real-candidate empirical validation');
assert(/simulated candidates/i.test(table), 'paper table must keep the simulated-candidate boundary visible');
assert(!audit.includes('Statistical significance p < 0.001 (***) confirmed across 4,800 Monte Carlo candidates'), 'system audit must not claim p < 0.001 for every ablation');
assert(/UNCALIBRATED_SOURCES/i.test(audit) || /uncalibrated/i.test(audit), 'system audit must acknowledge the uncalibrated-source ablation exception');

if (failures.length) {
  for (const failure of failures) console.error(`research claims contract: ${failure}`);
  process.exit(1);
}

console.log('research claims contract: passed');
