const { test } = require('node:test');
const assert = require('node:assert/strict');
const { execFileSync } = require('node:child_process');
const { mkdtempSync, mkdirSync, readFileSync, writeFileSync, existsSync, rmSync } = require('node:fs');
const { tmpdir } = require('node:os');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const assets = [
  'plugins/multi-review/workflows/multi-review.js',
  'plugins/multi-review/scripts/preflight.sh',
];
const reviewAgents = [
  'review-architecture',
  'review-correctness',
  'review-intent',
  'review-judge',
  'review-preflight',
  'review-risk-router',
  'review-runtime',
  'review-security',
  'review-test-integrity',
  'review-verifier',
];

test('bundled workflow and preflight contain no hidden ASCII controls', () => {
  for (const asset of assets) {
    const content = readFileSync(path.join(root, asset), 'utf8');
    assert.equal(/[\x00-\x08\x0b-\x1f\x7f]/.test(content), false, `${asset}: hidden control character`);
  }
});

test('Windows-style Git checkout preserves LF for executable plugin assets', () => {
  const temp = mkdtempSync(path.join(tmpdir(), 'multi-review-eol-'));
  const git = (...args) => execFileSync('git', args, { cwd: temp, stdio: 'pipe' });
  try {
    git('init', '--quiet');
    git('config', 'core.autocrlf', 'true');
    git('config', 'core.safecrlf', 'false');
    if (existsSync(path.join(root, '.gitattributes'))) {
      writeFileSync(path.join(temp, '.gitattributes'), readFileSync(path.join(root, '.gitattributes')));
    }
    for (const asset of assets) {
      mkdirSync(path.dirname(path.join(temp, asset)), { recursive: true });
      // Seed LF, as in the published Git blobs; checkout must not introduce CR.
      writeFileSync(path.join(temp, asset), readFileSync(path.join(root, asset), 'utf8').replace(/\r\n/g, '\n'));
    }
    git('add', '.');
    for (const asset of assets) rmSync(path.join(temp, asset));
    git('checkout-index', '--all', '--force');
    for (const asset of assets) {
      assert.equal(readFileSync(path.join(temp, asset)).includes(13), false, `${asset}: checkout introduced CR`);
    }
  } finally {
    rmSync(temp, { recursive: true, force: true });
  }
});

test('review agents use supported tool denials instead of ignored plugin permission modes', () => {
  for (const agent of reviewAgents) {
    const asset = `plugins/multi-review/agents/${agent}.md`;
    const content = readFileSync(path.join(root, asset), 'utf8').replace(/\r\n/g, '\n');
    assert.doesNotMatch(content, /^permissionMode:/m, `${asset}: plugin permissionMode is ignored`);
    assert.match(content, /^disallowedTools:\n(?:\s+- (?:Edit|Write|NotebookEdit)\n){3}/m, `${asset}: must deny direct file-edit tools`);
  }
});

test('workflow runs preflight through the dedicated restricted agent', () => {
  const workflow = readFileSync(path.join(root, 'plugins/multi-review/workflows/multi-review.js'), 'utf8');
  assert.match(
    workflow,
    /\{ agentType: NS \+ 'review-preflight', label: 'preflight', phase: 'Preflight', schema: PREFLIGHT_SCHEMA \}/,
  );
});
