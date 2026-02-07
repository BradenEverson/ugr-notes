#!/usr/bin/env python3
"""
build_static_site.py

Build a static, FTP-friendly site from analysis outputs.

WHAT IT DOES
------------
- Scans an output root (e.g., ./out_per_file) for per-test directories produced by your binner.
  Each test directory is expected to include:
     *_cpu_pct_overlay.png                (the overlay chart we want to publish)
     *_waitrun_*us.csv                    (ignored; CSVs are NOT copied)
- Groups tests by "suite" using the directory name before a trailing '_<number>'.
  Example: 'cpu_intensive_1' -> suite 'cpu_intensive'
           'io_intensive_3'  -> suite 'io_intensive'
- Builds a portable site under --out-dir:
     out-dir/
       index.html
       styles.css
       assets/
         img/
           <suite>/
             <test-stem>.png     (copied overlay image)
- Adds nav tabs (one per suite), and a grid of images per suite.
- Optional: reads test titles from a bash file that echos
      "=== Test N: Title ==="
  and maps them to the correct test numbers (READ-ONLY; never executed).

WHAT IT DOES NOT DO
-------------------
- It does NOT copy CSV files.
- It does NOT convert images or change resolution (keeps your PNGs intact).
- It does NOT run any of your workloads.

USAGE
-----
  python build_static_site.py \
    --in-root ./out_per_file \
    --out-dir ./site_pkg \
    --title-map-sh ./cpu_intensive.sh \
    --site-title "System Call Traces — Benchmark Gallery"

OPTIONS
-------
- --in-root             Root folder containing per-test subfolders.
- --out-dir             Destination folder for the site (created if missing).
- --title-map-sh        Optional path to a bash driver with lines like:
                          echo "=== Test 1: Large file compression ==="
                        The script only reads this file as text to map titles.
- --stem-number-regex   Regex to extract the test number from folder names (default: r'_(\\d+)$').
- --site-title          Text used in the page header and <title>.
"""

from __future__ import annotations
import argparse
import html
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


# ---------- Utilities ----------
def extract_test_number(stem: str, regex: str) -> int | None:
    """Extract integer test number from a name like 'cpu_intensive_17' using regex (default '_(\\d+)$')."""
    m = re.search(regex, stem)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def suite_key_from_stem(stem: str) -> str:
    """'cpu_intensive_17' -> 'cpu_intensive'; if no trailing _<digits>, return stem as-is."""
    return re.sub(r'_\d+$', '', stem)


def titlecase_suite(suite: str) -> str:
    """'cpu_intensive' -> 'CPU Intensive'"""
    return ' '.join([w.capitalize() if w.islower() else w for w in suite.replace('_', ' ').split()])


def slug(s: str) -> str:
    """Safe-ish filename slug for copying assets."""
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'[^-_.A-Za-z0-9]+', '-', s)
    return s.strip('-_') or "item"


# ---------- Title parsing from bash driver (READ-ONLY; never executed) ----------
def parse_test_labels_from_bash(sh_path: str) -> Dict[int, str]:
    """
    Parse titles from a shell script that prints headings like:
      echo "=== Test 1: Large file compression ==="

    Strategy:
      * Prefer quoted fragment if present.
      * Extract 'Test <N>: <Label>'.
      * Strip leading/trailing '=' runs and whitespace from <Label>.
      * Collapse internal whitespace.

    Returns: {1: 'Large file compression', 2: 'Decompression', ...}
    """
    if not sh_path:
        return {}
    p = Path(sh_path)
    if not p.exists():
        raise FileNotFoundError(f"--title-map-sh not found: {sh_path}")

    test_map: Dict[int, str] = {}
    pat = re.compile(r'(?i)Test\s*(\d+)\s*:\s*(.+)')

    def clean_label(txt: str) -> str:
        txt = re.sub(r'^\s*=+\s*', '', txt)    # strip leading ===
        txt = re.sub(r'\s*=+\s*$', '', txt)    # strip trailing ===
        txt = txt.strip().strip('"').strip("'")
        txt = re.sub(r'\s+', ' ', txt).strip()
        return txt

    with p.open('r', encoding='utf-8', errors='ignore') as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            # Prefer last quoted segment if present
            q = list(re.finditer(r'(["\'])(.*?)\1', line))
            candidates = [q[-1].group(2)] if q else [line]
            for text in candidates:
                m = pat.search(text)
                if not m:
                    continue
                idx = int(m.group(1))
                label = clean_label(m.group(2))
                if label:
                    test_map[idx] = label
                    break
    return test_map


