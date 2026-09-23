#!/usr/bin/env node
/**
 * Loads the built page in a headless DOM and exercises it the way a student
 * would. Catches the failure mode that matters most here: the page silently
 * breaking so that a scam message comes back looking clean.
 *
 *   python tools/build_site.py && npm install jsdom --no-save && node tools/test_ui.cjs
 *
 * Skips (exit 0) if jsdom isn't installed, so it never blocks a contributor
 * who only has Python.
 */
const fs = require("fs");
const path = require("path");

let JSDOM, VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = require("jsdom"));
} catch (e) {
  console.log("jsdom not installed — skipping UI test. (npm install jsdom --no-save)");
  process.exit(0);
}

const ROOT = path.resolve(__dirname, "..");
const BUILT = path.join(ROOT, "site", "verifyintern-offline.html");
if (!fs.existsSync(BUILT)) {
  console.error("Build the site first: python tools/build_site.py");
  process.exit(1);
}

const errors = [];
const virtualConsole = new VirtualConsole().on("jsdomError", (e) => {
  // jsdom doesn't implement layout, so scrolling is not a real failure.
  if (!/scrollIntoView/.test(e.message)) errors.push(e.message);
});

const dom = new JSDOM(fs.readFileSync(BUILT, "utf8"), {
  runScripts: "dangerously",
  url: "https://example-user.github.io/verifyintern/",
  virtualConsole
});

const w = dom.window;
const d = w.document;
const $ = (id) => d.getElementById(id);

let failed = 0;
function assert(label, cond, detail) {
  console.log((cond ? "ok   " : "FAIL ") + label + (cond ? "" : "\n       " + detail));
  if (!cond) failed++;
}
function click(id) {
  $(id).dispatchEvent(new w.Event("click"));
}

setTimeout(() => {
  assert("page loads without script errors", errors.length === 0, errors.join(" | "));
  assert("register loads from the bundled data", /scam patterns/.test($("registerCount").textContent), $("registerCount").textContent);
  assert("check button is enabled once data is in", $("checkBtn").disabled === false);
  assert("verification steps are listed", $("adviceList").children.length > 0);
  assert("register browser is populated", $("patternsList").children.length > 0);
  assert("repo is detected from the Pages URL", /example-user\/verifyintern/.test($("repoLinks").innerHTML), $("repoLinks").innerHTML);

  click("sampleBtn");
  const sample = $("result").innerHTML;
  assert("sample scam is flagged", /Treat this as a scam/.test(sample));
  assert("result cites its sources", /<a href="http/.test(sample));
  assert("matched phrases are highlighted", /<mark>/.test(sample));

  $("input").value = '<img src=x onerror=alert(1)> registration fee';
  click("checkBtn");
  assert("pasted markup is escaped, not rendered", !/<img/i.test($("result").innerHTML));

  $("input").value = "aictetindia.org";
  click("checkBtn");
  assert("a bare domain finds its register entry", /register/i.test($("result").innerHTML) && /<mark>/.test($("result").innerHTML));

  $("input").value = "Thank you for applying to Acme Corp. Interview Monday 10am, no payment is required at any stage.";
  click("checkBtn");
  assert("an ordinary offer is not flagged", /Nothing matched the register/.test($("result").innerHTML));

  assert("fraud reporting adapts to region", $("region").options.length > 1);
  $("region").value = "US";
  $("region").dispatchEvent(new w.Event("change"));
  assert("changing region changes the reporting channel", /ftc\.gov/.test($("regionAdvice").innerHTML), $("regionAdvice").innerHTML);

  $("rCompany").value = "";
  $("rReason").value = "";
  click("reportBtn");
  assert("a report without a company is refused", /Add the company/.test($("reportResult").textContent));

  assert("no script errors after interaction", errors.length === 0, errors.join(" | "));

  if (failed) {
    console.error(`\n${failed} UI assertion(s) failed.`);
    process.exit(1);
  }
  console.log("\nUI behaves as expected.");
}, 500);
