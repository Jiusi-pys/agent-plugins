export const meta = {
  name: 'multi-review',
  description:
    'Heterogeneous multi-sensor code review: deterministic preflight → risk routing → parallel read-only sensors → independent falsification → unified gate. No majority vote; only verified findings block; never auto-edits or auto-merges.',
  whenToUse:
    'Review a PR, ref range, or working diff before merge. args: { target, intent_file, mode: auto|normal|deep }.',
  phases: [
    { title: 'Preflight', detail: 'deterministic gates + intake thresholds (scripts/review/preflight.sh)' },
    { title: 'Risk Routing', detail: 'review-risk-router → R0–R3 + sensor set' },
    { title: 'Sensors', detail: 'parallel read-only reviewers emit candidate findings' },
    { title: 'Verification', detail: 'one fresh review-verifier per candidate tries to falsify' },
    { title: 'Judgment', detail: 'review-judge dedups, applies gate logic, emits report' },
  ],
}

// ───────────────────────── inputs ─────────────────────────
// Selection precedence: commit > staged > target > working tree.
//   { commit: "abc123" }       → exactly that one commit (its diff vs its parent)
//   { staged: true }           → staged changes only (git diff --staged)
//   { target: "origin/main" }  → this branch vs that ref (ref...HEAD)
//   { target: "a..b" }         → explicit range (also "a...b" or "abc123^!" pass through)
//   (omit)                     → working tree (uncommitted changes + untracked)
let targetArg = '' // exact $1 handed to preflight.sh; '' means working tree
if (args && args.commit != null && String(args.commit).trim() !== '') {
  targetArg = `${String(args.commit).trim()}^!`
} else if (args && (args.staged === true || args.target === 'staged' || args.target === 'cached')) {
  targetArg = 'staged'
} else if (args && args.target) {
  targetArg = String(args.target).trim()
}

const intentFile = (args && args.intent_file) || null
const mode = (args && args.mode) || 'auto' // auto | normal | deep
const preflightPath = (args && args.preflight) || null // absolute path to this plugin's scripts/preflight.sh (the command passes ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.sh)
const NS = 'multi-review:' // plugin components are namespaced <plugin>:<name>; agents resolve as multi-review:review-*

function describeTarget(t) {
  if (t === '') return 'the working tree (uncommitted changes vs HEAD, including untracked files)'
  if (t === 'staged') return 'the staged changes (git diff --staged)'
  if (/\^!$/.test(t)) return `the single commit ${t.replace(/\^!$/, '')} (its diff against its parent)`
  if (/\.\./.test(t)) return `the commit range ${t}`
  return `this branch compared to ${t} (${t}...HEAD)`
}
function diffCommand(t) {
  if (t === '') return 'git diff HEAD  (plus untracked: git ls-files --others --exclude-standard)'
  if (t === 'staged') return 'git diff --staged'
  if (/\^!$/.test(t)) { const c = t.replace(/\^!$/, ''); return `git show ${c}  (or: git diff ${c}^..${c})` }
  if (/\.\./.test(t)) return `git diff ${t}  (commit list: git log --oneline ${t})`
  return `git diff ${t}...HEAD  (commit list: git log --oneline ${t}...HEAD)`
}
const target = describeTarget(targetArg) // human-facing label reused across prompts
const diffCmd = diffCommand(targetArg)

const KNOWN_SENSORS = [
  'review-correctness',
  'review-test-integrity',
  'review-security',
  'review-architecture',
  'review-runtime',
  'review-intent',
]

// ───────────────────────── schemas ─────────────────────────
const SEVERITY = { type: 'string', enum: ['critical', 'high', 'medium', 'low'] }

const FINDING = {
  type: 'object',
  properties: {
    sensor: { type: 'string' },
    location: {
      type: 'object',
      properties: { file: { type: 'string' }, line: { type: 'integer' } },
      required: ['file', 'line'],
    },
    introduced_by_diff: { type: 'boolean' },
    claim: { type: 'string' },
    impact: { type: 'string' },
    trigger: { type: 'string' },
    evidence: { type: 'array', items: { type: 'string' } },
    reproduction_hint: { type: 'string' },
    severity: SEVERITY,
    confidence: { type: 'number' },
  },
  required: ['sensor', 'location', 'introduced_by_diff', 'claim', 'impact', 'trigger', 'evidence', 'severity', 'confidence'],
}

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: { findings: { type: 'array', items: FINDING } },
  required: ['findings'],
}

