#! /usr/bin/env python
"""This illustrates how shots can be visualized multiple times in a single script"""

import pooltool as pt
import pooltool.events as e

import numpy as np

from pathlib import Path
from collections import Counter

best_break_path = Path(__file__).parent / 'best_break.pkl'
best_break_stats = Path(__file__).parent / 'best_break_stats.pkl'

spacing_factor = 1e-3
run = pt.terminal.Run()
get_cue_pos = lambda cue, table: [cue.R + np.random.rand()*(table.w - 2*cue.R), table.l/4, cue.R]

def clear():
    if best_break_path.exists():
        best_break_path.unlink()
    if best_break_stats.exists():
        best_break_stats.unlink()


def load_prev_data():
    if best_break_path.exists():
        shot = pt.System(path=best_break_path)
    else:
        shot = None

    if best_break_stats.exists():
        stats = pt.utils.load_pickle(best_break_stats)
    else:
        stats = Counter({0: 0})

    return shot, stats


def main(args):
    if args.clear:
        clear()
    if not args.no_viz:
        interface = pt.ShotViewer()

    shot, stats = load_prev_data()

    session_best = 0
    best_break = max([x for x in list(stats.keys()) if x != 'scratch'])
    break_count = sum(list(stats.values())) + 1

    run.warning('', header="Cumulative stats", lc='green')
    run.info(f"Num scratch breaks", stats['scratch'])
    for k in sorted([x for x in list(stats.keys()) if x != 'scratch']):
        if k == 'scratch':
            continue
        run.info(f"Num breaks with {k} balls potted", stats[k])

    if not args.no_viz and shot is not None:
        interface.show(pt.System(path=best_break_path), f"The best break so far ({best_break} balls)")

    while True:
        # setup table, cue, and cue ball
        table = pt.PocketTable(model_name='7_foot')
        balls = pt.get_nine_ball_rack(table, spacing_factor=spacing_factor, ordered=True)
        balls['cue'].rvw[0] = get_cue_pos(balls['cue'], table)
        cue = pt.Cue(cueing_ball=balls['cue'])

        # Aim at the head ball then strike the cue ball
        cue.aim_at_ball(balls['1'])
        cue.strike(V0=8)

        # Evolve the shot
        shot = pt.System(cue=cue, table=table, balls=balls)
        try:
            shot.simulate(name=f"Break {break_count}", continuize=False, quiet=False)
            break_count += 1
        except KeyboardInterrupt:
            shot.progress.end()
            break
        except:
            shot.progress.end()
            shot.run.info("Shot calculation failed", ":(")
            continue

        if len(shot.events.filter_ball(balls['cue']).filter_type('ball-pocket')):
            # Cue ball was potted. Illegal shot
            stats['scratch'] += 1
            continue

        # Count how many balls were potted, ignoring cue ball
        numbered_balls = [ball for ball in balls.values() if ball.id != 'cue']
        balls_potted = len(shot.events.filter_type('ball-pocket').filter_ball(numbered_balls))
        stats[balls_potted] += 1

        shot.run.info("All time best", best_break)
        shot.run.info("Session best", session_best)
        shot.run.info("Balls potted", balls_potted)

        if balls_potted > session_best:
            session_best = balls_potted

        if balls_potted > best_break:
            shot.continuize(dt=0.003)
            shot.save(Path(__file__).parent / 'best_break.pkl')
            best_break = balls_potted
            if not args.no_viz:
                interface.show(shot)

    pt.utils.save_pickle(stats, best_break_stats)


if __name__ == '__main__':
    import argparse

    ap = argparse.ArgumentParser('A good old 9-ball break')
    ap.add_argument('--no-viz', action='store_true', help="If set, the break will not be visualized")
    ap.add_argument('--clear', action='store_true', help="Delete historical best breaks")

    args = ap.parse_args()
    main(args)
