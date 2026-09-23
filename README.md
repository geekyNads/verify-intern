# VerifyIntern

**An open, community-maintained legitimacy checker for internship and job offers.**

Students get flooded with fake internship offers, "registration fee" scams and
impersonated-employer schemes. Paste an offer here and you get an explanation of
what matched, linked to the public advisory it came from — not a black-box score.

---

## Just want to check an offer?

**Open the site: `https://YOUR-USERNAME.github.io/verifyintern/`**

Nothing to install, nothing to sign up for. Paste the message you received, or
type a company name or website, and press *Check this offer*. Whatever you paste
stays in your browser — the page never uploads it anywhere.

> Replace the link above with your own once you've published it. See
> [Publish your own copy](#publish-your-own-copy-10-minutes-no-coding) — it takes about
> ten minutes and needs no coding.

### Found a scam? Report it

Use the **Report a scam** form on the site, or
[open an issue](../../issues/new?template=scam_report.yml) directly. Reports are
reviewed by a human against the evidence before anything joins the register, so a
report is never published as fact.

If you have already paid someone, report it as fraud first — in India through
[cybercrime.gov.in](https://cybercrime.gov.in) or the 1930 helpline, elsewhere through
your local police and your bank — then come back and file a report here so others
are warned.

---

## What it does

1. **Pattern match.** Flags markers documented in real scams: upfront "registration"
   or "training" fees, payments to personal accounts, lookalike domains, fake
   affiliations with well-known institutes, manufactured urgency, unofficial forms
   asking for academic identifiers.
2. **Register lookup.** Checks a company name, domain or email address against
   records of entities named in public advisories.
3. **Shows its working.** Every result names the pattern that matched, highlights the
   exact words that triggered it, and links to the advisory or article behind it.
4. **Takes reports.** Anyone can submit a suspected scam; a maintainer reviews it
   against the evidence before it enters the dataset.

### What it deliberately does not do

- No automated "definitely a scam" verdict. It surfaces evidence and a confidence
  signal, and always shows its sources.
- No accusing a *named individual* of fraud without a corroborating public source.
  Flags attach to companies, domains and patterns, not to people.
- No wholesale copying of advisory PDFs. Records hold structured facts and a short
  paraphrase, and link to the original.
- **A clean result is not a clean bill of health.** It means nothing in the register
  matched — the register only covers what has been reported and sourced so far.

---

## Publish your own copy (10 minutes, no coding)

You end up with your own live site, your own register, and a report form that files
issues on your repository.

1. **Fork this repository.** Press *Fork* at the top right of the GitHub page.
2. **Turn on Pages.** In your fork: *Settings* → *Pages* → under **Source**, choose
   **GitHub Actions**. That is the only setting you need to change.
3. **Trigger the first build.** Go to the *Actions* tab, pick **Publish site** in the
   sidebar, then *Run workflow*. (Any later change to `data/` or `web/` republishes
   it automatically.)
4. **Open your site** at `https://YOUR-USERNAME.github.io/REPO-NAME/`. The Actions tab
   shows the exact link once the run finishes.

The page works out which repository it belongs to from that URL, so the *Report a
scam* button files issues against your fork with no configuration.

Adding a scam record needs no local setup either: open a scam report issue, and once
you have checked the evidence, add a line to
`data/flagged_employers/flagged_employers.jsonl` through GitHub's own file editor.
Every pull request is checked automatically against the schema and sourcing rules,
so a malformed or unsourced record cannot land.

---

## Run it on your own computer

You need Python 3.9 or newer. Nothing else — no pip install, no accounts.

**Easiest:** double-click `start-windows.bat` (Windows) or `start-mac-linux.command`
(macOS). It builds the site, starts a local server and opens your browser.

**From a terminal:**

```bash
python tools/serve.py
```

**No internet at all?** Run `python tools/build_site.py` and open
`site/verifyintern-offline.html`. That single file carries the page, the rules and the
whole register inside it — it works from a USB stick, which is handy for a placement
cell running a workshop on a locked-down machine.

---

## For developers

The rules live in two mirrored implementations: `api/classifier.py` and
`web/classifier.js`. The browser one is what students actually use; the Python one
backs the optional API. `tests/fixtures/classifier_cases.json` runs through both in CI,
so they cannot drift apart and give two different answers about the same message.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python tools/validate_data.py          # dataset schema + sourcing rules
python -m pytest api/tests -q          # Python rules
node tools/check_parity.cjs            # browser rules agree with Python
python tools/build_site.py             # writes site/
node tools/test_ui.cjs                 # loads the built page and drives it
```

### The optional API

The site needs no backend. The API exists for integrators — placement portals, bots,
bulk checks:

```bash
python -m uvicorn api.main:app --reload --port 8000
```

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | dataset counts |
| `GET /register` | the whole dataset in one response |
| `GET /lookup?query=` | flagged employers matching a name, domain or email |
| `POST /check` | pattern-match pasted offer text |
| `POST /report` | queue a suspected scam for review (writes to `data/_pending/`) |
| `GET /patterns`, `GET /employers` | the two collections on their own |

Interactive docs at `http://127.0.0.1:8000/docs` once it's running. Request bodies are
never stored.

### Adding a record from an advisory (maintainer flow)

```bash
# 1. ingest a candidate — writes to data/_pending/, not to the register
python -m scraper.sources.careers360_advisories \
  --url "https://example.com/advisory" \
  --company-name "Example Corp" \
  --summary "One or two sentences in your own words." \
  --pattern-ids sp_0001 --skip-fetch

# 2. review it
python -m scraper.review_queue list
python -m scraper.review_queue show <id>

# 3. approve — only a human passes --confirm
python -m scraper.review_queue approve <id> --confirm
```

---

## Repo layout

```
web/              the checker itself: one page, one rules file, no backend
data/             the register (JSONL) — this is the actual asset
api/              optional FastAPI service over the same rules
scraper/          ingestion scripts + human review queue
tools/            build, serve, validate, test
tests/fixtures/   cases both classifiers must agree on
docs/             ARCHITECTURE.md, DATA_SCHEMA.md
CLAUDE.md         rules for AI coding agents working in this repo
```

## License

Code: MIT (`LICENSE`). Dataset: CC BY-SA 4.0 (`DATA_LICENSE`) — share-alike, so
downstream commercial forks must keep their derived data open too.

## Status

v0 runs end to end: a seed dataset sourced from public AICTE and IIT Roorkee
advisories, FTC data spotlights and press coverage, a rule-based classifier that cites its sources, a
static site that needs no server, an optional API, a scraper with a human review
queue, and CI that refuses unsourced records and rule drift.
