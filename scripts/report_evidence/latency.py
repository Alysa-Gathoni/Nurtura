"""1g latency repeat: 20 held-out children x 5 repeats, in process.

Start-up is measured from this script's start to the model being loaded and
one query encoded. Each request is generation.generate() (rule engine,
encode, score every eligible activity, store a batch) inside a transaction
that is rolled back. Peak memory is the process's peak working set
(Windows GetProcessMemoryInfo). No HTTP: see docs/performance_recommendations.md
for the end-to-end figures.
"""

import time

T0 = time.perf_counter()

import ctypes  # noqa: E402
import statistics  # noqa: E402
from ctypes import wintypes  # noqa: E402

from _common import (
    django_setup,
    rolled_back,
    table,
    write_csv,
    write_json,
    write_md,
)  # noqa: E402

COMMAND = "backend\\venv\\Scripts\\python.exe scripts\\report_evidence\\latency.py"
REPEATS = 5


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def memory_mb():
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    kernel32, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb
    ):
        raise OSError(ctypes.get_last_error())
    return counters.PeakWorkingSetSize / 1e6, counters.WorkingSetSize / 1e6


def pct(values, p):
    values = sorted(values)
    k = (len(values) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def main():
    django_setup()
    from django.contrib.auth import get_user_model

    from recommendations import embeddings, generation, heldout

    embeddings.get_encoder().encode(["warm-up query"])
    startup = time.perf_counter() - T0
    after_load, _ = memory_mb()

    rows = []
    with rolled_back():
        caregiver = get_user_model().objects.create_user(
            username="latency-evidence@nurtura.invalid"
        )
        children = [
            heldout.create_child(c, caregiver) for c in heldout.HELDOUT_CHILDREN
        ]
        for repeat in range(1, REPEATS + 1):
            for child in children:
                t = time.perf_counter()
                result = generation.generate(child.pk, caregiver)
                ms = (time.perf_counter() - t) * 1000
                rows.append(
                    {
                        "repeat": repeat,
                        "child": child.name,
                        "ms": round(ms, 2),
                        "new_batch": result.created,
                    }
                )
    peak, current = memory_mb()
    write_csv("latency_runs.csv", rows)
    ms = [r["ms"] for r in rows]
    new = [r["ms"] for r in rows if r["new_batch"]]
    same = [r["ms"] for r in rows if not r["new_batch"]]
    summary = {
        "requests": len(ms),
        "p50_ms": round(statistics.median(ms), 1),
        "p95_ms": round(pct(ms, 95), 1),
        "max_ms": round(max(ms), 1),
        "new_batch": {
            "n": len(new),
            "p50_ms": round(statistics.median(new), 1) if new else None,
        },
        "identical_batch": {
            "n": len(same),
            "p50_ms": round(statistics.median(same), 1) if same else None,
        },
        "startup_s": round(startup, 1),
        "peak_working_set_mb_after_model_load": round(after_load, 0),
        "peak_working_set_mb_end": round(peak, 0),
    }
    write_json("latency_summary.json", summary)
    body = f"""In-process `generation.generate()` for the 20 held-out children, {REPEATS} repeats each, inside a rolled-back transaction (nothing saved). Model warm in this process. Raw: `raw/latency_runs.csv`, `raw/latency_summary.json`.

{table(['Measure', 'Value'], [
    ['Requests', summary['requests']],
    ['p50', f"{summary['p50_ms']} ms"],
    ['p95', f"{summary['p95_ms']} ms"],
    ['Slowest', f"{summary['max_ms']} ms"],
    ['New batch stored (first repeat)', f"n = {summary['new_batch']['n']}, p50 {summary['new_batch']['p50_ms']} ms"],
    ['Identical batch returned (repeats 2–5)', f"n = {summary['identical_batch']['n']}, p50 {summary['identical_batch']['p50_ms']} ms"],
    ['Start-up (script start → model loaded and one query encoded)', f"{summary['startup_s']} s"],
    ['Peak working set after model load', f"{summary['peak_working_set_mb_after_model_load']:.0f} MB"],
    ['Peak working set at the end', f"{summary['peak_working_set_mb_end']:.0f} MB"],
])}

Machine: see `02_environment.md`. Not a load test, and not over HTTP; `docs/performance_recommendations.md` has the HTTP figures and the server cold start.
"""
    write_md("05_latency.md", body, "Latency repeat (exploratory)", COMMAND)
    print(summary)


if __name__ == "__main__":
    main()
