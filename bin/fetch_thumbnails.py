#!/usr/bin/env python3
"""
fetch_thumbnails.py - Auto-download journal cover / og:image thumbnails for papers.bib.

Strategy per publisher:
  - bioRxiv / medRxiv : use their logo directly (no paper-specific image available)
  - Nature / Springer : og:image (works well)
  - Science           : try enhanced browser headers; fall back to Science logo
  - Unknown / failure : fall back to journal logo if known, else skip

Usage:
    python bin/fetch_thumbnails.py                    # uses _bibliography/papers.bib
    python bin/fetch_thumbnails.py path/to/other.bib
    python bin/fetch_thumbnails.py --dry-run          # show what would be fetched
    python bin/fetch_thumbnails.py --force            # re-fetch even if preview already set
"""

import argparse
import mimetypes
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PREVIEW_DIR = Path("assets/img/publication_preview")

# ---------------------------------------------------------------------------
# Known fallback logos  (filename_stem, logo_url)
# Keyed by lowercase journal name or DOI prefix
# ---------------------------------------------------------------------------
FALLBACK_LOGOS = {
    "biorxiv":  ("biorxiv_logo",  "https://upload.wikimedia.org/wikipedia/commons/d/db/BioRxiv_logo.png"),
    "medrxiv":  ("medrxiv_logo",  "https://upload.wikimedia.org/wikipedia/commons/c/c6/MedRxiv_homepage_logo.png"),
    "science":  ("science_logo",  "https://upload.wikimedia.org/wikipedia/commons/e/eb/Science_Magazine_logo.svg"),
    "10.1126":  ("science_logo",  "https://upload.wikimedia.org/wikipedia/commons/e/eb/Science_Magazine_logo.svg"),
    "10.64898": ("biorxiv_logo",  "https://upload.wikimedia.org/wikipedia/commons/d/db/BioRxiv_logo.png"),
}

# Headers that mimic a real browser (helps with Science and similar)
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "no-cache",
}

# ---------------------------------------------------------------------------
# Bib parsing
# ---------------------------------------------------------------------------

ENTRY_RE = re.compile(r"(@\w+\s*\{[^@]*?\n\})", re.DOTALL)
FIELD_RE = re.compile(r"^\s{2}(\w+)\s*=\s*\{([^}]*)\}", re.MULTILINE)
KEY_RE   = re.compile(r"@\w+\s*\{(\S+?),")


def parse_entries(text):
    entries = []
    for m in ENTRY_RE.finditer(text):
        raw = m.group(1)
        key = KEY_RE.search(raw).group(1)
        fields = {f.lower(): v.strip() for f, v in FIELD_RE.findall(raw)}
        entries.append({"key": key, "raw": raw, "fields": fields, "span": m.span()})
    return entries


def inject_field(raw, name, value):
    line = f"  {name:<12}= {{{value}}},"
    idx = raw.rfind("\n}")
    if idx == -1:
        return raw
    before = raw[:idx]
    last_nl = before.rfind("\n")
    last_line = before[last_nl + 1:]
    if last_line.strip() and not last_line.rstrip().endswith(","):
        before = before[:last_nl + 1] + last_line.rstrip() + ","
    return before + "\n" + line + "\n" + raw[idx:]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch_url(url, extra_headers=None, timeout=15):
    headers = {**BROWSER_HEADERS, **(extra_headers or {})}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.url, r.read().decode("utf-8", errors="replace")


def extract_og_image(html):
    for pattern in [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ]:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def download_image(img_url, dest_path, timeout=20):
    req = urllib.request.Request(img_url, headers=BROWSER_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            content_type = r.headers.get_content_type()
        if dest_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
            ext = mimetypes.guess_extension(content_type) or ".jpg"
            ext = ext.replace(".jpe", ".jpg")
            dest_path = dest_path.with_suffix(ext)
        dest_path.write_bytes(data)
        return dest_path
    except Exception as e:
        print(f"    [download error] {e}")
        return None


# ---------------------------------------------------------------------------
# Publisher detection
# ---------------------------------------------------------------------------

def detect_fallback(journal: str, doi: str) -> tuple[str, str] | None:
    """Return (stem, logo_url) if we recognise this as a known publisher."""
    j = journal.lower()
    if j in FALLBACK_LOGOS:
        return FALLBACK_LOGOS[j]
    doi_prefix = doi.split("/")[0] if "/" in doi else ""
    if doi_prefix in FALLBACK_LOGOS:
        return FALLBACK_LOGOS[doi_prefix]
    return None


def get_or_download_logo(stem: str, logo_url: str, dry_run: bool) -> str | None:
    """Download a shared logo once and reuse it. Returns filename."""
    # Guess extension from URL
    ext = Path(urllib.parse.urlparse(logo_url).path).suffix.lower() or ".png"
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}:
        ext = ".png"
    filename = f"{stem}{ext}"
    dest = PREVIEW_DIR / filename
    if dest.exists():
        print(f"  logo   → {filename} (cached)")
        return filename
    time.sleep(1.5)  # be polite to Wikimedia
    if dry_run:
        print(f"  logo   → {filename} (would download {logo_url[:70]})")
        return filename
    saved = download_image(logo_url, dest)
    if saved:
        print(f"  logo   → {saved.name}")
        return saved.name
    return None