# ---------- Site builder ----------
def collect_tests(in_root: Path,
                  stem_number_regex: str,
                  title_map: Dict[int, str]) -> Dict[str, List[Tuple[str, int | None, Path]]]:
    """
    Scan in_root/* for per-test subdirectories, each containing:
      - *_cpu_pct_overlay.png (we copy this)
    Return mapping: suite_key -> list of (display_title, test_num, png_path)
    """
    suites: Dict[str, List[Tuple[str, int | None, Path]]] = {}

    for child in sorted(in_root.iterdir()):
        if not child.is_dir():
            continue
        stem = child.name  # e.g., 'cpu_intensive_1'
        test_num = extract_test_number(stem, stem_number_regex)
        suite = suite_key_from_stem(stem)

        # pick the overlay plot
        pngs = sorted(child.glob('*_cpu_pct_overlay.png'))
        if not pngs:
            continue  # nothing to publish for this test
        png = pngs[0]

        # Build display title
        if test_num is not None and test_num in title_map:
            disp = f"{title_map[test_num]} (Test {test_num})"
        elif test_num is not None:
            disp = f"Test {test_num} ({stem})"
        else:
            disp = stem

        suites.setdefault(suite, []).append((disp, test_num, png))

    # Sort within suite: by test number if present, else by title
    for suite, items in suites.items():
        items.sort(key=lambda t: (t[1] is None, t[1] if t[1] is not None else 10**9, t[0].lower()))
    return suites


def write_css(dest_css: Path) -> None:
    css = r"""
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
header { padding: 16px 20px; border-bottom: 1px solid #ddd; }
h1 { margin: 0; font-size: 1.25rem; }
.nav { display: flex; gap: 8px; padding: 12px 20px; border-bottom: 1px solid #ddd; flex-wrap: wrap; }
.nav button { border: 1px solid #999; background: #f6f6f6; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
.nav button.active { background: #0366d6; color: #fff; border-color: #0366d6; }
.container { padding: 16px 20px 40px; }
.tab { display: none; }
.tab.active { display: block; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.card { border: 1px solid #ddd; border-radius: 8px; padding: 12px; background: #fff; }
.card h3 { margin: 0 0 8px 0; font-size: 1rem; }
.card .media { display: block; border: 1px solid #ccc; border-radius: 6px; overflow: hidden; background: #fafafa; }
.card .media img { display: block; width: 100%; height: auto; }
footer { padding: 16px 20px; border-top: 1px solid #ddd; font-size: 0.9rem; color: #666; }
@media (prefers-color-scheme: dark) {
  body { background: #111; color: #e6e6e6; }
  header, .nav, footer { border-color: #333; }
  .card { background: #1a1a1a; border-color: #333; }
  .card .media { background: #151515; border-color: #333; }
  .nav button { background: #222; border-color: #555; color: #e6e6e6; }
  .nav button.active { background: #0a57c7; border-color: #0a57c7; }
}
"""
    dest_css.write_text(css.strip() + "\n", encoding="utf-8")


