/*!
 * VerifyIntern — shared rule-based classifier (browser + Node).
 *
 * This is a deliberate port of `api/classifier.py`. The two MUST stay in
 * sync: `tools/check_parity.cjs` and `api/tests/test_parity_cases.py` both
 * run the shared cases in `tests/fixtures/classifier_cases.json` through
 * their respective implementations and fail CI if they disagree.
 *
 * Nothing here is a black box: every result points back to the dataset
 * record (and therefore the public source) that produced it.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(); // Node / CI parity check
  } else {
    root.VerifyIntern = factory(); // Browser
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  var SEVERITY_WEIGHT = { high: 40, medium: 20, low: 10 };
  var EMPLOYER_WEIGHT = 60;

  /** Lowercase, fold typographic characters, collapse whitespace. */
  function normalize(text) {
    if (!text) return "";
    var s = String(text);
    if (typeof s.normalize === "function") s = s.normalize("NFKC");
    return s
      .toLowerCase()
      .replace(/[\u2018\u2019\u02bc]/g, "'")
      .replace(/[\u201c\u201d]/g, '"')
      .replace(/[\u2010-\u2015]/g, "-")
      .replace(/[\u200b-\u200d\ufeff]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function escapeRegExp(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  /**
   * Build a whitespace-tolerant, word-boundary-anchored matcher for a hint.
   * "registration  fee" matches "registration\nfee" but "fees" does not
   * produce a match for "fee" alone -> fewer false positives than a raw
   * substring search.
   */
  function hintRegex(hint) {
    var norm = normalize(hint);
    if (!norm) return null;
    var body = norm.split(" ").map(escapeRegExp).join("\\s+");
    var prefix = /^[a-z0-9_]/.test(norm) ? "\\b" : "";
    var suffix = /[a-z0-9_]$/.test(norm) ? "\\b" : "";
    return new RegExp(prefix + body + suffix);
  }

  function containsPhrase(haystackNorm, phrase) {
    var re = hintRegex(phrase);
    return re ? re.test(haystackNorm) : false;
  }

  /** "Careers@Example-Corp.com/jobs" -> "example-corp.com" */
  function extractHost(query) {
    var q = normalize(query);
    if (!q) return "";
    q = q.replace(/^[a-z]+:\/\//, "");
    if (q.indexOf("@") !== -1) q = q.slice(q.lastIndexOf("@") + 1);
    q = q.split("/")[0].split("?")[0].split(" ")[0];
    q = q.replace(/^www\./, "").replace(/\.$/, "");
    return q;
  }

  function domainMatchesQuery(domain, query) {
    var d = normalize(domain).replace(/^www\./, "");
    if (!d) return false;
    var host = extractHost(query);
    var q = normalize(query);
    if (!host && !q) return false;
    if (host === d) return true;
    if (host && host.length > d.length && host.slice(-(d.length + 1)) === "." + d) return true;
    if (q.length >= 4 && d.indexOf(q) !== -1) return true;
    if (d.length >= 4 && q.indexOf(d) !== -1) return true;
    return false;
  }

  function nameMatchesQuery(name, query) {
    var n = normalize(name);
    var q = normalize(query);
    if (!n || q.length < 3) return false;
    if (n === q) return true;
    if (q.length >= 3 && n.indexOf(q) !== -1) return true;
    if (n.length >= 4 && q.indexOf(n) !== -1) return true;
    return false;
  }

  /**
   * Look up an employer record by company name, alias, domain, URL or email.
   * Queries shorter than 3 characters return nothing — otherwise "a" would
   * match half the register.
   */
  function findEmployers(dataset, query) {
    var q = normalize(query);
    if (q.length < 3) return [];
    var out = (dataset.flagged_employers || []).filter(function (emp) {
      var names = [emp.company_name].concat(emp.aliases || []);
      var nameHit = names.some(function (n) {
        return nameMatchesQuery(n, query);
      });
      var domainHit = (emp.domains || []).some(function (d) {
        return domainMatchesQuery(d, query);
      });
      return nameHit || domainHit;
    });
    return out.slice().sort(function (a, b) {
      return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
    });
  }

  /** Employers named directly inside a pasted message. */
  function employersMentionedIn(dataset, textNorm) {
    return (dataset.flagged_employers || [])
      .filter(function (emp) {
        var names = [emp.company_name]
          .concat(emp.aliases || [])
          .filter(function (n) {
            return normalize(n).length >= 5;
          });
        var nameHit = names.some(function (n) {
          return containsPhrase(textNorm, n);
        });
        var domainHit = (emp.domains || []).some(function (d) {
          return containsPhrase(textNorm, d);
        });
        return nameHit || domainHit;
      })
      .sort(function (a, b) {
        return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
      });
  }

  var GENERAL_ADVICE = [
    "A legitimate employer never asks you to pay for a job, an interview, a training kit or a \u201cseat\u201d.",
    "Look up the company's phone number or email yourself, from a search engine or the institution's official site \u2014 never from the message you received.",
    "Check the sender's email domain character by character against the real one. Lookalike domains are the most common trick.",
    "Ask for the offer on letterhead with a named HR contact, and call the company's published switchboard to confirm that person exists.",
    "Never share bank details, OTPs, Aadhaar/PAN or your full date of birth to \u201cverify\u201d an internship offer."
  ];

  /**
   * Classify pasted offer text against the dataset.
   * Returns matched patterns (with the exact phrases that matched), matched
   * employer records, a confidence band, a 0-100 score for display, and a
   * plain-language explanation.
   */
  function checkText(dataset, text) {
    var textNorm = normalize(text);
    var matched = [];

    (dataset.scam_patterns || []).forEach(function (pattern) {
      var hits = (pattern.detection_hints || []).filter(function (hint) {
        return containsPhrase(textNorm, hint);
      });
      if (hits.length) matched.push({ pattern: pattern, matched_hints: hits });
    });

    matched.sort(function (a, b) {
      return a.pattern.id < b.pattern.id ? -1 : a.pattern.id > b.pattern.id ? 1 : 0;
    });

    var matchedEmployers = employersMentionedIn(dataset, textNorm);

    var highHits = matched.filter(function (m) {
      return m.pattern.severity === "high";
    }).length;

    // Mirrors api/classifier.py: a high-severity marker corroborated by any
    // second pattern counts as high; a lone high-severity hit stays at medium.
    var corroborated = highHits >= 1 && matched.length >= 2;
    var confidence;
    if (matchedEmployers.length || highHits >= 2 || corroborated) confidence = "high";
    else if (highHits === 1 || matched.length >= 2) confidence = "medium";
    else if (matched.length) confidence = "low";
    else confidence = "none";

    var score = 0;
    matched.forEach(function (m) {
      score += SEVERITY_WEIGHT[m.pattern.severity] || 0;
    });
    if (matchedEmployers.length) score += EMPLOYER_WEIGHT;
    score = Math.min(100, score);

    var explanation;
    if (confidence === "none") {
      explanation =
        "No known scam patterns or flagged employers matched this text. " +
        "This is not a guarantee the offer is legitimate \u2014 it only means " +
        "nothing in the current dataset matched. Always verify independently.";
    } else {
      var names = matched
        .map(function (m) {
          return m.pattern.name;
        })
        .join(", ");
      explanation = "Matched pattern(s): " + (names || "none") + ".";
      if (matchedEmployers.length) {
        explanation +=
          " Matched flagged record(s): " +
          matchedEmployers
            .map(function (e) {
              return e.company_name;
            })
            .join(", ") +
          ".";
      }
    }

    return {
      matched_patterns: matched,
      matched_employers: matchedEmployers,
      confidence: confidence,
      score: score,
      explanation: explanation,
      advice: GENERAL_ADVICE.slice()
    };
  }

  /** Parse a JSONL file body into records, skipping blank lines. */
  function parseJsonl(body) {
    return body
      .split("\n")
      .map(function (line) {
        return line.trim();
      })
      .filter(Boolean)
      .map(function (line) {
        return JSON.parse(line);
      });
  }

  return {
    normalize: normalize,
    parseJsonl: parseJsonl,
    findEmployers: findEmployers,
    checkText: checkText,
    GENERAL_ADVICE: GENERAL_ADVICE
  };
});
