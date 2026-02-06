#!/usr/bin/env python3
"""
wait_run_binner_multi.py

Aggregate per-timeslice 'waiting' (in syscalls) vs. 'running' (on-CPU) from
CSV traces that contain:
  - relative_time (seconds): start of the syscall
  - duration_us (microseconds): syscall duration

Algorithm (per file):
  1) Convert each row to a [start_us, end_us) interval:
        start_us = round(relative_time * 1e6)
        end_us   = start_us + ceil(duration_us)
  2) Merge overlapping/adjacent waiting intervals (avoid double-counting).
  3) For each requested bin size (bin_size_us), compute per-bin:
        waiting_time_us = sum of overlaps with waiting intervals
        running_time_us = bin_span_us - waiting_time_us
        waiting_pct, running_pct
  4) Write one CSV per bin size into an output subdirectory dedicated to the input file.

Example:
  python wait_run_binner_multi.py \
      --inputs './traces/*.csv' \
      --bin-sizes-us 500 1000 1500 2000 5000 \
      --out-root ./out_per_file

This will produce, for each input F, a directory:
  ./out_per_file/<stem_of_F>/
containing files like:
  <stem_of_F>_waitrun_500us.csv
  <stem_of_F>_waitrun_1000us.csv
  ...
"""

from __future__ import annotations
import argparse
import glob
import math
import os
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd


