#!/usr/bin/env node
/**
 * Runs the shared fixtures through web/classifier.js.
 *
 * The Python suite runs the same fixtures through api/classifier.py. If the
 * browser and the API ever disagree about the same message, one of them is
 * lying to a student — so CI runs both and fails on any divergence.
 *
 *   node tools/check_parity.cjs
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const VI = require(path.join(ROOT, "web", "classifier.js"));

function loadJsonl(p) {
  return VI.parseJsonl(fs.readFileSync(p, "utf8"));
}

const dataset = {
  flagged_employers: loadJsonl(
    path.join(ROOT, "data", "flagged_employers", "flagged_employers.jsonl")
  ),
  scam_patterns: loadJsonl(path.join(ROOT, "data", "scam_patterns", "scam_patterns.jsonl"))
};

const fixtures = JSON.parse(
  fs.readFileSync(path.join(ROOT, "tests", "fixtures", "classifier_cases.json"), "utf8")
);

let failures = 0;
function check(label, actual, expected) {
  const a = JSON.stringify(actual);
  const e = JSON.stringify(expected);
  if (a !== e) {
    failures++;
    console.error(`FAIL  ${label}\n        expected ${e}\n        actual   ${a}`);
  }
}

for (const c of fixtures.check_cases) {
  const r = VI.checkText(dataset, c.text);
  check(`check/${c.name}/confidence`, r.confidence, c.expect.confidence);
  check(
    `check/${c.name}/patterns`,
    r.matched_patterns.map((m) => m.pattern.id),
    c.expect.pattern_ids
  );
  check(
    `check/${c.name}/employers`,
    r.matched_employers.map((e) => e.id),
    c.expect.employer_ids
  );
}

for (const c of fixtures.lookup_cases) {
  const ids = VI.findEmployers(dataset, c.query).map((e) => e.id);
  check(`lookup/${JSON.stringify(c.query)}`, ids, c.expect_ids);
}

const total = fixtures.check_cases.length + fixtures.lookup_cases.length;
if (failures) {
  console.error(`\n${failures} parity assertion(s) failed across ${total} cases.`);
  process.exit(1);
}
console.log(`web/classifier.js agrees with the shared fixtures (${total} cases).`);
