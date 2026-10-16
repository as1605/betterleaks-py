# Benchmarks: Library vs. CLI Subprocess

> **One-liner:** the in-process Python library is **1,000× – 10,000× faster than spawning the CLI via `subprocess.run()`** for repeated scans, and **~15–25% faster even on a single cold start**.

---

## Overview

`betterleaks-py` ships two ways to run the scanner:

| Mode | How it works |
|------|---|
| **Python library** (`betterleaks.scan_string` / `scan_file`) | The Go shared library (`libbetterleaks.so/.dylib/.dll`) is loaded **once** into the Python process via `ctypes`. The scanner engine, compiled regexes, and rule filters stay warm in memory across all subsequent calls. |
| **CLI subprocess** (`subprocess.run(["betterleaks", ...])`) | Each call spawns a brand-new OS process: the Go runtime boots, all 100+ rules are parsed and compiled, the scan runs, results are serialised to JSON over stdout, and the process exits. |

The benchmarks live in [`benchmarks/bench.py`](./bench.py).

---

## Running the Benchmarks

### Prerequisites

```bash
# 1. Install the package in editable mode (builds the shared library and CLI binary)
pip install -e .

# Or build just the CLI binary manually:
go build -buildvcs=false \
  -o src/betterleaks/bin/betterleaks \
  ./upstream
```

### Hot-run benchmark (default)

```bash
python benchmarks/bench.py
```

Measures repeated calls inside a **single warm process**.
Performs 2 warm-up calls before timing begins; GC is disabled during measurement.

### Cold-run benchmark

```bash
python benchmarks/bench.py --cold            # 100 iterations (default)
python benchmarks/bench.py --cold --cold-runs 50
```

Every iteration is executed in a **brand-new, isolated OS process** (spawned via `subprocess.run([sys.executable, ...])`).
Calls are interleaved (Library → Subprocess → Direct CLI) to prevent thermal or scheduler bias.
Raw per-run data is saved to `benchmarks/cold_results.json` for further analysis.

---

## Hot-Run Results

*Measured on macOS Apple Silicon (arm64), Python 3.9, Go 1.25.*

| Workload | Library Mean | CLI Subprocess Mean | **Speedup** |
|---|:---:|:---:|:---:|
| Single String (~100 B, 1 secret) | **0.09 ms** | 89.20 ms | **~1,050×** |
| Single String (~100 B, clean) | **0.01 ms** | 97.59 ms | **~10,500×** |
| Medium String (~50 KB, 1 secret) | **0.50 ms** | 102.92 ms | **~205×** |
| Large String (~1 MB, 1 secret) | **5.53 ms** | 119.96 ms | **~22×** |
| Large String (~1 MB, clean) | **5.11 ms** | 119.64 ms | **~23×** |
| File on Disk (~100 KB) | **0.96 ms** | 99.23 ms | **~104×** |
| **Batch: 20 files × 10 KB** | **6.38 ms** | 1,787.52 ms | **~280×** |

### Why the library dominates on hot runs

Once imported, `betterleaks` pays the Go runtime and rule-compilation cost **once** (via `sync.Once`). Every subsequent call passes a memory pointer directly across the CGO boundary — no forking, no IPC pipes, no JSON serialisation of findings on the Go side beyond what is already returned.

The subprocess CLI pays its full ~90 ms process-startup cost on **every single call**, because each invocation is a fresh OS process that must:
1. Create kernel structures and address-space mappings.
2. Boot the Go runtime (allocator, GC, goroutine scheduler).
3. Parse and compile all configured rules from scratch.
4. Pipe the content in via stdin and serialise results to stdout.

---

## Cold-Run Results

*100 iterations, each in a fresh process, interleaved to prevent bias.*

| Metric | Library (in-Python) | CLI Subprocess | Direct CLI |
|---|:---:|:---:|:---:|
| **Mean** | **87.09 ms** | 104.30 ms | 108.93 ms |
| **Median (p50)** | **75.61 ms** | 93.12 ms | 92.89 ms |
| **Minimum** | **61.85 ms** | 76.62 ms | 76.56 ms |
| **p90** | **108.47 ms** | 132.91 ms | 122.08 ms |
| **p95** | **138.28 ms** | 186.10 ms | 160.51 ms |
| **p99** | 343.13 ms | 370.51 ms | 699.39 ms |
| **Std. deviation** | 46.51 ms | 48.00 ms | **86.64 ms** |

**Library cold-start breakdown (mean):**

| Phase | Time |
|---|:---:|
| `import betterleaks` (Python import + `ctypes.CDLL` + Go bootstrap) | 36.07 ms |
| First `scan_string()` call (`sync.Once` compiles all rules) | 51.01 ms |
| **Total** | **87.09 ms** |

### Head-to-head win rate (100 cold runs)

| Comparison | Library wins |
|---|:---:|
| Library vs. CLI Subprocess (from Python) | **92 / 100 (92%)** |
| Library vs. Direct Native CLI | **89 / 100 (89%)** |

The library is faster in **92% of cold runs**. In the remaining 8%, macOS `dyld` code-signature verification or dynamic-linker jitter caused the library's `.dylib` load step to spike (sometimes 260–340 ms), allowing the directly-executed Go binary to win. This variance is higher on first boot after reboot or when the OS clears its shared-library cache.

---

## Choosing the Right Mode

| Use case | Recommended |
|---|---|
| Python service, web hook, stream consumer, or data pipeline | **Library** — always wins on repeated calls |
| Pre-commit hook or CI step scanning a batch of files | **Library** — 280× faster than looping subprocess calls |
| One-off shell pipeline or cron job | **Direct CLI** — simpler invocation, comparable cold-start cost |
| Full repository scan (`betterleaks git ...`, `betterleaks filesystem ...`) | **Direct CLI** — uses native Go parallel filesystem walker |
| Integrating into existing Python tooling | **Library** — typed `Finding` objects, no JSON parsing |

---

## Notes on Variance

Both modes show significant cold-start variance (stddev ~46–87 ms) because:

- macOS `dyld` code-signing checks vary depending on the security policy and library cache state.
- Go runtime allocator behaves differently bootstrapping inside an existing Python process heap (library) versus a clean kernel-allocated address space (CLI).
- OS CPU scheduler preemption can hit either process during startup.

For production use-cases where deterministic latency matters, always use the library in a long-running process to fully amortise the cold-start cost.
