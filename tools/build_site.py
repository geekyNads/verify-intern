#!/usr/bin/env python3
"""Build the static site from the repository.

    python tools/build_site.py [--repo owner/name] [--out site]

Produces, in `site/`:

  index.html            the page, unchanged from web/index.html
  classifier.js         the shared rules
  data.json             the whole register, bundled so the page needs no API
  verifyintern-offline.html
                        everything above inlined into one file that works
                        from a USB stick with no internet and no server
  .nojekyll             stops GitHub Pages hiding files it thinks are drafts

Standard library only — someone with a plain Python install can run it.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DATA = ROOT / "data"


def load_jsonl(path: Path) -> list[dict]:
    records = []
    if not path.exists():
        return records
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{path.name} line {lineno} is not valid JSON: {exc}")
    return records


def build_dataset() -> dict:
    return {
        "flagged_employers": load_jsonl(DATA / "flagged_employers" / "flagged_employers.jsonl"),
        "scam_patterns": load_jsonl(DATA / "scam_patterns" / "scam_patterns.jsonl"),
    }


def build(out_dir: Path, repo: str | None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    dataset = build_dataset()
    (out_dir / "data.json").write_text(json.dumps(dataset, indent=1), encoding="utf-8")

    index_html = (WEB / "index.html").read_text(encoding="utf-8")
    classifier_js = (WEB / "classifier.js").read_text(encoding="utf-8")

    if repo:
        index_html = index_html.replace(
            '<script src="classifier.js"></script>',
            f'<script>window.__VERIFYINTERN_REPO__ = {json.dumps(repo)};</script>\n'
            '<script src="classifier.js"></script>',
        )

    (out_dir / "index.html").write_text(index_html, encoding="utf-8")
    (out_dir / "classifier.js").write_text(classifier_js, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    # Single-file build: no server, no network, no install.
    inline_data = json.dumps(dataset)
    standalone = index_html.replace(
        '<script src="classifier.js"></script>',
        "<script>\n"
        + classifier_js
        + "\nwindow.__VERIFYINTERN_DATA__ = "
        + inline_data.replace("</", "<\\/")
        + ";\n</script>",
    )
    # Google Fonts would fail silently offline; fall back to system faces.
    standalone = standalone.replace(
        '<link href="https://fonts.googleapis.com', '<link data-offline-skip href="https://fonts.googleapis.com'
    )
    (out_dir / "verifyintern-offline.html").write_text(standalone, encoding="utf-8")

    for extra in ("README.md",):
        src = ROOT / extra
        if src.exists():
            shutil.copy2(src, out_dir / extra)

    print(f"Built {out_dir.relative_to(ROOT)}/")
    print(f"  {len(dataset['flagged_employers'])} flagged employers, {len(dataset['scam_patterns'])} scam patterns")
    print(f"  single-file copy: {(out_dir / 'verifyintern-offline.html').relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="site", help="Output directory (default: site)")
    ap.add_argument(
        "--repo",
        default=None,
        help="owner/name of the GitHub repo, used for the 'report a scam' link. "
        "On GitHub Pages the page works this out on its own.",
    )
    args = ap.parse_args()
    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    build(out, args.repo)


if __name__ == "__main__":
    main()
