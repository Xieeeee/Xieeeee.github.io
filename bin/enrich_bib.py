#!/usr/bin/env python3
"""
enrich_bib.py - Enrich papers.bib with doi, html, and altmetric fields
using the CrossRef and Altmetric APIs (no external dependencies required).

Usage:
    python bin/enrich_bib.py                        # uses _bibliography/papers.bib
    python bin/enrich_bib.py path/to/custom.bib
    python bin/enrich_bib.py --dry-run              # preview changes without writing
    python bin/enrich_bib.py --no-altmetric         # skip Altmetric lookups (rate-limited)
"""

import json
import re
import sys
import time
import argparse
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

CROSSREF_UA = "bib-enricher/1.0 (https://github.com/Xieeeee)"


def crossref_lookup(title: str, first_author: str = "") -> tuple[str | None, str | None]:
    """Return (doi, url) from CrossRef, or (None, None) on failure."""
    params = {"query.title": title, "rows": "3"}
    if first_author:
        params["query.author"] = first_author
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_UA})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        items = data.get("message", {}).get("items", [])
        if not items:
            return None, None
        item = items[0]
        doi = item.get("DOI")
        link = item.get("URL") or item.get("resource", {}).get("primary", {}).get("URL")
        return doi, link
    except Exception as e:
        print(f"    [CrossRef error] {e}")
        return None, None


def altmetric_lookup(doi: str, api_key: str = "") -> str | None:
    """Return Altmetric ID string for a DOI, or None.

    Altmetric requires a free API key (register at https://www.altmetric.com/researcher-api-access/).
    Pass via --altmetric-key or set env var ALTMETRIC_KEY.
    """
    base = f"https://api.altmetric.com/v1/doi/{urllib.parse.quote(doi, safe='/')}"
    url = f"{base}?key={api_key}" if api_key else base
    req = urllib.request.Request(url, headers={"User-Agent": CROSSREF_UA})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        aid = data.get("altmetric_id")
        return str(aid) if aid else None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # not tracked yet, that's fine
        if e.code == 403:
            print("    [Altmetric] 403 – API key required. Get a free key at https://www.altmetric.com/researcher-api-access/ then pass --altmetric-key YOUR_KEY")
            return None
        print(f"    [Altmetric error] HTTP {e.code}")
        return None
    except Exception as e:
        print(f"    [Altmetric error] {e}")
        return None


# ---------------------------------------------------------------------------
# Bib parsing (regex-based, preserves original formatting)
# ---------------------------------------------------------------------------

ENTRY_RE = re.compile(
    r"(@\w+\s*\{[^@]*?\n\})",
    re.DOTALL,
)
FIELD_RE = re.compile(r"^\s{2}(\w+)\s*=\s*\{([^}]*)\}", re.MULTILINE)
KEY_RE = re.compile(r"@\w+\s*\{(\S+?),")


def parse_entries(text: str) -> list[dict]:
    """Return list of {key, raw, fields{}} dicts."""
    entries = []
    for m in ENTRY_RE.finditer(text):
        raw = m.group(1)
        key_m = KEY_RE.search(raw)
        key = key_m.group(1) if key_m else "unknown"
        fields = {f.lower(): v.strip() for f, v in FIELD_RE.findall(raw)}
        entries.append({"key": key, "raw": raw, "fields": fields, "span": m.span()})
    return entries


def inject_fields(raw: str, new_fields: dict[str, str]) -> str:
    """Insert new fields before the closing brace of a bib entry."""
    lines = []
    for name, value in new_fields.items():
        lines.append(f"  {name:<12}= {{{value}}},")
    insertion = "\n".join(lines) + "\n"
    # Insert just before the final closing brace
    idx = raw.rfind("\n}")
    if idx == -1:
        return raw
    # Ensure the line just before our insertion ends with a comma
    before = raw[:idx]
    last_line_end = before.rfind("\n")
    last_line = before[last_line_end + 1:]
    if last_line.strip() and not last_line.rstrip().endswith(","):
        before = before[:last_line_end + 1] + last_line.rstrip() + ",\n"
        # strip the trailing newline we just added since we'll add one with insertion
        before = before.rstrip("\n")
    return before + "\n" + insertion + raw[idx:]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Enrich papers.bib with doi/html/altmetric via APIs.")
    parser.add_argument("bib", nargs="?", default="_bibliography/papers.bib", help="Path to .bib file")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing")
    parser.add_argument("--no-altmetric", action="store_true", help="Skip Altmetric lookups")
    parser.add_argument("--altmetric-key", default="", help="Altmetric API key (or set ALTMETRIC_KEY env var)")
    args = parser.parse_args()

    bib_path = Path(args.bib)
    if not bib_path.exists():
        sys.exit(f"File not found: {bib_path}")

    text = bib_path.read_text()
    entries = parse_entries(text)
    print(f"Found {len(entries)} entries in {bib_path}\n")

    # Process each entry, collecting (span, new_raw) replacements
    replacements: list[tuple[tuple[int, int], str]] = []

    for entry in entries:
        key = entry["key"]
        fields = entry["fields"]
        title = fields.get("title", "")
        authors_raw = fields.get("author", "")
        first_author = authors_raw.split(" and ")[0].split(",")[0].strip() if authors_raw else ""

        print(f"[{key}]")
        print(f"  title: {title[:80]}")

        # Determine what's missing
        need_doi  = "doi"  not in fields
        need_html = "html" not in fields
        need_alt  = "altmetric" not in fields and not args.no_altmetric

        if not (need_doi or need_html or need_alt):
            print("  -> all fields present, skipping\n")
            continue

        to_add: dict[str, str] = {}

        # --- CrossRef ---
        doi = fields.get("doi")
        html = fields.get("html")

        if need_doi or need_html:
            print(f"  searching CrossRef (author hint: {first_author})...")
            cr_doi, cr_url = crossref_lookup(title, first_author)
            time.sleep(0.3)  # be polite

            if cr_doi and need_doi:
                to_add["doi"] = cr_doi
                doi = cr_doi
                print(f"  + doi = {cr_doi}")
            elif not cr_doi:
                print("  ! CrossRef: no DOI found")

            if cr_url and need_html:
                to_add["html"] = cr_url
                html = cr_url
                print(f"  + html = {cr_url}")

        # --- Altmetric ---
        if need_alt and doi:
            import os
            api_key = args.altmetric_key or os.environ.get("ALTMETRIC_KEY", "")
            print(f"  looking up Altmetric for doi:{doi}...")
            aid = altmetric_lookup(doi, api_key)
            time.sleep(0.5)
            if aid:
                to_add["altmetric"] = aid
                print(f"  + altmetric = {aid}")
            else:
                print("  ! Altmetric: not tracked yet")

        if to_add:
            new_raw = inject_fields(entry["raw"], to_add)
            replacements.append((entry["span"], new_raw))
        print()

    if not replacements:
        print("Nothing to update.")
        return

    # Apply replacements in reverse order (so offsets stay valid)
    new_text = text
    for (start, end), new_raw in sorted(replacements, key=lambda x: -x[0][0]):
        new_text = new_text[:start] + new_raw + new_text[end:]

    if args.dry_run:
        print("--- DRY RUN: showing updated bib ---\n")
        print(new_text)
    else:
        bib_path.write_text(new_text)
        print(f"Written {len(replacements)} updated entries to {bib_path}")


if __name__ == "__main__":
    main()