const PREFLIGHT_SCHEMA = {
  type: 'object',
  properties: {
    gate: { type: 'string', enum: ['OK', 'BLOCK', 'REJECT_INTAKE'] },
    deterministic_gate: { type: 'string', enum: ['pass', 'fail', 'skipped'] },
    gates_run: { type: 'array', items: { type: 'string' } },
    intake: {
      type: 'object',
      properties: {
        score: { type: 'integer' },
        reject: { type: 'boolean' },
        signals: {
          type: 'array',
          items: {
            type: 'object',
            properties: { signal: { type: 'string' }, points: { type: 'integer' } },
            required: ['signal', 'points'],
          },
        },
      },
      required: ['score', 'reject', 'signals'],
    },
    diff: {
      type: 'object',
      properties: {
        changed_files: { type: 'integer' },
        changed_lines: { type: 'integer' },
        high_risk_paths: { type: 'array', items: { type: 'string' } },
        test_weakening: { type: 'boolean' },
        threshold_drop: { type: 'boolean' },
        public_api_or_schema: { type: 'boolean' },
      },
      required: ['changed_files', 'changed_lines'],
    },
    reasons: { type: 'array', items: { type: 'string' } },
  },
  required: ['gate', 'deterministic_gate', 'intake', 'diff'],
}

const ROUTER_SCHEMA = {
  type: 'object',
  properties: {
    risk_level: { type: 'string', enum: ['R0', 'R1', 'R2', 'R3'] },
    score: { type: 'integer' },
    signals: {
      type: 'array',
      items: {
        type: 'object',
        properties: { signal: { type: 'string' }, points: { type: 'integer' } },
        required: ['signal', 'points'],
      },
    },
    sensors: { type: 'array', items: { type: 'string' } },
    recommend_ultrareview: { type: 'boolean' },
    always_human_required: { type: 'boolean' },
    rationale: { type: 'string' },
  },
  required: ['risk_level', 'score', 'signals', 'sensors', 'recommend_ultrareview', 'always_human_required', 'rationale'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    candidate_ref: {
      type: 'object',
      properties: { file: { type: 'string' }, line: { type: 'integer' } },
      required: ['file', 'line'],
    },
    status: { type: 'string', enum: ['verified', 'rejected', 'unresolved'] },
    introduced_by_diff: { type: 'boolean' },
    trigger: { type: ['string', 'null'] },
    evidence: { type: 'array', items: { type: 'string' } },
    rationale: { type: 'string' },
    needs_human: { type: ['string', 'null'] },
    severity: { type: ['string', 'null'], enum: ['critical', 'high', 'medium', 'low', null] },
  },
  required: ['candidate_ref', 'status', 'introduced_by_diff', 'rationale'],
}

const JUDGE_SCHEMA = {
  type: 'object',
  properties: {
    gate: { type: 'string', enum: ['PASS', 'PASS_WITH_NOTES', 'HUMAN_REQUIRED', 'BLOCK', 'REJECT_INTAKE'] },
    risk_level: { type: 'string', enum: ['R0', 'R1', 'R2', 'R3'] },
    blocking_findings: { type: 'array', items: FINDING },
    human_required_reasons: { type: 'array', items: { type: 'string' } },
    notes: { type: 'array', items: FINDING, maxItems: 5 },
    unresolved: { type: 'array', items: FINDING },
    summary_markdown: { type: 'string' },
  },
  required: ['gate', 'risk_level', 'summary_markdown'],
}

// ───────────────────────── prompts ─────────────────────────
const POLICY_PREAMBLE =
  `Read REVIEW.md (repo root) for the static review policy before judging severity.\n` +
  `Target under review: ${target}.\n` +
  `Inspect the changes with: ${diffCmd}\n` +
  (intentFile ? `Per-PR intent/acceptance file: ${intentFile} (read it).\n` : `No intent file supplied.\n`) +
  `You are a read-only sensor. Inspect the diff, and unchanged callers/callees when needed. Do NOT modify files.\n` +
  `Emit ONLY candidates conforming to the review-contract Finding schema; return {"findings": []} when no evidence-supported issue exists.\n` +
  `Do not report CI-deterministic issues (lint/format/type/style/naming). Do not report pre-existing issues the diff did not introduce.\n` +
  `Every finding needs a concrete trigger and file:line evidence, and introduced_by_diff must be true. Max 5 non-blocking findings.`

