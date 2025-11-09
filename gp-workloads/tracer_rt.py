#!/usr/bin/env python3
from bcc import BPF
import argparse
import sys
import signal
import os

# Command line arguments
parser = argparse.ArgumentParser(description='Trace system calls from realtime processes')
parser.add_argument('-o', '--output', help='Output file (default: stdout)')
args = parser.parse_args()

def get_next_filename(base_filename):
    """
    Generates an incremented filename if the base_filename already exists.
    Example: "report.txt" -> "report_1.txt", "report_2.txt", etc.
    """
    name, ext = os.path.splitext(base_filename)
    counter = 0
    new_filename = base_filename

    while os.path.exists(new_filename):
        counter += 1
        new_filename = f"{name}_{counter}{ext}"
    return new_filename

def get_syscall_name(nr):
    return syscall_names.get(nr, f"syscall_{nr}")

def handle_interrupt(sig, frame):
    global output_file

    # Setup output file
    if args.output:
        output_file.close()
        output_file = open(get_next_filename(args.output), 'w')

    print_header()

def print_header():
    print("timestamp,relative_time,pid,comm,uid,syscall,duration_us", file=output_file)
    output_file.flush()

# Setup output
if args.output:
    output_file = open(get_next_filename(args.output), 'w')
else:
    output_file = sys.stdout

# eBPF program
bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct data_t {
    u32 pid;
    u32 uid;
    u64 ts;
    u64 duration_ns;
    int syscall_nr;
    char comm[TASK_COMM_LEN];
};

BPF_PERF_OUTPUT(events);
BPF_HASH(start, u64, u64);

TRACEPOINT_PROBE(raw_syscalls, sys_enter) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;

    // Get current task's scheduling policy
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    int policy = task->policy;

    // Filter for realtime processes only
    // SCHED_FIFO = 1, SCHED_RR = 2
    if (policy != 1 && policy != 2) {
        return 0;
    }

    // Record start time for this syscall
    u64 ts = bpf_ktime_get_ns();
    start.update(&pid_tgid, &ts);

    return 0;
}

TRACEPOINT_PROBE(raw_syscalls, sys_exit) {
    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;

    // Get current task's scheduling policy
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    int policy = task->policy;

    // Filter for realtime processes only
    if (policy != 1 && policy != 2) {
        return 0;
    }

    // Get start time
    u64 *tsp = start.lookup(&pid_tgid);
    if (tsp == 0) {
        return 0;  // Missed entry
    }

    u64 ts_end = bpf_ktime_get_ns();
    u64 duration = ts_end - *tsp;

    struct data_t data = {};
    data.pid = pid;
    data.uid = bpf_get_current_uid_gid();
    data.ts = *tsp;
    data.duration_ns = duration;
    data.syscall_nr = args->id;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));

    events.perf_submit(args, &data, sizeof(data));

    // Cleanup
    start.delete(&pid_tgid);

    return 0;
}
"""

# Syscall name mapping (common syscalls)
syscall_names = {
    0: "read", 1: "write", 2: "open", 3: "close", 4: "stat",
    5: "fstat", 6: "lstat", 7: "poll", 8: "lseek", 9: "mmap",
    10: "mprotect", 11: "munmap", 12: "brk", 13: "rt_sigaction",
    14: "rt_sigprocmask", 15: "rt_sigreturn", 16: "ioctl", 17: "pread64",
    18: "pwrite64", 19: "readv", 20: "writev", 21: "access", 22: "pipe",
    23: "select", 24: "sched_yield", 25: "mremap", 26: "msync",
    32: "dup", 33: "dup2", 39: "getpid", 41: "socket", 42: "connect",
    43: "accept", 44: "sendto", 45: "recvfrom", 49: "bind", 50: "listen",
    56: "clone", 57: "fork", 58: "vfork", 59: "execve", 60: "exit",
    61: "wait4", 62: "kill", 63: "uname", 72: "fcntl", 78: "getdents",
    79: "getcwd", 80: "chdir", 82: "rename", 83: "mkdir", 84: "rmdir",
    85: "creat", 86: "link", 87: "unlink", 89: "readlink", 90: "chmod",
    257: "openat", 262: "newfstatat", 263: "unlinkat", 265: "linkat",
    266: "symlinkat", 267: "readlinkat", 268: "fchmodat", 269: "faccessat",
    292: "dup3", 293: "pipe2", 316: "renameat2", 322: "execveat"
}

# Tracking for relative timestamps
start_time = None

# Process event
def print_event(cpu, data, size):
    global start_time
    event = b["events"].event(data)

    if start_time is None:
        start_time = event.ts

    syscall_name = get_syscall_name(event.syscall_nr)
    comm = event.comm.decode('utf-8', 'replace')

    # Convert nanoseconds timestamp to seconds with nanosecond precision
    ts_sec = event.ts / 1_000_000_000
    relative_ts = (event.ts - start_time) / 1_000_000_000
    duration_us = event.duration_ns / 1000.0  # Convert to microseconds

    # CSV format: timestamp,relative_time,pid,comm,uid,syscall,duration_us
    print(f"{ts_sec:.9f},{relative_ts:.9f},{event.pid},{comm},{event.uid},{syscall_name},{duration_us:.3f}",
          file=output_file)
    output_file.flush()

if __name__ == "__main__":
    # Load BPF program
    b = BPF(text=bpf_text)

    # Attach to perf output
    b["events"].open_perf_buffer(print_event)

    signal.signal(signal.SIGUSR1, handle_interrupt)

    msg = "Tracing system calls from REALTIME processes only (SCHED_FIFO/SCHED_RR)..."
    if args.output:
        msg += f"\nOutput file: {args.output}"

    print(msg, file=sys.stderr)

    # CSV header
    print_header()

    # Signal that we're ready
    print("READY", file=sys.stderr)
    sys.stderr.flush()

    # Read events
    try:
        while True:
            b.perf_buffer_poll()
    except KeyboardInterrupt:
        print("\n\nDetaching...", file=sys.stderr)

        if args.output:
            output_file.close()