# ---------------------------------------------------------------------------
# Science-specific fetch (tries several header combos)
# ---------------------------------------------------------------------------

def fetch_science(doi: str):
    """Try multiple approaches to get Science og:image. Returns img_url or None."""
    candidates = [
        f"https://www.science.org/doi/abs/{doi}",
        f"https://www.science.org/doi/{doi}",
    ]
    referer_headers = {**BROWSER_HEADERS, "Referer": "https://www.google.com/"}
    for url in candidates:
        for hdrs in [BROWSER_HEADERS, referer_headers]:
            try:
                _, html = fetch_url(url, extra_headers=hdrs, timeout=20)
                img = extract_og_image(html)
                if img:
                    return img
            except urllib.error.HTTPError as e:
                print(f"    [Science] {url} → HTTP {e.code}")
            except Exception as e:
                print(f"    [Science] {url} → {e}")
            time.sleep(0.5)
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def sanitize(key):
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", key)


def main():
    parser = argparse.ArgumentParser(description="Fetch journal cover thumbnails for papers.bib.")
    parser.add_argument("bib", nargs="?", default="_bibliography/papers.bib")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true", help="Re-fetch even if preview already set")
    args = parser.parse_args()

    bib_path = Path(args.bib)
    if not bib_path.exists():
        sys.exit(f"File not found: {bib_path}")

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    text     = bib_path.read_text()
    entries  = parse_entries(text)
    print(f"Found {len(entries)} entries in {bib_path}\n")

    replacements = []

    for entry in entries:
        key     = entry["key"]
        fields  = entry["fields"]

        if not args.force and "preview" in fields:
            print(f"[{key}] preview already set → skipping")
            continue

        doi     = fields.get("doi", "")
        html    = fields.get("html", "")
        journal = fields.get("journal", "")

        if not doi and not html:
            print(f"[{key}] no doi or html → skipping\n")
            continue

        print(f"[{key}]  journal={journal}")

        filename = None

        # ── 1. Known preprint servers: use logo directly ────────────────────
        fallback = detect_fallback(journal, doi)
        is_preprint = journal.lower() in ("biorxiv", "medrxiv")

        if is_preprint and fallback:
            stem, logo_url = fallback
            filename = get_or_download_logo(stem, logo_url, args.dry_run)

        # ── 2. Science: try enhanced fetch ──────────────────────────────────
        elif journal.lower() == "science" or doi.startswith("10.1126"):
            print(f"  trying Science page (enhanced headers)...")
            if not args.dry_run:
                img_url = fetch_science(doi)
                if img_url:
                    print(f"  og:image → {img_url[:80]}")
                    ext = Path(urllib.parse.urlparse(img_url).path).suffix.lower() or ".jpg"
                    dest = PREVIEW_DIR / f"{sanitize(key)}{ext}"
                    saved = download_image(img_url, dest)
                    if saved:
                        filename = saved.name
                        print(f"  saved  → {saved}")
                if not filename:
                    print("  ! Science fetch failed → using Science logo")
                    stem, logo_url = FALLBACK_LOGOS["science"]
                    filename = get_or_download_logo(stem, logo_url, args.dry_run)

        # ── 3. Generic og:image scrape ──────────────────────────────────────
        else:
            start_url = f"https://doi.org/{doi}" if doi else html
            print(f"  fetching {start_url} ...")
            if not args.dry_run:
                try:
                    final_url, html_text = fetch_url(start_url)
                    time.sleep(0.5)
                    img_url = extract_og_image(html_text)
                    if img_url:
                        if img_url.startswith("//"):
                            img_url = "https:" + img_url
                        elif img_url.startswith("/"):
                            p = urllib.parse.urlparse(final_url)
                            img_url = f"{p.scheme}://{p.netloc}{img_url}"
                        print(f"  og:image → {img_url[:80]}")
                        ext = Path(urllib.parse.urlparse(img_url).path).suffix.lower() or ".jpg"
                        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                            ext = ".jpg"
                        dest = PREVIEW_DIR / f"{sanitize(key)}{ext}"
                        saved = download_image(img_url, dest)
                        if saved:
                            filename = saved.name
                            print(f"  saved  → {saved}")
                    else:
                        print("  ! no og:image found")
                except Exception as e:
                    print(f"  ! fetch failed: {e}")

                # fallback to logo on any failure
                if not filename:
                    fb = detect_fallback(journal, doi)
                    if fb:
                        stem, logo_url = fb
                        print(f"  falling back to logo...")
                        filename = get_or_download_logo(stem, logo_url, args.dry_run)

        if filename:
            new_raw = inject_field(entry["raw"], "preview", filename)
            replacements.append((entry["span"], new_raw))
        print()

        time.sleep(0.8)

    if not replacements:
        if not args.dry_run:
            print("Nothing to update.")
        return

    new_text = text
    for (start, end), new_raw in sorted(replacements, key=lambda x: -x[0][0]):
        new_text = new_text[:start] + new_raw + new_text[end:]

    if args.dry_run:
        print("(dry-run: bib not written)")
    else:
        bib_path.write_text(new_text)
        print(f"Updated {len(replacements)} entries in {bib_path}")


if __name__ == "__main__":
    main()
