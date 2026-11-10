"""Measure whole native simulations in a fresh, isolated benchmark directory.

Run from the contribution checkout with the development dependencies:
    python -m sandbox.compiled_fp64_benchmark --output <new-directory>

Optionally use --cache-only-ref <trusted Git revision> to measure the separate
cache optimization with the same reference physics. The benchmark executes
only that revision's original CollisionCache.invalidate method.
"""

import argparse
import ast
import json
import os
import platform
import subprocess
import sys
from contextlib import nullcontext
from importlib.metadata import version
from pathlib import Path
from statistics import median
from time import perf_counter, process_time
from unittest.mock import patch

THREADS = (
    "NUMBA_NUM_THREADS",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "BLIS_NUM_THREADS",
)
REFERENCE = "reference"
COMPILED = "compiled_fp64"
CACHE_ONLY = "cache-only"
DT = 0.02
REPO = Path(__file__).resolve().parents[1]


def _git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args]).decode().strip()


def _cache_method(revision):
    from pooltool.evolution.event_based import cache

    source = _git("show", f"{revision}:pooltool/evolution/event_based/cache.py")
    collision_cache = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef) and node.name == "CollisionCache"
    )
    method = next(
        node
        for node in collision_cache.body
        if isinstance(node, ast.FunctionDef) and node.name == "invalidate"
    )
    namespace = dict(vars(cache))
    exec(  # noqa: S102 - benchmark the method from the explicitly trusted Git revision
        compile(ast.Module(body=[method], type_ignores=[]), "<cache revision>", "exec"),
        namespace,
    )
    return namespace["invalidate"]


def _rss():
    import psutil

    return psutil.Process().memory_info().rss


def _peak_rss():
    if sys.platform == "win32":
        import psutil

        return psutil.Process().memory_info().peak_wset
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak if sys.platform == "darwin" else peak * 1024


def _timed(shot, physics, variant, count):
    import pooltool as pt

    memory_before = _rss()
    started, cpu = perf_counter(), process_time()
    try:
        results = [
            pt.simulate(
                shot,
                engine=physics,
                backend=variant if variant != CACHE_ONLY else REFERENCE,
                continuous=True,
                dt=DT,
            )
            for _ in range(count)
        ]
    except Exception as error:  # noqa: BLE001 - retain failed trials in the receipt
        return {
            "wall_s": perf_counter() - started,
            "cpu_s": process_time() - cpu,
            "failure": f"{type(error).__name__}: {error}",
        }, []
    elapsed, cpu_elapsed = perf_counter() - started, process_time() - cpu
    return {
        "wall_s": elapsed,
        "cpu_s": cpu_elapsed,
        "rss_before_bytes": memory_before,
        "rss_after_bytes": _rss(),
        "events": [len(result.events) for result in results],
        "trajectories": [
            sum(len(ball.history_cts) for ball in result.balls.values())
            for result in results
        ],
    }, results


def _compare_results(expected, actual):
    from sandbox.compiled_fp64_workloads import compare

    started = perf_counter()
    try:
        assert len(expected) == len(actual) and expected
        for ref, candidate in zip(expected, actual):
            compare(ref, candidate)
    except AssertionError as error:
        return {
            "wall_s": perf_counter() - started,
            "failure": f"{type(error).__name__}: {error}",
        }
    return {"wall_s": perf_counter() - started, "matched": len(expected)}


def _startup(args, shot, physics):
    report, results = _timed(shot, physics, args.variant, 1)
    if results:
        started = perf_counter()
        results[0].save(args.output)
        report["save_s"] = perf_counter() - started
    return report


def _verify_startup(args):
    import pooltool as pt

    results = {}
    for phase in ("cold", "cached"):
        paths = [
            args.output / f"{phase}-{variant}.msgpack"
            for variant in (REFERENCE, COMPILED)
        ]
        if not all(path.exists() for path in paths):
            results[phase] = {"failure": "One or both startup simulations failed"}
        else:
            results[phase] = _compare_results(
                [pt.System.load(paths[0])], [pt.System.load(paths[1])]
            )
    return results


def _warm(args, workloads, physics):
    from pooltool.evolution.event_based.cache import CollisionCache

    methods = {REFERENCE: None, COMPILED: None}
    if args.cache_only_ref:
        methods[CACHE_ONLY] = _cache_method(args.cache_only_ref)

    def cache_scope(method):
        return (
            nullcontext()
            if method is None
            else patch.object(CollisionCache, "invalidate", method)
        )

    warmup = {}
    for variant, method in methods.items():
        with cache_scope(method):
            warmup[variant] = {
                name: _timed(shot, physics, variant, 1)[0]
                for name, shot in workloads.items()
            }

    pairs = []
    for i in range(args.pairs):
        order = list(methods)
        if i % 2:
            order.reverse()
        row = {"pair": i + 1, "order": order, "workloads": {}}
        for name, shot in workloads.items():
            for kind, count in (("single", 1), ("batch", args.batch_size)):
                result = {"simulations": count, "timings": {}, "verification": {}}
                outputs = {}
                for variant in order:
                    with cache_scope(methods[variant]):
                        metrics, shots = _timed(shot, physics, variant, count)
                    result["timings"][variant] = metrics
                    outputs[variant] = shots
                for variant in order:
                    if variant != REFERENCE:
                        result["verification"][variant] = _compare_results(
                            outputs[REFERENCE], outputs[variant]
                        )
                row["workloads"][f"{name}/{kind}"] = result
        pairs.append(row)

    summary = {}
    for workload in pairs[0]["workloads"]:
        summary[workload] = {}
        for variant in methods:
            rows = [row["workloads"][workload] for row in pairs]
            samples = [
                row["timings"][variant]["wall_s"]
                for row in rows
                if "failure" not in row["timings"][variant]
                and all(
                    "failure" not in check for check in row["verification"].values()
                )
            ]
            summary[workload][variant] = {
                "valid_paired_samples": len(samples),
                "minimum_s": min(samples) if samples else None,
                "median_s": median(samples) if samples else None,
                "maximum_s": max(samples) if samples else None,
            }
    return {"warmup": warmup, "pairs": pairs, "summary": summary}