const SENSOR_BRIEF = {
  'review-correctness':
    `LENS: correctness. Trace the full call chain and state changes. Look for broken invariants, incorrect state transitions, missing error propagation, races/retries/idempotency, edge cases newly introduced, and behavior inconsistent with existing call sites. Treat passing tests as NOT proof of correctness.`,
  'review-test-integrity':
    `LENS: test integrity. Read the TEST diff FIRST. Look for deleted/skipped/loosened assertions, expectations rewritten to match current (possibly wrong) behavior, happy-path-only coverage, and "implementation and test wrong together" collusion. Flag where mutation testing is warranted.`,
  'review-security':
    `LENS: security, organized by trust boundary and data flow (not just dangerous-function matching). Authn/authz, tenant isolation, command/SQL/path/template injection, secrets & PII, SSRF, deserialization, dependency changes, and user-controlled content reaching an LLM prompt / tool call / agent memory.`,
  'review-architecture':
    `LENS: architecture & long-term constraints. Module boundaries and dependency direction, duplicated capability (not duplicated text), public API and backward compatibility, expand/contract on DB migrations, rollout/rollback, and existing domain conventions / ADRs.`,
  'review-runtime':
    `LENS: runtime behavior. Where safe and cheap, run the narrowest targeted/repro test or command. Inspect async timing, resource leaks, timeouts/retries, query counts/performance, and (if available via MCP) historical failure modes from logs/Sentry. Prefer concrete observed behavior over speculation.`,
  'review-intent':
    `LENS: intent vs implementation. Compare the diff against the acceptance criteria and non-goals in the intent file / PR body. Flag unmet acceptance criteria, violated non-goals, undeclared behavior, and missing edge cases the requirement implies. Judge "is this what was asked", NOT "is this elegant".`,
}

function sensorPrompt(name) {
  return `${POLICY_PREAMBLE}\n\n${SENSOR_BRIEF[name] || ''}\n\nYou are sensor "${name}". Return {"findings": [...]} per the review-contract schema.`
}

const ROUTER_PROMPT =
  `You are the risk router. Read REVIEW.md (risk scoring + high-risk paths).\n` +
  `Target: ${target}. Mode: ${mode}.\n` +
  `Inspect the changes with: ${diffCmd}\n` +
  (intentFile ? `Intent file: ${intentFile} (read it; note if acceptance criteria / test evidence are missing).\n` : `No intent file supplied (counts toward intake risk).\n`) +
  `Inspect the diff and its stats. Score the change with the REVIEW.md seed weights, assign a tier R0–R3, and pick the minimal sufficient sensor set from: ${KNOWN_SENSORS.join(', ')}.\n` +
  `Rules: R0 → ["review-correctness"] only. R1 → correctness + test-integrity + security. R2 (any bearing path / test weakening / threshold drop / score ≥5) → add architecture and intent (and runtime when behavior/perf/async is touched), set always_human_required=true and recommend_ultrareview=true. R3 (oversized / no intent / no evidence) → circuit-break: return risk_level "R3" with the smallest sensor set.\n` +
  (mode === 'deep'
    ? `Mode is "deep": include all six sensors unless clearly irrelevant, and recommend_ultrareview=true.\n`
    : '') +
  `Return the review-contract risk-route object.`

function verifierPrompt(c) {
  // Deliberately withhold the originating reviewer's reasoning, impact and evidence chain.
  return (
    `Independently verify ONE candidate code-review finding. Do NOT assume the originating reviewer is correct; try to FALSIFY it first.\n\n` +
    `Target under review: ${target}.\n` +
    `The changes under review come from: ${diffCmd}\n` +
    `Candidate claim: ${c.claim}\n` +
    `Location: ${c.location.file}:${c.location.line}\n` +
    `Reproduction hint: ${c.reproduction_hint || '(none provided)'}\n\n` +
    `Procedure: (1) trace the complete execution path yourself; (2) look for guards, callers, invariants or framework behavior that invalidate the claim; (3) run the narrowest safe command or existing test that can establish behavior; (4) determine whether this is introduced by the target diff.\n` +
    `Return exactly one status: verified | rejected | unresolved. A "verified" verdict requires a concrete trigger AND code/runtime evidence. An "unresolved" verdict must state in needs_human exactly what requires human judgment. Default to rejected/unresolved under uncertainty.\n` +
    `Return the review-contract verdict object (candidate_ref = {file:"${c.location.file}", line:${c.location.line}}).`
  )
}