def build_index_html(out_dir: Path,
                     site_title: str,
                     suites: Dict[str, List[Tuple[str, int | None, Path]]],
                     img_root_rel: str) -> None:
    # Minimal inline JS for tabs + persisted selection
    js = r"""
function openTab(idx) {
  const tabs = document.querySelectorAll('.tab');
  const buttons = document.querySelectorAll('.nav button');
  tabs.forEach((t,i) => t.classList.toggle('active', i===idx));
  buttons.forEach((b,i) => b.classList.toggle('active', i===idx));
  try { localStorage.setItem('suiteTabIndex', String(idx)); } catch(e) {}
}
window.addEventListener('DOMContentLoaded', () => {
  let idx = 0;
  try { const s=localStorage.getItem('suiteTabIndex'); if(s!==null) idx = parseInt(s,10)||0; } catch(e) {}
  openTab(idx);
});
""".strip()

    suite_keys = sorted(suites.keys())
    # Build nav
    nav_html = []
    for i, key in enumerate(suite_keys):
        label = html.escape(titlecase_suite(key))
        nav_html.append(f'<button type="button" onclick="openTab({i})">{label}</button>')
    nav_html = "\n    ".join(nav_html)

    # Build tabs
    tabs_html_parts = []
    for i, key in enumerate(suite_keys):
        items = suites[key]
        grid_items = []
        for disp, test_num, src_png in items:
            caption = html.escape(disp)
            # We copied images to assets/img/<suite>/<slug>.png
            target_rel = f"{img_root_rel}/{key}/{slug(src_png.parent.name)}.png"
            img_tag = (f'<a class="media" href="{html.escape(target_rel)}" target="_blank" rel="noopener">'
                       f'<img src="{html.escape(target_rel)}" alt="{caption}"></a>')
            card = f"""
      <div class="card">
        <h3>{caption}</h3>
        {img_tag}
      </div>""".rstrip()
            grid_items.append(card)
        grid_html = "\n".join(grid_items) if grid_items else "<p>No graphs found in this suite.</p>"
        tab = f"""
  <section class="tab" id="tab-{i}">
    <div class="grid">
{grid_html}
    </div>
  </section>""".rstrip()
        tabs_html_parts.append(tab)
    tabs_html = "\n".join(tabs_html_parts)

    # Final HTML
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(site_title)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preload" href="styles.css" as="style">
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header>
    <h1>{html.escape(site_title)}</h1>
  </header>
  <nav class="nav">
    {nav_html}
  </nav>
  <main class="container">
{tabs_html}
  </main>
  <footer>
    Packaged by build_static_site.py — CSV files omitted by design.
  </footer>
  <script>
{js}
  </script>
</body>
</html>
"""
    (out_dir / "index.html").write_text(html_doc, encoding="utf-8")


def copy_images(suites: Dict[str, List[Tuple[str, int | None, Path]]],
                dest_img_root: Path) -> None:
    """
    Copy overlay images into assets/img/<suite>/<slug(stem)>.png
    """
    for suite, items in suites.items():
        suite_dir = dest_img_root / suite
        suite_dir.mkdir(parents=True, exist_ok=True)
        for _, __, src_png in items:
            dst_name = slug(src_png.parent.name) + ".png"
            dst = suite_dir / dst_name
            shutil.copy2(src_png, dst)


def main():
    ap = argparse.ArgumentParser(description="Build a static, FTP-friendly site for graphs (no CSVs).")
    ap.add_argument("--in-root", required=True,
                    help="Root directory containing per-test subfolders (e.g., ./out_per_file).")
    ap.add_argument("--out-dir", required=True,
                    help="Destination directory for the site (created if missing).")
    ap.add_argument("--title-map-sh", default=None,
                    help="Optional path to bash script with echoed '=== Test N: Name ===' lines (read-only, not executed).")
    ap.add_argument("--stem-number-regex", default=r'_(\d+)$',
                    help="Regex to extract test number from directory name (default matches trailing _NNN).")
    ap.add_argument("--site-title", default="System Call Traces — Benchmark Gallery",
                    help="Title for the site header and <title> tag.")
    args = ap.parse_args()

    in_root = Path(args.in_root).resolve()
    out_dir = Path(args.out_dir).resolve()

    if not in_root.exists():
        raise SystemExit(f"--in-root not found: {in_root}")

    out_dir.mkdir(parents=True, exist_ok=True)

    title_map = parse_test_labels_from_bash(args.title_map_sh) if args.title_map_sh else {}
    suites = collect_tests(in_root, args.stem_number_regex, title_map)

    # Write CSS
    write_css(out_dir / "styles.css")

    # Copy images only
    img_root = out_dir / "assets" / "img"
    img_root.mkdir(parents=True, exist_ok=True)
    copy_images(suites, img_root)

    # Build HTML with relative paths
    build_index_html(out_dir, args.site_title, suites, img_root_rel="assets/img")

    print(f"[OK] Site packaged at: {out_dir}")
    print("     Upload this entire directory to your web server (FTP/SFTP/rsync).")
    print("     Entry point: index.html")


if __name__ == "__main__":
    main()