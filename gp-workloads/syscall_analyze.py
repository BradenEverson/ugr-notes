#!/usr/bin/env python3
"""
Analyze syscall trace CSV to calculate aggregate time spent in each syscall and userspace
Produces a single row per input CSV file with one column per syscall
"""
import csv
import sys
import glob
import os
from collections import defaultdict
import argparse


def analyze_syscalls(csv_file):
    """Parse CSV and calculate aggregate statistics across all processes"""

    # Track all unique syscalls we encounter
    all_syscalls = set()

    # Aggregate statistics across ALL processes
    aggregate_stats = {
        'total_syscall_time_us': 0.0,
        'total_userspace_time_us': 0.0,
        'syscall_count': 0,
        'syscall_times': defaultdict(float),  # syscall name -> total time
        'first_ts': None,
        'last_ts': None,
    }

    # Track per-process to calculate userspace time correctly
    process_tracking = defaultdict(lambda: {
        'last_syscall_end': None,
        'first_ts': None,
        'last_ts': None
    })

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            timestamp = float(row['timestamp'])
            pid = int(row['pid'])
            comm = row['comm']
            syscall = row['syscall']
            duration_us = float(row['duration_us'])

            all_syscalls.add(syscall)

            # Calculate syscall end time
            syscall_end = timestamp + (duration_us / 1_000_000.0)

            # Update aggregate syscall time
            aggregate_stats['total_syscall_time_us'] += duration_us
            aggregate_stats['syscall_count'] += 1
            aggregate_stats['syscall_times'][syscall] += duration_us

            # Track overall time range
            if aggregate_stats['first_ts'] is None or timestamp < aggregate_stats['first_ts']:
                aggregate_stats['first_ts'] = timestamp
            if aggregate_stats['last_ts'] is None or syscall_end > aggregate_stats['last_ts']:
                aggregate_stats['last_ts'] = syscall_end

            # Calculate userspace time per process/pid combination
            proc_key = f"{comm}_{pid}"
            proc = process_tracking[proc_key]

            if proc['last_syscall_end'] is not None:
                userspace_time = (timestamp - proc['last_syscall_end']) * 1_000_000.0
                if userspace_time > 0:
                    aggregate_stats['total_userspace_time_us'] += userspace_time

            proc['last_syscall_end'] = syscall_end

    return aggregate_stats, sorted(all_syscalls)


def export_single_row_csv(aggregate_stats, all_syscalls, csv_filename, output_file, append=False):
    """Export single-row CSV with aggregate times across all processes"""

    import os

    mode = 'a' if append else 'w'
    file_exists = False

    if append:
        try:
            with open(output_file, 'r') as f:
                file_exists = True
        except FileNotFoundError:
            file_exists = False

    with open(output_file, mode, newline='') as f:
        writer = csv.writer(f)

        # Write header only if creating new file
        if not file_exists:
            header = ['trace_file'] + [f"{sc}_ms" for sc in all_syscalls] + ['userspace_ms', 'total_ms', 'wall_time_s']
            writer.writerow(header)

        total_syscall_ms = aggregate_stats['total_syscall_time_us'] / 1000.0
        total_userspace_ms = aggregate_stats['total_userspace_time_us'] / 1000.0
        total_ms = total_syscall_ms + total_userspace_ms
        wall_time = aggregate_stats['last_ts'] - aggregate_stats['first_ts'] if aggregate_stats['first_ts'] else 0

        # Extract just the filename without path
        filename_only = os.path.basename(csv_filename)
        row = [filename_only]

        # Add time for each syscall (0 if not used)
        for syscall in all_syscalls:
            time_ms = aggregate_stats['syscall_times'].get(syscall, 0.0) / 1000.0
            row.append(f"{time_ms:.3f}")

        # Add userspace, total, and wall time
        row.extend([
            f"{total_userspace_ms:.3f}",
            f"{total_ms:.3f}",
            f"{wall_time:.6f}"
        ])

        writer.writerow(row)

    action = "Appended to" if append else "Created"
    print(f"{action}: {output_file}")
    print(f"Row for: {os.path.basename(csv_filename)}")
    print(f"  Syscalls: {len(all_syscalls)}, Total time: {total_ms:.3f} ms, Wall time: {wall_time:.6f} s")


