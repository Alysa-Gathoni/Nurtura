"""Sample a process tree's memory every second for SECONDS (#224).

Usage: python peak_memory.py PID SECONDS OUT.json
Writes the peak and the mean resident memory (MB) of PID and its children,
and the mean CPU use (% of one core), to OUT.json.
"""

import json
import sys
import time

import psutil


def main():
    pid, seconds, out = int(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
    root = psutil.Process(pid)
    known = {}  # pid -> Process, kept so cpu_percent measures since last call

    def tree():
        procs = [root, *root.children(recursive=True)]
        for p in procs:
            if p.pid not in known:
                known[p.pid] = p
                p.cpu_percent(None)  # first call only starts the clock
        return [known[p.pid] for p in procs]

    tree()
    rss, cpu = [], []
    end = time.time() + seconds
    while time.time() < end:
        time.sleep(1)
        try:
            procs = tree()
            rss.append(sum(p.memory_info().rss for p in procs) / 2**20)
            cpu.append(sum(p.cpu_percent(None) for p in procs))
        except psutil.NoSuchProcess:
            break
    result = {
        "peak_rss_mb": round(max(rss), 1) if rss else None,
        "mean_rss_mb": round(sum(rss) / len(rss), 1) if rss else None,
        "mean_cpu_percent_one_core": round(sum(cpu) / len(cpu), 1) if cpu else None,
        "samples": len(rss),
        "logical_cores": psutil.cpu_count(),
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f)
    print(result)


if __name__ == "__main__":
    main()