def _child(args):
    started = perf_counter()
    import pooltool as pt
    from sandbox.compiled_fp64_workloads import cluster, engine, sparse, straight

    import_s = perf_counter() - started
    if Path(pt.__file__).resolve().parent != REPO / "pooltool":
        raise RuntimeError("Expected Pooltool from this checkout")
    started = perf_counter()
    physics = engine()
    if args.child == "startup":
        shot = cluster()
        fixture_s = perf_counter() - started
        results = _startup(args, shot, physics)
    elif args.child == "verify":
        fixture_s = perf_counter() - started
        results = _verify_startup(args)
    else:
        workloads = {"cluster": cluster(), "ordinary": straight(), "sparse": sparse()}
        fixture_s = perf_counter() - started
        results = _warm(args, workloads, physics)
    return {
        "import_s": import_s,
        "fixture_s": fixture_s,
        "process_peak_rss_bytes": _peak_rss(),
        "results": results,
    }


def _run_child(mode, output, cache, config, args, variant=REFERENCE):
    cache.mkdir(parents=True, exist_ok=True)
    config.mkdir(parents=True, exist_ok=True)
    cache_path = str(cache)
    if sys.platform == "win32" and not cache_path.startswith("\\\\?\\"):
        cache_path = (
            "\\\\?\\UNC\\" + cache_path[2:]
            if cache_path.startswith("\\\\")
            else "\\\\?\\" + cache_path
        )
    env = dict(os.environ)
    env.update({name: "1" for name in THREADS})
    env["NUMBA_CACHE_DIR"] = cache_path
    env["USERPROFILE" if sys.platform == "win32" else "HOME"] = str(config)
    env.pop("PYTHONPATH", None)
    command = [
        sys.executable,
        "-B",
        "-m",
        "sandbox.compiled_fp64_benchmark",
        "--child",
        mode,
        "--output",
        str(output),
        "--variant",
        variant,
        "--pairs",
        str(args.pairs),
        "--batch-size",
        str(args.batch_size),
    ]
    if args.cache_only_ref:
        command += ["--cache-only-ref", args.cache_only_ref]
    entries = sum(1 for _ in cache.rglob("*.nbc"))
    started = perf_counter()
    try:
        child = subprocess.run(
            command,
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return {"failure": "Benchmark subprocess exceeded 600 s"}
    elapsed = perf_counter() - started
    metadata = {
        "process_wall_s": elapsed,
        "returncode": child.returncode,
        "cache_entries_before": entries,
        "cache_entries_after": sum(1 for _ in cache.rglob("*.nbc")),
    }
    if child.stderr:
        metadata["stderr"] = child.stderr
    try:
        metadata.update(json.loads(child.stdout))
    except json.JSONDecodeError:
        metadata.update(failure="Child did not emit a result", stdout=child.stdout)
    return metadata


def _failed(value):
    if isinstance(value, dict):
        return (
            "failure" in value
            or value.get("returncode", 0) != 0
            or any(_failed(item) for item in value.values())
        )
    return isinstance(value, list) and any(_failed(item) for item in value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--cache-only-ref", help="Trusted Git commit with cache patch")
    parser.add_argument("--child", choices=("startup", "warm", "verify"))
    parser.add_argument("--variant", choices=(REFERENCE, COMPILED), default=REFERENCE)
    args = parser.parse_args()
    if args.pairs < 1 or args.batch_size < 2:
        parser.error("use at least one pair and at least two shots per batch")
    if args.child:
        print(json.dumps(_child(args), sort_keys=True))
        return

    if args.cache_only_ref:
        args.cache_only_ref = _git(
            "rev-parse", "--verify", f"{args.cache_only_ref}^{{commit}}"
        )
    output = args.output.resolve()
    if output.is_relative_to(REPO):
        parser.error("Use an output directory outside the contribution checkout")
    output.mkdir(parents=True, exist_ok=False)
    report = {
        "head": _git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(_git("status", "--porcelain=v1")),
        "cache_only_ref": args.cache_only_ref,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu": platform.processor(),
            "cpu_count": os.cpu_count(),
            "packages": {
                name: version(name)
                for name in (
                    "pooltool-billiards",
                    "numpy",
                    "numba",
                    "scipy",
                    "llvmlite",
                )
            },
            "thread_settings": dict.fromkeys(THREADS, 1),
        },
        "pairs_requested": args.pairs,
        "batch_size": args.batch_size,
        "dt": DT,
        "startup": {},
    }
    config = output / "config"
    for phase in ("cold", "cached"):
        report["startup"][phase] = {}
        for variant in (REFERENCE, COMPILED):
            report["startup"][phase][variant] = _run_child(
                "startup",
                output / f"{phase}-{variant}.msgpack",
                output / f"jit-{variant}",
                config,
                args,
                variant,
            )
    report["startup_verification"] = _run_child(
        "verify", output, output / f"jit-{COMPILED}", config, args
    )
    report["warm"] = _run_child(
        "warm", output, output / f"jit-{COMPILED}", config, args
    )
    receipt = output / "timings.json"
    receipt.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(receipt)
    if _failed(report):
        raise SystemExit("At least one benchmark workload or verification failed")


if __name__ == "__main__":
    main()
