#!/usr/bin/env python3
"""
Analyze syscall trace CSV to calculate time spent in each syscall and userspace
Produces a wide-format CSV with one column per syscall
"""
import csv
import sys
from collections import defaultdict
import argparse


def analyze_syscalls(csv_file):
    """Parse CSV and calculate statistics including userspace time and per-syscall breakdown"""

    # Track all unique syscalls we encounter
    all_syscalls = set()

    # Statistics by process name
    process_stats = defaultdict(lambda: {
        'total_syscall_time_us': 0.0,
        'total_userspace_time_us': 0.0,
        'syscall_count': 0,
        'syscall_times': defaultdict(float),  # syscall name -> total time
        'first_ts': None,
        'last_ts': None,
        'last_syscall_end': None
    })

    # Statistics by PID
    pid_stats = defaultdict(lambda: {
        'comm': '',
        'total_syscall_time_us': 0.0,
        'total_userspace_time_us': 0.0,
        'syscall_count': 0,
        'syscall_times': defaultdict(float),
        'first_ts': None,
        'last_ts': None,
        'last_syscall_end': None
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

            # Update process stats
            proc = process_stats[comm]
            proc['total_syscall_time_us'] += duration_us
            proc['syscall_count'] += 1
            proc['syscall_times'][syscall] += duration_us

            # Calculate userspace time
            if proc['last_syscall_end'] is not None:
                userspace_time = (timestamp - proc['last_syscall_end']) * 1_000_000.0
                if userspace_time > 0:
                    proc['total_userspace_time_us'] += userspace_time

            if proc['first_ts'] is None:
                proc['first_ts'] = timestamp
            proc['last_ts'] = syscall_end
            proc['last_syscall_end'] = syscall_end

            # Update PID stats
            pid_info = pid_stats[pid]
            pid_info['comm'] = comm
            pid_info['total_syscall_time_us'] += duration_us
            pid_info['syscall_count'] += 1
            pid_info['syscall_times'][syscall] += duration_us

            # Calculate userspace time for this PID
            if pid_info['last_syscall_end'] is not None:
                userspace_time = (timestamp - pid_info['last_syscall_end']) * 1_000_000.0
                if userspace_time > 0:
                    pid_info['total_userspace_time_us'] += userspace_time

            if pid_info['first_ts'] is None:
                pid_info['first_ts'] = timestamp
            pid_info['last_ts'] = syscall_end
            pid_info['last_syscall_end'] = syscall_end

    return process_stats, pid_stats, sorted(all_syscalls)


def export_wide_format_csv(process_stats, pid_stats, all_syscalls, output_file, by_pid=False):
    """Export wide-format CSV with one column per syscall (times in milliseconds)"""

    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)

        if by_pid:
            # Header: pid, process, [syscall columns], userspace_time_ms, total_time_ms, wall_time_s
            header = ['pid', 'process'] + [f"{sc}_ms" for sc in all_syscalls] + ['userspace_ms', 'total_ms',
                                                                                 'wall_time_s']
            writer.writerow(header)

            sorted_pids = sorted(pid_stats.items(),
                                 key=lambda x: x[1]['total_syscall_time_us'] + x[1]['total_userspace_time_us'],
                                 reverse=True)

            for pid, stats in sorted_pids:
                total_syscall_ms = stats['total_syscall_time_us'] / 1000.0
                total_userspace_ms = stats['total_userspace_time_us'] / 1000.0
                total_ms = total_syscall_ms + total_userspace_ms
                wall_time = stats['last_ts'] - stats['first_ts'] if stats['first_ts'] else 0

                row = [pid, stats['comm']]

                # Add time for each syscall (0 if not used)
                for syscall in all_syscalls:
                    time_ms = stats['syscall_times'].get(syscall, 0.0) / 1000.0
                    row.append(f"{time_ms:.3f}")

                # Add userspace, total, and wall time
                row.extend([
                    f"{total_userspace_ms:.3f}",
                    f"{total_ms:.3f}",
                    f"{wall_time:.6f}"
                ])

                writer.writerow(row)
        else:
            # Header: process, [syscall columns], userspace_time_ms, total_time_ms, wall_time_s
            header = ['process'] + [f"{sc}_ms" for sc in all_syscalls] + ['userspace_ms', 'total_ms', 'wall_time_s']
            writer.writerow(header)

            sorted_procs = sorted(process_stats.items(),
                                  key=lambda x: x[1]['total_syscall_time_us'] + x[1]['total_userspace_time_us'],
                                  reverse=True)

            for comm, stats in sorted_procs:
                total_syscall_ms = stats['total_syscall_time_us'] / 1000.0
                total_userspace_ms = stats['total_userspace_time_us'] / 1000.0
                total_ms = total_syscall_ms + total_userspace_ms
                wall_time = stats['last_ts'] - stats['first_ts'] if stats['first_ts'] else 0

                row = [comm]

                # Add time for each syscall (0 if not used)
                for syscall in all_syscalls:
                    time_ms = stats['syscall_times'].get(syscall, 0.0) / 1000.0
                    row.append(f"{time_ms:.3f}")

                # Add userspace, total, and wall time
                row.extend([
                    f"{total_userspace_ms:.3f}",
                    f"{total_ms:.3f}",
                    f"{wall_time:.6f}"
                ])

                writer.writerow(row)

    print(f"Wide-format breakdown exported to: {output_file}")
    print(f"Columns: process, {len(all_syscalls)} syscalls, userspace_ms, total_ms, wall_time_s")


def print_summary(process_stats, top_n=10):
    """Print brief summary to console"""

    print("=" * 80)
    print("SYSCALL TIME ANALYSIS SUMMARY")
    print("=" * 80)

    print(f"\n{'PROCESS':<20} {'USERSPACE (ms)':<15} {'TOTAL (ms)':<15} {'WALL (s)':<12}")
    print("-" * 80)

    sorted_procs = sorted(process_stats.items(),
                          key=lambda x: x[1]['total_syscall_time_us'] + x[1]['total_userspace_time_us'],
                          reverse=True)

    for comm, stats in sorted_procs[:top_n]:
        total_syscall_ms = stats['total_syscall_time_us'] / 1000.0
        userspace_ms = stats['total_userspace_time_us'] / 1000.0
        total_ms = total_syscall_ms + userspace_ms
        wall_time = stats['last_ts'] - stats['first_ts'] if stats['first_ts'] else 0

        print(f"{comm:<20} {userspace_ms:<15.3f} {total_ms:<15.3f} {wall_time:<12.6f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Analyze syscall trace CSV files - produces wide-format output')
    parser.add_argument('csv_file', help='Input CSV file from syscall tracer')
    parser.add_argument('-o', '--output', required=True, help='Output CSV file with wide-format breakdown')
    parser.add_argument('--by-pid', action='store_true', help='Group by PID instead of process name')
    parser.add_argument('--top', type=int, default=10,
                        help='Number of top processes to show in console output (default: 10)')
    parser.add_argument('--quiet', action='store_true', help='Suppress console output')

    args = parser.parse_args()

    try:
        process_stats, pid_stats, all_syscalls = analyze_syscalls(args.csv_file)

        if not args.quiet:
            print_summary(process_stats, top_n=args.top)
            print()

        export_wide_format_csv(process_stats, pid_stats, all_syscalls, args.output, by_pid=args.by_pid)

    except FileNotFoundError:
        print(f"Error: File '{args.csv_file}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)