# -----------------------------
# Core loading / processing
# -----------------------------
def load_intervals(csv_path: str,
                   relative_time_col: str = "relative_time",
                   duration_us_col: str = "duration_us"
                   ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load a CSV and convert rows into [start_us, end_us) intervals.
    Expected columns:
      - relative_time (seconds)
      - duration_us (microseconds)

    Returns:
        start_us (int64 array), end_us (int64 array)
    """
    df = pd.read_csv(csv_path)
    # Normalize column names (case-insensitive match)
    df.columns = [c.strip().lower().replace("\\", "") for c in df.columns]
    rel_col = next((c for c in df.columns if c == relative_time_col.lower()), None)
    dur_col = next((c for c in df.columns if c == duration_us_col.lower()), None)
    if rel_col is None or dur_col is None:
        raise ValueError(
            f"{csv_path}: expected columns '{relative_time_col}' and '{duration_us_col}'. "
            f"Found: {list(df.columns)}"
        )

    # Coerce numeric and drop bad rows
    df[rel_col] = pd.to_numeric(df[rel_col], errors="coerce")
    df[dur_col] = pd.to_numeric(df[dur_col], errors="coerce")
    df = df.dropna(subset=[rel_col, dur_col]).copy()

    # Convert to integer microseconds
    start_us = np.rint(df[rel_col].values * 1_000_000.0).astype(np.int64)
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

    Returns:
        merged: shape (N,2) int64 array
    """
    merged: List[List[int]] = []
    for s, e in zip(starts, ends):
        if not merged:
            merged.append([int(s), int(e)])
        else:
            if s <= merged[-1][1]:
                if e > merged[-1][1]:
                    merged[-1][1] = int(e)
            else:
                merged.append([int(s), int(e)])
    return np.array(merged, dtype=np.int64) if merged else np.empty((0, 2), dtype=np.int64)


def bin_wait_run(merged: np.ndarray, bin_size_us: int) -> pd.DataFrame:
    """
    Aggregate waiting vs. running per fixed-size time slice.

    Args:
        merged: (N,2) array of merged waiting intervals [start_us, end_us)
        bin_size_us: bin width in microseconds (e.g., 500, 1000, 1500, 2000, 5000)

    Returns:
        DataFrame with:
          bin_index,start_time_us,end_time_us,waiting_time_us,running_time_us,waiting_pct,running_pct
    """
    if merged.size == 0:
        return pd.DataFrame(columns=[
            "bin_index", "start_time_us", "end_time_us",
            "waiting_time_us", "running_time_us", "waiting_pct", "running_pct"
        ])

    min_start = int(merged[0, 0])
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
            bin_start = min_start + b * bin_size_us
            bin_end = bin_start + bin_size_us
            ov = max(0, min(e0, bin_end) - max(s0, bin_start))
            if ov:
                waiting[b] += ov

    starts = min_start + np.arange(num_bins, dtype=np.int64) * bin_size_us
    ends = starts + bin_size_us
    # Clip the last bin to the exact trace end so totals match perfectly
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


def process_file_for_bins(input_csv: str,
                          out_dir_for_file: str,
                          bin_sizes_us: List[int],
                          relative_time_col: str = "relative_time",
                          duration_us_col: str = "duration_us") -> List[str]:
    """
    Process one input CSV once (load+merge intervals), then emit outputs
    for all bin sizes in bin_sizes_us.

    Returns:
        List of generated file paths.
    """
    starts, ends = load_intervals(
        input_csv,
        relative_time_col=relative_time_col,
        duration_us_col=duration_us_col,
    )
    merged = merge_intervals(starts, ends)

    os.makedirs(out_dir_for_file, exist_ok=True)
    stem = os.path.splitext(os.path.basename(input_csv))[0]
    outputs = []

    for B in bin_sizes_us:
        out_df = bin_wait_run(merged, B)
        out_name = f"{stem}_waitrun_{B}us.csv"
        out_path = os.path.join(out_dir_for_file, out_name)
        out_df.to_csv(out_path, index=False)
        outputs.append(out_path)

    return outputs


# -----------------------------
# CLI helpers
# -----------------------------
def expand_inputs(inputs: Iterable[str]) -> List[str]:
    """Allow plain paths and globs in --inputs."""
    files: List[str] = []
    for item in inputs:
        files.extend(glob.glob(item))
    # Deduplicate while preserving order
    return list(dict.fromkeys(files))


def main():
    ap = argparse.ArgumentParser(
        description="Bin waiting vs running per time slice from syscall CSVs (multiple bin sizes, multiple files)."
    )
    ap.add_argument("--inputs", nargs="+", required=True,
                    help="Input CSV path(s) or globs (e.g., './traces/*.csv').")
    ap.add_argument("--out-root", default="./out_per_file",
                    help="Root directory to write outputs. A subdir per input file will be created here.")
    ap.add_argument("--bin-sizes-us", nargs="+", type=int, required=True,
                    help="One or more bin sizes in microseconds, e.g. 500 1000 1500 2000 5000.")
    ap.add_argument("--relative-time-col", default="relative_time",
                    help="Column name for syscall start time in seconds.")
    ap.add_argument("--duration-us-col", default="duration_us",
                    help="Column name for syscall duration in microseconds.")
    args = ap.parse_args()

    files = expand_inputs(args.inputs)
    if not files:
        raise SystemExit("No input files matched the given --inputs patterns.")

    # Sort/bin sizes, dedupe, and sanity-check
    bin_sizes = sorted(set([b for b in args.bin_sizes_us if b > 0]))
    if not bin_sizes:
        raise SystemExit("Provide at least one positive --bin-sizes-us value.")

    print(f"[INFO] Inputs: {len(files)} file(s)")
    print(f"[INFO] Bin sizes (µs): {bin_sizes}")
    print(f"[INFO] Output root: {args.out_root}")

    os.makedirs(args.out_root, exist_ok=True)
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        out_dir_for_file = os.path.join(args.out_root, stem)
        outputs = process_file_for_bins(
            input_csv=path,
            out_dir_for_file=out_dir_for_file,
            bin_sizes_us=bin_sizes,
            relative_time_col=args.relative_time_col,
            duration_us_col=args.duration_us_col,
        )
        # Quick summary
        print(f"[OK] {path} -> {out_dir_for_file}/ "
              f"wrote {len(outputs)} file(s):")
        for p in outputs:
            print(f"     - {os.path.basename(p)}")


if __name__ == "__main__":
    main()