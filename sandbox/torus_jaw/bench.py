"""Benchmark every candidate airborne jaw detector against the reference solver.

Usage:
    python sandbox/torus_jaw/bench.py [n_per_family] [seed]
"""

import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from numba import njit

sys.path.insert(0, str(Path(__file__).parent))
from geometry import (
    FAMILIES,
    JAWS,
    G,
    generate_cases,
    reference_octic,
    reference_solution,
)
from methods import METHODS, windows

WRONG_ROOT = 1e-7
GRAZE = 1e-4


def make_runner(fn):
    @njit
    def run(cases, out_t, out_it):
        for i in range(cases.shape[0]):
            c = cases[i]
            t, it = fn(c[0], c[1], c[2], c[3], c[4], c[5], G, c[6], c[7])
            out_t[i] = t
            out_it[i] = it

    return run


def time_runner(run, cases, target_s=0.6):
    n = cases.shape[0]
    out_t = np.empty(n)
    out_it = np.empty(n)
    run(cases, out_t, out_it)
    reps = 1
    while True:
        t0 = time.perf_counter()
        for _ in range(reps):
            run(cases, out_t, out_it)
        el = time.perf_counter() - t0
        if el > target_s:
            break
        reps *= 2
    return el / (reps * n) * 1e9, out_t, out_it


def time_python_calls(fn, cases, k=2000):
    sub = cases[:k]
    for c in sub[:10]:
        fn(c[0], c[1], c[2], c[3], c[4], c[5], G, c[6], c[7])
    t0 = time.perf_counter()
    for c in sub:
        fn(c[0], c[1], c[2], c[3], c[4], c[5], G, c[6], c[7])
    return (time.perf_counter() - t0) / len(sub) * 1e6


