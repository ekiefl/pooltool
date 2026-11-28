"""Head-to-head: exact octic vs enclosing quadric on a large airborne case set.

Usage:
    python sandbox/torus_jaw/bench3.py [n_per_family] [seed]
"""

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from bench import make_runner, time_runner
from geometry import FAMILIES, JAWS, generate_cases, reference_solution
from methods import detect_octic, detect_quadric

n_per = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11

t0 = time.perf_counter()
cases, labels = generate_cases(n_per, seed)
n = len(cases)
fams = np.array([lab[1] for lab in labels])
jaws = np.array([lab[0] for lab in labels])
print(
    f"{n} airborne cases ({n_per} per family x {len(FAMILIES)} families x {len(JAWS)} jaws), seed {seed}; generated in {time.perf_counter() - t0:.1f}s"
)

ns_o, t_o, _ = time_runner(make_runner(detect_octic), cases, target_s=2.0)
ns_q, t_q, it_q = time_runner(make_runner(detect_quadric), cases, target_s=2.0)
print(f"octic:   {ns_o:8.0f} ns/call")
print(f"quadric: {ns_q:8.0f} ns/call   ratio {ns_o / ns_q:.0f}x")

hit_o, hit_q = np.isfinite(t_o), np.isfinite(t_q)
both = hit_o & hit_q
dt = np.abs(t_o[both] - t_q[both])
print(
    f"\nhits: octic {hit_o.sum()}, quadric {hit_q.sum()}, both {both.sum()}, neither {(~hit_o & ~hit_q).sum()}"
)
print(f"hit/miss disagreements: {(hit_o != hit_q).sum()}")
print(
    f"among shared hits: |dt| max {dt.max():.2e} s, 99.9th pct {np.percentile(dt, 99.9):.2e} s, count > 1e-9 s: {(dt > 1e-9).sum()}, count > 1e-7 s: {(dt > 1e-7).sum()}"
)

disagree = np.flatnonzero((hit_o != hit_q) | (both & (np.abs(t_o - t_q) > 1e-9)))
if disagree.size:
    print(
        f"\nadjudicating {disagree.size} disagreements with the brute-force reference:"
    )
    tally = {}
    for i in disagree[:200]:
        t_ref, d_min = reference_solution(cases[i])
        c = cases[i]
        ok_o = (np.isfinite(t_ref) == np.isfinite(t_o[i])) and (
            not np.isfinite(t_ref) or abs(t_ref - t_o[i]) < 1e-7
        )
        ok_q = (np.isfinite(t_ref) == np.isfinite(t_q[i])) and (
            not np.isfinite(t_ref) or abs(t_ref - t_q[i]) < 1e-7
        )
        key = (
            "octic right" if ok_o else "octic wrong",
            "quadric right" if ok_q else "quadric wrong",
        )
        tally[key] = tally.get(key, 0) + 1
        if len(tally) <= 8 and tally[key] <= 2:
            print(
                f"  case {i} {labels[i]}: ref {t_ref:.9g}  octic {t_o[i]:.9g}  quadric {t_q[i]:.9g}  gap-to-locus {d_min - c[7]:+.2e} m"
            )
    for k, v in sorted(tally.items()):
        print(f"  {k}: {v}")
    if disagree.size > 200:
        print(f"  (first 200 of {disagree.size} adjudicated)")
else:
    print("\nno disagreements to adjudicate")

print("\nquadric solves per call:")
ih = np.bincount(it_q[hit_q].astype(int))
im = np.bincount(it_q[~hit_q].astype(int))
hit_hist = " ".join(f"{i}:{c}" for i, c in enumerate(ih) if c)
miss_hist = " ".join(f"{i}:{c}" for i, c in enumerate(im) if c)
print(
    f"  on hits:   mean {it_q[hit_q].mean():.2f} max {int(it_q[hit_q].max())}"
    f"  hist {hit_hist}"
)
print(
    f"  on misses: mean {it_q[~hit_q].mean():.2f} max {int(it_q[~hit_q].max())}"
    f"  hist {miss_hist}"
)
print("\nby family (hits / cases, mean solves on hits, max solves):")
for f in FAMILIES:
    sel = fams == f
    h = sel & hit_q
    print(
        f"  {f:10s} {h.sum():5d} / {sel.sum():5d}   {it_q[h].mean():5.2f}   {int(it_q[sel].max()):3d}"
    )
print("by jaw:")
for j in [jw.name for jw in JAWS]:
    sel = jaws == j
    h = sel & hit_q
    print(
        f"  {j:15s} {h.sum():5d} / {sel.sum():5d}   {it_q[h].mean():5.2f}   {int(it_q[sel].max()):3d}"
    )