// ───────────────────────── helpers ─────────────────────────
function dedupeKeepSources(findings) {
  const byKey = new Map()
  for (const f of findings) {
    if (!f || !f.location) continue
    if (!f.trigger || !Array.isArray(f.evidence) || f.evidence.length === 0) continue // evidence bar
    if (f.introduced_by_diff === false) continue
    const claimKey = String(f.claim || '').toLowerCase().replace(/\s+/g, ' ').trim()
    const key = `${f.location.file}:${f.location.line}:${claimKey}`
    const existing = byKey.get(key)
    if (existing) {
      existing.sources = existing.sources || [existing.sensor]
      if (!existing.sources.includes(f.sensor)) existing.sources.push(f.sensor)
      // keep the higher severity / confidence representative
      const rank = { critical: 3, high: 2, medium: 1, low: 0 }
      if ((rank[f.severity] || 0) > (rank[existing.severity] || 0)) existing.severity = f.severity
      existing.confidence = Math.max(existing.confidence || 0, f.confidence || 0)
    } else {
      byKey.set(key, { ...f, sources: [f.sensor] })
    }
  }
  return Array.from(byKey.values())
}

function shouldVerify(c) {
  if (c.severity === 'critical' || c.severity === 'high') return true
  if (c.severity === 'medium' && (c.confidence || 0) > 0.55) return true
  if (mode === 'deep') return true // deep mode verifies everything that cleared the evidence bar
  return false
}

// ───────────────────────── Phase 1: preflight ─────────────────────────
phase('Preflight')
const preflight = await agent(
  `Run the deterministic preflight for this review.\n` +
    (preflightPath
      ? `Run the bundled preflight script at "${preflightPath}" from the repo under review (the current working directory). `
      : `Locate the script (try "$HOME/scripts/review/preflight.sh", else "./scripts/review/preflight.sh") and run it from the repo under review (the current working directory). `) +
    (targetArg === ''
      ? `Run it with NO arguments (working-tree review).\n`
      : `Run it with exactly one argument, quoted verbatim: '${targetArg}'\n`) +
    `Target: ${target}.\n` +
    `The script prints a single JSON object on stdout (gate, deterministic_gate, gates_run, intake, diff, reasons). Run it, capture stdout, and RETURN THAT JSON unchanged (coerced to the PREFLIGHT_SCHEMA). If the script is missing or errors, compute the same fields yourself from \`git diff\` stats and REVIEW.md thresholds, run any obvious lint/type/test command you can detect, and set deterministic_gate accordingly.`,
  { label: 'preflight', phase: 'Preflight', schema: PREFLIGHT_SCHEMA },
)

if (!preflight) {
  log('Preflight agent produced no result — escalating to HUMAN_REQUIRED.')
  return { gate: 'HUMAN_REQUIRED', risk_level: 'R3', summary_markdown: '## Review\nPreflight did not complete; a human must run deterministic gates manually.' }
}
if (preflight.gate === 'BLOCK') {
  log('Deterministic gate failed → BLOCK.')
  return { gate: 'BLOCK', risk_level: 'R0', blocking_findings: [], human_required_reasons: [], notes: [], unresolved: [], summary_markdown: `## BLOCK — deterministic gate failed\n\n- ${(preflight.reasons || ['lint/type/test/security check failed']).join('\n- ')}` }
}
if (preflight.gate === 'REJECT_INTAKE') {
  log('Intake thresholds exceeded → REJECT_INTAKE.')
  return { gate: 'REJECT_INTAKE', risk_level: 'R3', blocking_findings: [], human_required_reasons: [], notes: [], unresolved: [], summary_markdown: `## REJECT_INTAKE — not reviewable as-is\n\n- ${(preflight.reasons || ['missing intent / test evidence, or diff too large']).join('\n- ')}\n\nSplit the change or supply intent + test evidence, then re-run.` }
}

// ───────────────────────── Phase 2: risk routing ─────────────────────────
phase('Risk Routing')
let route = await agent(ROUTER_PROMPT, { agentType: NS + 'review-risk-router', label: 'risk-router', phase: 'Risk Routing', schema: ROUTER_SCHEMA })
if (!route) {
  log('Router produced no result — falling back to a conservative R2 sensor set.')
  route = { risk_level: 'R2', sensors: ['review-correctness', 'review-test-integrity', 'review-security', 'review-architecture', 'review-intent'], recommend_ultrareview: true, always_human_required: true, rationale: 'router failure → conservative default' }
}
let sensors = (route.sensors || []).filter((s) => KNOWN_SENSORS.includes(s))
if (sensors.length === 0) sensors = ['review-correctness']
if (route.risk_level === 'R3') {
  log(`Router circuit-broke at R3: ${route.rationale}`)
  return { gate: 'REJECT_INTAKE', risk_level: 'R3', blocking_findings: [], human_required_reasons: [route.rationale || 'change is not reviewable as-is'], notes: [], unresolved: [], summary_markdown: `## REJECT_INTAKE (R3) — unreviewable\n\n${route.rationale || ''}\n\nSplit the change, add intent, or supply test evidence before review.` }
}
log(`Risk ${route.risk_level}; sensors: ${sensors.join(', ')}${route.recommend_ultrareview ? '; ultrareview recommended' : ''}`)

