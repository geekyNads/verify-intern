## What does this change?

<!-- One or two sentences. If it touches /data, say which records. -->

## Checklist

- [ ] `python tools/validate_data.py` passes
- [ ] `python -m pytest api/tests -q` passes
- [ ] `node tools/check_parity.cjs` passes (required if you touched either classifier)

If this PR touches `/data`:

- [ ] Every new or changed record cites a source a reviewer can open
- [ ] No private individual is named as a fraudster
- [ ] No verbatim text was copied from the source — the summary is in my own words
- [ ] Anything set to `confirmed` was confirmed by a human against the source, not by a script

If this PR touches classification logic:

- [ ] `api/classifier.py` and `web/classifier.js` were changed together
- [ ] A case was added to `tests/fixtures/classifier_cases.json`
- [ ] The result still shows which pattern or record triggered it
