#!/usr/bin/env python3
"""Keep an Oracle Always Free instance above the idle-reclamation thresholds.

Oracle marks an Always Free instance idle when, over 7 days, the 95th percentile
CPU utilization stays below 20% (plus network/memory checks). This keeps every
vCPU busy for KEEPALIVE_CPU_PERCENT of each short period. Run it under
SCHED_IDLE (see scripts/systemd/goodjian-keepalive.service) so real traffic
always preempts it.

Environment:
  KEEPALIVE_CPU_PERCENT  target utilization per vCPU, 1-90 (default 25)
  KEEPALIVE_MEM_MB       memory to hold and touch, 0 disables (default 0)
"""

import multiprocessing
import os
import signal
import sys
import time

PERIOD_SECONDS = 0.1
PAGE_SIZE = 4096


def _read_int(name, default, low, high):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        sys.exit(f"{name} must be an integer, got {raw!r}")
    return max(low, min(high, value))


def burn(fraction):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    busy = PERIOD_SECONDS * fraction
    x = 0
    while True:
        start = time.perf_counter()
        while time.perf_counter() - start < busy:
            x = (x * 1103515245 + 12345) & 0x7FFFFFFF
        remaining = PERIOD_SECONDS - (time.perf_counter() - start)
        if remaining > 0:
            time.sleep(remaining)


def hold_memory(megabytes):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    block = bytearray(megabytes * 1024 * 1024)
    # Touch every page periodically so the kernel keeps it resident.
    while True:
        for i in range(0, len(block), PAGE_SIZE):
            block[i] = (block[i] + 1) & 0xFF
        time.sleep(60)


def main():
    cpu_percent = _read_int("KEEPALIVE_CPU_PERCENT", 25, 1, 90)
    mem_mb = _read_int("KEEPALIVE_MEM_MB", 0, 0, 1024 * 16)
    workers = os.cpu_count() or 1

    procs = [
        multiprocessing.Process(target=burn, args=(cpu_percent / 100,), daemon=True)
        for _ in range(workers)
    ]
    if mem_mb:
        procs.append(multiprocessing.Process(target=hold_memory, args=(mem_mb,), daemon=True))

    def stop(signum, _frame):
        for p in procs:
            p.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    for p in procs:
        p.start()
    print(
        f"keepalive: {workers} vCPU x {cpu_percent}% CPU, memory hold {mem_mb} MB",
        flush=True,
    )

    while True:
        for p in procs:
            if not p.is_alive():
                sys.exit(f"keepalive: worker {p.pid} exited with {p.exitcode}")
        time.sleep(30)


if __name__ == "__main__":
    main()
