#!/usr/bin/env node
/**
 * Print a short Playwright JSON-reporter summary for agents (stdout).
 */
import fs from 'node:fs';
import path from 'node:path';

const reportPath = path.resolve('test-results/e2e-results.json');

if (!fs.existsSync(reportPath)) {
  console.log('E2E summary: no test-results/e2e-results.json (suite did not write a report).');
  process.exit(0);
}

const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
const stats = report.stats || {};
const passed = stats.expected ?? 0;
const failed = stats.unexpected ?? 0;
const skipped = stats.skipped ?? 0;
const flaky = stats.flaky ?? 0;

const failures = [];

function walkSuite(suite) {
  for (const spec of suite.specs || []) {
    for (const t of spec.tests || []) {
      const status = t.status || t.results?.[t.results.length - 1]?.status;
      if (status === 'unexpected' || status === 'failed' || status === 'timedOut') {
        const title = [...(suite.titlePath || []), spec.title].filter(Boolean).join(' › ');
        const error =
          t.results?.find((r) => r.error)?.error?.message ||
          t.results?.find((r) => r.errors?.length)?.errors?.[0]?.message ||
          status;
        failures.push({ title: title || spec.title, error: String(error).split('\n')[0] });
      }
    }
  }
  for (const child of suite.suites || []) walkSuite(child);
}

for (const suite of report.suites || []) walkSuite(suite);

console.log(
  `E2E summary: ${passed} passed, ${failed} failed, ${skipped} skipped, ${flaky} flaky`,
);
if (failures.length) {
  console.log('First failures:');
  for (const f of failures.slice(0, 8)) {
    console.log(`  - ${f.title}`);
    if (f.error) console.log(`    ${f.error}`);
  }
}
