import fs from 'node:fs';

function fail(message) {
  console.error(`deployment contract: ${message}`);
  process.exitCode = 1;
}

if (fs.existsSync('index.html')) {
  fail('root index.html must not exist; it can shadow the real apps/web Next.js product');
}

if (!fs.existsSync('vercel.json')) {
  fail('vercel.json is required to pin deployment to apps/web');
} else {
  const config = JSON.parse(fs.readFileSync('vercel.json', 'utf8'));
  if (config.framework !== 'nextjs') {
    fail('vercel.json must declare the nextjs framework');
  }
  if (!String(config.installCommand || '').includes('apps/web')) {
    fail('installCommand must install the apps/web lockfile');
  }
  if (!String(config.buildCommand || '').includes('apps/web')) {
    fail('buildCommand must build apps/web');
  }
  if (config.outputDirectory !== 'apps/web/.next') {
    fail('outputDirectory must point at apps/web/.next');
  }
}

const webPackage = JSON.parse(fs.readFileSync('apps/web/package.json', 'utf8'));
if (!webPackage.dependencies?.['framer-motion']) {
  fail('apps/web must declare framer-motion because the production UI imports it');
}

const webLock = fs.readFileSync('apps/web/package-lock.json', 'utf8');
if (!webLock.includes('framer-motion')) {
  fail('apps/web package-lock.json must lock framer-motion for reproducible Vercel installs');
}

if (!process.exitCode) {
  console.log('deployment contract: passed');
}
