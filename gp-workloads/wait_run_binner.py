#!/usr/bin/env python3
"""
wait_run_binner_multi_plot_titles.py

- Processes multiple input CSVs (globs ok)
- Aggregates waiting vs. running for multiple bin sizes in one pass
- Normalizes time so all outputs start at t = 0
- Generates one overlay chart per input file (CPU running % vs time)
- Reads human-friendly test names from a bash script that contains lines like:
    echo "=== Test 1: Large file compression ==="

IMPORTANT: This script ONLY READS the .sh file as TEXT; it NEVER executes it.
"""

from __future__ import annotations
import argparse
import glob
import math
import os
import re
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# -------------------------------------------------
# Title mapping from bash "=== Test N: Name ===" lines (read-only, no exec)
# -------------------------------------------------
def parse_test_labels_from_bash(sh_path: str) -> Dict[int, str]:
    """
    Parse titles from a shell script that prints headings like:
      echo "=== Test 1: Large file compression ==="

    Strategy:
      1) Prefer parsing the QUOTED portion of any echo-ish line.
      2) From that text, extract 'Test <N>: <Label>'.
      3) Sanitize <Label> by stripping BOTH leading and trailing runs of '='
         (and surrounding spaces) and collapsing whitespace.

    Returns: {1: 'Large file compression', 2: 'Decompression', ...}

    NOTE: This function only READS the .sh as text; it NEVER executes it.
    """
    if not sh_path:
        return {}
    if not os.path.exists(sh_path):
        raise FileNotFoundError(f"--title-map-sh path not found: {sh_path}")

    test_map: Dict[int, str] = {}

    # We’ll search inside quotes when present; otherwise use the whole line.
    quoted_fragment = re.compile(r'["\'](.*?)["\']')  # capture text inside quotes
    test_pat = re.compile(r'(?i)Test\s*(\d+)\s*:\s*(.+)')  # Test N: Label

    def clean_label(txt: str) -> str:
        # Strip leading/trailing sequences of '=' (+ nearby spaces), quotes, and collapse spaces
        txt = re.sub(r'^\s*=+\s*', '', txt)
        txt = re.sub(r'\s*=+\s*$', '', txt)
        txt = txt.strip().strip('"').strip("'")
        txt = re.sub(r'\s+', ' ', txt).strip()
        return txt

    with open(sh_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue

            # Prefer last quoted chunk if any; else use full line
            qs = quoted_fragment.findall(line)
            candidates = [qs[-1]] if qs else [line]

            for text in candidates:
                m = test_pat.search(text)
                if not m:
                    continue
                idx = int(m.group(1))
                label_raw = m.group(2)
                label = clean_label(label_raw)
                if label:
                    test_map[idx] = label
                    break

    return test_map


def extract_test_number_from_stem(stem: str, regex: str) -> int | None:
    """
    Extract an integer test number from a filename stem using a user-supplied regex.
    Default matches digits after an underscore at end: r'_(\\d+)$'
    """
    m = re.search(regex, stem)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


# -------------------------------------------------
# Core processing logic (time-normalized)
# -------------------------------------------------
def load_intervals(csv_path: str,
                   relative_time_col: str = "relative_time",
                   duration_us_col: str = "duration_us"
                   ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load a CSV -> [start_us, end_us) intervals, normalized so the first event is at t=0.
    CSV is expected to match trace columns:
      - relative_time (seconds)
      - duration_us (microseconds)
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower().replace("\\", "") for c in df.columns]

    rel_col = next((c for c in df.columns if c == relative_time_col.lower()), None)
    dur_col = next((c for c in df.columns if c == duration_us_col.lower()), None)
    if rel_col is None or dur_col is None:
        raise ValueError(
            f"{csv_path}: expected columns '{relative_time_col}' and '{duration_us_col}'. "
            f"Found: {list(df.columns)}"
        )

    df[rel_col] = pd.to_numeric(df[rel_col], errors="coerce")
    df[dur_col] = pd.to_numeric(df[dur_col], errors="coerce")
    df = df.dropna(subset=[rel_col, dur_col]).copy()
    if df.empty:
        return np.empty((0,), dtype=np.int64), np.empty((0,), dtype=np.int64)

    # Normalize so earliest time is 0
    t0 = float(df[rel_col].min())
    rel_norm = df[rel_col] - t0
    start_us = np.rint(rel_norm.values * 1_000_000.0).astype(np.int64)

    dur_us = np.ceil(np.maximum(df[dur_col].values, 0)).astype(np.int64)  # clip negatives to 0
    end_us = start_us + dur_us

    # Keep only positive-length intervals
    valid = end_us > start_us
    start_us = start_us[valid]
    end_us = end_us[valid]

    # Sort by start (stable)
    order = np.argsort(start_us, kind="mergesort")
    return start_us[order], end_us[order]


def merge_intervals(starts: np.ndarray, ends: np.ndarray) -> np.ndarray:
    """
    Merge overlapping / adjacent [start_us, end_us) intervals.
    """
    if starts.size == 0:
        return np.empty((0, 2), dtype=np.int64)

    merged = []
    for s, e in zip(starts, ends):
        if not merged:
            merged.append([int(s), int(e)])
        else:
            if s <= merged[-1][1]:
                if e > merged[-1][1]:
                    merged[-1][1] = int(e)
            else:
                merged.append([int(s), int(e)])
    return np.array(merged, dtype=np.int64)


def bin_wait_run(merged: np.ndarray, bin_size_us: int) -> pd.DataFrame:
    """
    Aggregate waiting vs. running per fixed-size time slice.
    """
    if merged.size == 0:
        return pd.DataFrame(columns=[
            "bin_index", "start_time_us", "end_time_us",
            "waiting_time_us", "running_time_us", "waiting_pct", "running_pct"
        ])

    min_start = int(merged[0, 0])  # will be 0 after normalization
    max_end = int(merged[-1, 1])
    total_span = max_end - min_start
    if total_span <= 0:
        return pd.DataFrame(columns=[
            "bin_index", "start_time_us", "end_time_us",
            "waiting_time_us", "running_time_us", "waiting_pct", "running_pct"
        ])

    num_bins = math.ceil(total_span / bin_size_us)
    waiting = np.zeros(num_bins, dtype=np.int64)

    # Distribute waiting intervals into bins
    for (s, e) in merged:
        s0 = max(s, min_start)
        e0 = min(e, max_end)
        if e0 <= s0:
            continue
        first_bin = (s0 - min_start) // bin_size_us
        last_bin = (e0 - 1 - min_start) // bin_size_us  # inclusive
        for b in range(first_bin, last_bin + 1):
            bs = min_start + b * bin_size_us
            be = bs + bin_size_us
            ov = max(0, min(e0, be) - max(s0, bs))
            if ov:
                waiting[b] += ov

    starts = min_start + np.arange(num_bins, dtype=np.int64) * bin_size_us
    ends = starts + bin_size_us
    # Clip the last bin to the exact trace end
    ends[-1] = max_end

    spans = ends - starts
    running = spans - waiting
    waiting_pct = (waiting / spans) * 100.0
    running_pct = 100.0 - waiting_pct

    return pd.DataFrame({
        "bin_index": np.arange(num_bins, dtype=np.int64),
        "start_time_us": starts,
        "end_time_us": ends,
        "waiting_time_us": waiting,
        "running_time_us": running,
        "waiting_pct": waiting_pct,
        "running_pct": running_pct,
    })


# -------------------------------------------------
# Plotting
# -------------------------------------------------
def plot_cpu_overlay(per_bin_results: dict,
                     out_png: str,
                     title: str):
    """
    Draw one figure with running% vs time for all bin sizes.
    """
    plt.figure(figsize=(12, 6))

    for bin_us, df in sorted(per_bin_results.items()):
        time_sec = df["start_time_us"] / 1_000_000.0
        cpu_pct = df["running_pct"]
        plt.plot(time_sec, cpu_pct, label=f"{bin_us} µs")

    plt.xlabel("Time (seconds)")
    plt.ylabel("CPU running (%)")
    plt.title(title)
    plt.legend(title="Time slice")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()


# -------------------------------------------------
# CLI helpers
# -------------------------------------------------
def expand_inputs(inputs: Iterable[str]) -> List[str]:
    files = []
    for item in inputs:
        files.extend(glob.glob(item))
    # Dedup while preserving order
    return list(dict.fromkeys(files))


def main():
    ap = argparse.ArgumentParser(
        description="Generate wait/run CSVs and CPU% overlay charts per input file, titles from bash Test names."
    )
    ap.add_argument("--inputs", nargs="+", required=True,
                    help="Input CSV path(s) or globs (e.g. './out/cpu_intensive_*.csv').")
    ap.add_argument("--out-root", default="./out_per_file",
                    help="Root output directory (one subdir per input).")
    ap.add_argument("--bin-sizes-us", nargs="+", type=int, required=True,
                    help="Bin sizes in microseconds (e.g. 500 1000 1500 2000 5000).")
    ap.add_argument("--relative-time-col", default="relative_time",
                    help="Column for syscall start time (seconds).")
    ap.add_argument("--duration-us-col", default="duration_us",
                    help="Column for duration (microseconds).")
    ap.add_argument("--title-map-sh", default=None,
                    help="Path to bash script that prints lines like '=== Test N: Name ==='. (READ-ONLY)")
    ap.add_argument("--stem-number-regex", default=r'_(\d+)$',
                    help="Regex (with one capture group) to extract the test number from the filename stem."
                         " Default matches trailing '_NNN'.")
    args = ap.parse_args()

    files = expand_inputs(args.inputs)
    if not files:
        raise SystemExit("No input files matched the given --inputs patterns.")

    bin_sizes = sorted({b for b in args.bin_sizes_us if b > 0})
    if not bin_sizes:
        raise SystemExit("Provide at least one positive --bin-sizes-us value.")

    title_map: Dict[int, str] = {}
    if args.title_map_sh:
        title_map = parse_test_labels_from_bash(args.title_map_sh)

    os.makedirs(args.out_root, exist_ok=True)

    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        out_dir = os.path.join(args.out_root, stem)
        os.makedirs(out_dir, exist_ok=True)

        # Determine a human-friendly title for this file
        test_idx = extract_test_number_from_stem(stem, args.stem_number_regex)
        if test_idx is not None and test_idx in title_map:
            title = f"{title_map[test_idx]} (Test {test_idx})"
        elif test_idx is not None:
            title = f"Test {test_idx} ({stem})"
        else:
            title = stem  # fallback if no number found

        print(f"[INFO] Processing {path}  -> title: {title}")

        # Load + merge once per file
        starts, ends = load_intervals(
            path,
            relative_time_col=args.relative_time_col,
            duration_us_col=args.duration_us_col,
        )
        merged = merge_intervals(starts, ends)

        # Produce outputs for all bin sizes
        per_bin_results = {}
        for B in bin_sizes:
            df_out = bin_wait_run(merged, B)
            out_csv = os.path.join(out_dir, f"{stem}_waitrun_{B}us.csv")
            df_out.to_csv(out_csv, index=False)
            per_bin_results[B] = df_out

        # Plot overlay figure with mapped title
        out_png = os.path.join(out_dir, f"{stem}_cpu_pct_overlay.png")
        plot_cpu_overlay(
            per_bin_results,
            out_png=out_png,
            title=f"CPU Utilization vs Time — {title}"
        )

        print(f"[OK] {path} -> {out_dir}/ ({len(bin_sizes)} CSVs + 1 PNG)")


if __name__ == "__main__":
    main()