// ───────────── Phase 3: parallel sensors (BARRIER: dedup needs all candidates) ─────────────
phase('Sensors')
const sensorResults = await parallel(
  sensors.map((name) => () => agent(sensorPrompt(name), { agentType: NS + name, label: `sensor:${name}`, phase: 'Sensors', schema: FINDINGS_SCHEMA })),
)
const rawFindings = sensorResults.filter(Boolean).flatMap((r) => (r && Array.isArray(r.findings) ? r.findings : []))
const candidates = dedupeKeepSources(rawFindings)
log(`${rawFindings.length} raw candidate(s) → ${candidates.length} after evidence bar + dedup (sources preserved, no majority-vote filtering).`)

// ───────────── Phase 4: independent verification (BARRIER: judge needs all verdicts) ─────────────
phase('Verification')
const toVerify = candidates.filter(shouldVerify)
log(`Verifying ${toVerify.length}/${candidates.length} candidate(s) (critical/high, medium>0.55${mode === 'deep' ? ', or all in deep mode' : ''}).`)
const verifiedPairs = (
  await parallel(
    toVerify.map((c) => () =>
      agent(verifierPrompt(c), { agentType: NS + 'review-verifier', label: `verify:${c.location.file}:${c.location.line}`, phase: 'Verification', schema: VERDICT_SCHEMA }).then((v) => ({ candidate: c, verdict: v })),
    ),
  )
)
  .filter(Boolean)
  .filter((p) => p.verdict)

const verified = verifiedPairs.filter((p) => p.verdict.status === 'verified').map((p) => ({ ...p.candidate, severity: p.verdict.severity || p.candidate.severity, trigger: p.verdict.trigger || p.candidate.trigger, evidence: (p.verdict.evidence && p.verdict.evidence.length ? p.verdict.evidence : p.candidate.evidence) }))
const unresolved = verifiedPairs.filter((p) => p.verdict.status === 'unresolved').map((p) => ({ ...p.candidate, reproduction_hint: p.verdict.needs_human || p.candidate.reproduction_hint }))
const notVerifiedNotes = candidates.filter((c) => !toVerify.includes(c)).slice(0, 5) // low/medium that cleared the bar but weren't escalated

// ───────────────────────── Phase 5: judgment ─────────────────────────
phase('Judgment')
const judgePayload = {
  risk_level: route.risk_level,
  always_human_required: route.always_human_required,
  recommend_ultrareview: route.recommend_ultrareview,
  deterministic_gate: preflight.deterministic_gate,
  diff: preflight.diff,
  verified,
  unresolved,
  candidate_notes: notVerifiedNotes,
}
const verdict = await agent(
  `You are the review judge. Read REVIEW.md for gate logic. Synthesize the final gate from this payload (JSON below). Dedupe by root cause, merge related findings, compute blast radius.\n\n` +
    `GATE LOGIC (binding): deterministic_gate=="fail" ⇒ BLOCK; any VERIFIED critical/high ⇒ BLOCK; any unresolved high-risk ⇒ HUMAN_REQUIRED; always_human_required==true (R2) ⇒ HUMAN_REQUIRED even if otherwise clean; only verified low/medium with no human trigger ⇒ PASS_WITH_NOTES; nothing verified and no human trigger ⇒ PASS.\n` +
    `Only VERIFIED findings may appear in blocking_findings. Notes ≤5. Produce a concise human-facing summary_markdown${route.recommend_ultrareview ? ' and remind the human to additionally run `/code-review ultra` for this R2 change' : ''}. Never auto-modify code or auto-merge.\n\n` +
    `PAYLOAD:\n${JSON.stringify(judgePayload, null, 2)}`,
  { agentType: NS + 'review-judge', label: 'judge', phase: 'Judgment', schema: JUDGE_SCHEMA },
)

if (!verdict) {
  return { gate: 'HUMAN_REQUIRED', risk_level: route.risk_level, blocking_findings: verified.filter((f) => f.severity === 'critical' || f.severity === 'high'), human_required_reasons: ['judge agent failed to produce a verdict'], notes: notVerifiedNotes, unresolved, summary_markdown: '## HUMAN_REQUIRED\nJudge did not complete; see verified findings.' }
}

log(`Gate: ${verdict.gate} (risk ${verdict.risk_level}).`)
return verdict