def main(n_per_family=150, seed=0):
    cases, labels = generate_cases(n_per_family, seed)
    n = len(cases)
    print(
        f"{n} cases ({n_per_family} per family x {len(FAMILIES)} families x {len(JAWS)} jaws)"
    )

    t0 = time.perf_counter()
    ref = np.array([reference_solution(c) for c in cases])
    t_true, d_min = ref[:, 0], ref[:, 1]
    print(f"reference solved in {time.perf_counter() - t0:.1f}s")

    t_oct = np.array([reference_octic(c) for c in cases])
    both = np.isfinite(t_true) & np.isfinite(t_oct)
    mism = (np.isfinite(t_true) != np.isfinite(t_oct)).sum()
    err = np.abs(t_true[both] - t_oct[both])
    print(
        f"reference vs numpy-octic: {mism} hit/miss disagreements, max |dt| {err.max():.2e} over {both.sum()} hits"
    )

    hit = np.isfinite(t_true)
    depth = np.where(hit, cases[:, 7] - d_min, np.nan)
    graze = hit & (depth < GRAZE)
    near_miss = ~hit & ((d_min - cases[:, 7]) < GRAZE)
    print(
        f"truth: {hit.sum()} hits ({graze.sum()} grazes < {GRAZE} m deep), {(~hit).sum()} misses ({near_miss.sum()} near misses)"
    )
    fam_counts = Counter(lab[1] for lab, h in zip(labels, hit) if h)
    print("hits by family:", dict(fam_counts))
    print()

    header = f"{'method':18s} {'ns/call':>8s} {'us/pycall':>9s} {'FN':>4s} {'FN_graze':>8s} {'FP':>4s} {'FP_near':>7s} {'wrong':>5s} {'max_err':>9s} {'med_err':>9s} {'iters':>6s} {'max':>4s}"
    print(header)
    print("-" * len(header))
    failures = {}
    for name, fn in METHODS.items():
        run = make_runner(fn)
        ns, t_m, it_m = time_runner(run, cases)
        us_py = time_python_calls(fn, cases)
        m_hit = np.isfinite(t_m)
        fn_mask = hit & ~m_hit
        fp_mask = ~hit & m_hit
        both = hit & m_hit
        err = np.abs(t_m[both] - t_true[both])
        wrong_mask = np.zeros(n, dtype=bool)
        wrong_mask[np.flatnonzero(both)[err > WRONG_ROOT]] = True
        ok_err = err[err <= WRONG_ROOT]
        max_err = ok_err.max() if ok_err.size else float("nan")
        med_err = np.median(ok_err) if ok_err.size else float("nan")
        iters = it_m[hit & m_hit].mean() if (hit & m_hit).any() else 0
        iters_max = it_m.max()
        print(
            f"{name:18s} {ns:8.0f} {us_py:9.2f} {fn_mask.sum():4d} {(fn_mask & graze).sum():8d} "
            f"{fp_mask.sum():4d} {(fp_mask & near_miss).sum():7d} {wrong_mask.sum():5d} {max_err:9.1e} {med_err:9.1e} {iters:6.1f} {iters_max:4.0f}"
        )
        failures[name] = (fn_mask, fp_mask, wrong_mask, t_m)

    print()
    bins = [0, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, np.inf]
    print("false negatives by contact depth (m):")
    labels_bins = [f"<{b:.0e}" for b in bins[1:]]
    print(f"{'method':18s} " + " ".join(f"{s:>7s}" for s in labels_bins))
    idx = np.digitize(depth[hit], bins) - 1
    for name, (fn_mask, _, _, _) in failures.items():
        counts = np.bincount(idx[fn_mask[hit]], minlength=len(bins) - 1)
        totals = np.bincount(idx, minlength=len(bins) - 1)
        print(
            f"{name:18s} " + " ".join(f"{c:3d}/{t:<3d}" for c, t in zip(counts, totals))
        )
    print()
    for name in ("newton", "tangent", "meridian", "quadric", "sample_bisect_16"):
        fn_mask, fp_mask, wrong_mask, t_m = failures[name]
        bad = fn_mask | fp_mask | wrong_mask
        if not bad.any():
            print(f"{name}: no failures")
            continue
        by = defaultdict(int)
        for i in np.flatnonzero(bad):
            kind = "FN" if fn_mask[i] else ("FP" if fp_mask[i] else "wrong")
            by[(labels[i][0], labels[i][1], kind)] += 1
        print(f"{name} failures by (jaw, family, kind):")
        for k, v in sorted(by.items()):
            print(f"    {k}: {v}")
        worst = np.flatnonzero(bad)[:3]
        for i in worst:
            print(
                f"    case {i} {labels[i]}: truth={t_true[i]:.6g} depth={depth[i]:.2e} d_min-D={d_min[i] - cases[i, 7]:.2e} got={t_m[i]:.6g}"
            )
    print("quadric iteration histogram (hits / misses-after-window):")
    for name in ("quadric", "quadric_nowindow"):
        run = make_runner(METHODS[name])
        out_t = np.empty(n)
        out_it = np.empty(n)
        run(cases, out_t, out_it)
        ih = np.bincount(out_it[hit].astype(int))
        im = np.bincount(out_it[~hit].astype(int))
        print(
            f"  {name} hits:   " + " ".join(f"{i}:{c}" for i, c in enumerate(ih) if c)
        )
        print(
            f"  {name} misses: " + " ".join(f"{i}:{c}" for i, c in enumerate(im) if c)
        )
        for fam in FAMILIES:
            sel = np.array([lab[1] == fam for lab in labels]) & hit
            if sel.any():
                print(
                    f"      {fam:10s} hits: mean {out_it[sel].mean():.1f} max {out_it[sel].max():.0f}"
                )
    nwin = np.array(
        [windows(c[0], c[1], c[2], c[3], c[4], c[5], G, c[6], c[7])[0] for c in cases]
    )
    print("window counts:", dict(zip(*np.unique(nwin, return_counts=True))))


if __name__ == "__main__":
    n_per = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    main(n_per, int(sys.argv[2]) if len(sys.argv) > 2 else 0)
