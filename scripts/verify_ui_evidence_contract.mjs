import fs from 'node:fs';

const read = (path) => fs.readFileSync(path, 'utf8');
const failures = [];
const assert = (condition, message) => {
  if (!condition) failures.push(message);
};

const page = read('apps/web/app/page.tsx');
const directory = read('apps/web/components/CandidateDirectory.tsx');
const comparison = read('apps/web/components/CandidateComparison.tsx');
const wizard = read('apps/web/components/EvaluationWizard.tsx');

assert(!page.includes('MOCK_DOSSIER'), 'app/page.tsx must not preload or silently substitute MOCK_DOSSIER');
assert(!page.includes('MOCK_GRAPH'), 'app/page.tsx must not preload or silently substitute MOCK_GRAPH');
assert(!page.includes('fallback to mock'), 'app/page.tsx must not hide backend failures behind mock results');
assert(!page.includes('setInterval('), 'pipeline completion must be driven by backend state, not a cosmetic timer');
assert(page.includes('useState<Dossier | null>(null)'), 'dossier state must start empty');
assert(page.includes('useState<CEGGraph | null>(null)'), 'graph state must start empty');

assert(!directory.includes('FALLBACK_CANDIDATES'), 'candidate directory must not fabricate live-looking fallback candidates');
assert(!directory.includes('verified dossiers, RCI ratings'), 'directory copy must not claim verification when the backend is unavailable');

assert(!comparison.includes('MOCK_DOSSIER'), 'comparison must not synthesize candidate scores from a mock dossier');
assert(!comparison.includes('Mock fallback simulation'), 'comparison must not silently generate comparison results');

assert(!wizard.includes('RCI 90.0'), 'quick-demo controls must not advertise preset RCI outcomes');
assert(!wizard.includes('RCI 86.0'), 'quick-demo controls must not advertise preset RCI outcomes');
assert(wizard.includes('isBackendOnline'), 'evaluation presets must know whether a real backend is available');

if (failures.length) {
  for (const failure of failures) console.error(`ui evidence contract: ${failure}`);
  process.exit(1);
}

console.log('ui evidence contract: passed');