def print_summary(aggregate_stats, csv_filename):
    """Print brief summary to console"""

    print("=" * 80)
    print(f"SYSCALL TIME ANALYSIS: {csv_filename}")
    print("=" * 80)

    total_syscall_ms = aggregate_stats['total_syscall_time_us'] / 1000.0
    total_userspace_ms = aggregate_stats['total_userspace_time_us'] / 1000.0
    total_ms = total_syscall_ms + total_userspace_ms
    wall_time = aggregate_stats['last_ts'] - aggregate_stats['first_ts'] if aggregate_stats['first_ts'] else 0

    print(f"\nTotal syscalls:      {aggregate_stats['syscall_count']}")
    print(f"Syscall time:        {total_syscall_ms:.3f} ms")
    print(f"Userspace time:      {total_userspace_ms:.3f} ms")
    print(f"Total CPU time:      {total_ms:.3f} ms")
    print(f"Wall time:           {wall_time:.6f} s")

    # Show top 10 syscalls by time
    print(f"\nTop syscalls by time:")
    sorted_syscalls = sorted(aggregate_stats['syscall_times'].items(),
                             key=lambda x: x[1],
                             reverse=True)

    for syscall, time_us in sorted_syscalls[:10]:
        time_ms = time_us / 1000.0
        pct = (time_us / aggregate_stats['total_syscall_time_us'] * 100) if aggregate_stats[
                                                                                'total_syscall_time_us'] > 0 else 0
        print(f"  {syscall:<20} {time_ms:>10.3f} ms ({pct:>5.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Analyze syscall trace CSV - produces one aggregate row per input file',
        epilog='Examples:\n'
               '  python3 analyze_syscall_times.py test1.csv test2.csv -o results.csv\n'
               '  python3 analyze_syscall_times.py "trace_*.csv" -o results.csv\n'
               '  python3 analyze_syscall_times.py "tests/**/*.csv" -o results.csv',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('csv_files', nargs='+', help='Input CSV file(s) or glob pattern(s) from syscall tracer')
    parser.add_argument('-o', '--output', required=True, help='Output CSV file')
    parser.add_argument('--quiet', action='store_true', help='Suppress console output')

    args = parser.parse_args()

    try:
        # Expand glob patterns
        all_files = []
        for pattern in args.csv_files:
            # Try glob expansion
            expanded = glob.glob(pattern, recursive=True)
            if expanded:
                all_files.extend(expanded)
            else:
                # If glob didn't match anything, treat as literal filename
                all_files.append(pattern)

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in all_files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        if not unique_files:
            print("Error: No files found matching the specified patterns", file=sys.stderr)
            sys.exit(1)

        if not args.quiet:
            print(f"Found {len(unique_files)} file(s) to process")
            print()

        # Process first file (create new output file)
        first_file = unique_files[0]
        aggregate_stats, all_syscalls = analyze_syscalls(first_file)

        if not args.quiet:
            print_summary(aggregate_stats, first_file)
            print()

        export_single_row_csv(aggregate_stats, all_syscalls, first_file,
                              args.output, append=False)

        # Process remaining files (append to output file)
        for csv_file in unique_files[1:]:
            aggregate_stats, all_syscalls = analyze_syscalls(csv_file)

            if not args.quiet:
                print_summary(aggregate_stats, csv_file)
                print()

            export_single_row_csv(aggregate_stats, all_syscalls, csv_file,
                                  args.output, append=True)

        if not args.quiet:
            print("=" * 80)
            print(f"Processed {len(unique_files)} file(s)")
            print(f"Output written to: {args.output}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)