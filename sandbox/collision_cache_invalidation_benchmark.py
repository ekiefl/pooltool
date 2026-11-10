"""Compare collision-cache invalidation with an upstream Git revision.

From the contribution checkout, use the development environment and run
``python -m sandbox.collision_cache_invalidation_benchmark --base <base-sha>``.
Select a dedicated NUMBA_CACHE_DIR before launch. Run once with an empty cache
and again with the same directory to distinguish compilation from cache load.
Use only a trusted base revision. The benchmark executes its original method.
"""

import argparse
import ast
import hashlib
import json
import os
import platform
import subprocess
from importlib.metadata import version
from itertools import combinations
from math import sqrt
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
CACHE_COPIES = 600
CLUSTER_SHOTS = 4
LIGHT_SHOTS = 20
DT = 0.02


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Trusted upstream Git revision")
    parser.add_argument("--pairs", type=int, default=5)
    args = parser.parse_args()
    if args.pairs < 1:
        parser.error("--pairs must be positive")

    for setting in THREADS:
        os.environ[setting] = "1"
    cache_root = os.environ.get("NUMBA_CACHE_DIR")
    if not cache_root:
        parser.error("set NUMBA_CACHE_DIR to a dedicated writable directory")
    populated_at_start = any(Path(cache_root).rglob("*.nbc"))
    started = perf_counter()
    # Thread configuration and the cache check must precede numerical imports.
    import msgpack
    import msgpack_numpy

    import pooltool as pt
    from pooltool.events import ball_ball_collision
    from pooltool.evolution.engine import SimulationEngine
    from pooltool.evolution.event_based import cache
    from pooltool.physics.resolve.resolver import default_resolver
    from pooltool.serialize import SerializeFormat, conversion

    import_s = perf_counter() - started
    repo = Path(__file__).resolve().parents[1]
    cache_source = "pooltool/evolution/event_based/cache.py"
    if Path(cache.__file__).resolve() != repo / cache_source:
        raise RuntimeError("Pooltool was not imported from this contribution checkout")

    def git(*arguments):
        return subprocess.check_output(["git", "-C", str(repo), *arguments])

    base = git("rev-parse", "--verify", f"{args.base}^{{commit}}").decode().strip()
    upstream = git("show", f"{base}:{cache_source}")
    cache_class = next(
        node
        for node in ast.parse(upstream).body
        if isinstance(node, ast.ClassDef) and node.name == "CollisionCache"
    )
    original = next(
        node
        for node in cache_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "invalidate"
    )
    namespace = dict(vars(cache))
    exec(  # noqa: S102 - execute only the explicitly trusted base Git method
        compile(ast.Module(body=[original], type_ignores=[]), "<upstream Git>", "exec"),
        namespace,
    )
    methods = [
        ("upstream", namespace["invalidate"]),
        ("optimized", cache.CollisionCache.invalidate),
    ]

    started = perf_counter()
    table = pt.Table.default()
    balls = [f"ball-{i}" for i in range(16)]
    times = {pt.EventType.BALL_BALL: dict.fromkeys(combinations(balls, 2), 1.0)}
    for category, targets in (
        (pt.EventType.BALL_LINEAR_CUSHION, table.cushion_segments.linear),
        (pt.EventType.BALL_CIRCULAR_CUSHION, table.cushion_segments.circular),
        (pt.EventType.BALL_POCKET, table.pockets),
    ):
        times[category] = dict.fromkeys(
            ((ball, target) for ball in balls for target in targets), 2.0
        )
    event = ball_ball_collision(pt.Ball.create(balls[0]), pt.Ball.create(balls[1]), 0.5)
    params = pt.BallParams.default()
    spacing = 2 * params.R * 1.001
    rack = {
        f"rack-{row}-{col}": pt.Ball.create(
            f"rack-{row}-{col}",
            xy=(
                table.w / 2 + spacing * (col - row / 2),
                table.l * 0.62 + spacing * row * sqrt(3) / 2,
            ),
        )
        for row in range(5)
        for col in range(row + 1)
    }
    rack["cue"] = pt.Ball.create("cue", xy=(table.w * 0.44, table.l * 0.28))
    cluster = pt.System(cue=pt.Cue.default(), table=table, balls=rack)
    cluster.strike(V0=6.5, phi=pt.aim.at_ball(cluster, "rack-0-0"), a=0.05, b=-0.1)
    shots = [
        ("cluster", cluster, CLUSTER_SHOTS),
        ("light", pt.System.example(), LIGHT_SHOTS),
    ]
    engine = SimulationEngine(is_3d=False, resolver=default_resolver())
    setup_s = perf_counter() - started

    def simulation_sample(shot, count, verify=True):
        started, cpu = perf_counter(), process_time()
        systems = [
            pt.simulate(shot, engine=engine, continuous=True, dt=DT)
            for _ in range(count)
        ]
        wall_s, cpu_s = perf_counter() - started, process_time() - cpu
        digest = hashlib.sha256()
        if verify:
            for result in systems:
                data = conversion[SerializeFormat.MSGPACK].unstructure(result)
                packed = msgpack.packb(data, default=msgpack_numpy.encode)
                assert isinstance(packed, bytes)
                digest.update(packed)
        return {
            "wall_s": wall_s,
            "cpu_s": cpu_s,
            "events": sum(len(result.events) for result in systems),
            "signature": digest.hexdigest() if verify else None,
        }

    def cache_sample(method):
        copies = [
            cache.CollisionCache(
                {kind: values.copy() for kind, values in times.items()}
            )
            for _ in range(CACHE_COPIES)
        ]
        started, cpu = perf_counter(), process_time()
        for item in copies:
            method(item, event)
        wall_s, cpu_s = perf_counter() - started, process_time() - cpu
        ordered_contents = [
            tuple((kind, tuple(values.items())) for kind, values in item.times.items())
            for item in copies
        ]
        return {
            "wall_s": wall_s,
            "cpu_s": cpu_s,
            "signature": hashlib.sha256(repr(ordered_contents).encode()).hexdigest(),
        }

    # The two variants use the same numerical kernels and same Python process.
    # Record first execution separately, then alternate warm orders.
    first_shots = {}
    with patch.object(cache.CollisionCache, "invalidate", methods[0][1]):
        for name, shot, _ in shots:
            first_shots[name] = simulation_sample(shot, 1, verify=False)

    rows = []
    for pair in range(args.pairs):
        ordered = methods if pair % 2 == 0 else methods[::-1]
        matched = {}
        for name, method in ordered:
            measurements = {"invalidation": cache_sample(method)}
            with patch.object(cache.CollisionCache, "invalidate", method):
                for workload, shot, count in shots:
                    measurements[workload] = simulation_sample(shot, count)
            matched[name] = {
                key: (sample["signature"], sample.get("events"))
                for key, sample in measurements.items()
            }
            rows.append({"pair": pair + 1, "variant": name, "workloads": measurements})
        if matched["upstream"] != matched["optimized"]:
            raise AssertionError(
                f"Cache or complete simulation changed in pair {pair + 1}"
            )

    summary = {}
    for workload in ("invalidation", "cluster", "light"):
        summary[workload] = {}
        for variant, _ in methods:
            seconds = [
                row["workloads"][workload]["wall_s"]
                for row in rows
                if row["variant"] == variant
            ]
            summary[workload][variant] = {
                "median_s": median(seconds),
                "minimum_s": min(seconds),
                "maximum_s": max(seconds),
            }
    print(
        json.dumps(
            {
                "base": base,
                "head": git("rev-parse", "HEAD").decode().strip(),
                "upstream_source_sha256": hashlib.sha256(upstream).hexdigest(),
                "checkout_source_sha256": hashlib.sha256(
                    (repo / cache_source).read_bytes()
                ).hexdigest(),
                "environment": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "architecture": platform.machine(),
                    "python": platform.python_version(),
                    "logical_cpus": os.cpu_count(),
                    "packages": {
                        name: version(name)
                        for name in (
                            "pooltool-billiards",
                            "numpy",
                            "numba",
                            "scipy",
                            "llvmlite",
                            "panda3d",
                        )
                    },
                    "thread_settings": {name: os.environ[name] for name in THREADS},
                },
                "setup": {
                    "populated_cache_at_start": populated_at_start,
                    "import_wall_s": import_s,
                    "fixture_wall_s": setup_s,
                    "first_shots": first_shots,
                },
                "invalidations_per_sample": CACHE_COPIES,
                "initial_entries_per_cache": sum(map(len, times.values())),
                "simulations_per_sample": {name: count for name, _, count in shots},
                "continuous_dt_s": DT,
                "summary": summary,
                "samples": rows,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
