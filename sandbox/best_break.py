#! /usr/bin/env python
"""This illustrates how shots can be visualized multiple times in a single script"""

import multiprocessing
from collections import Counter
from pathlib import Path

import numpy as np

import pooltool as pt
import pooltool.events as e

best_break_path = Path(__file__).parent / "best_break.pkl"
best_break_stats = Path(__file__).parent / "best_break_stats.pkl"

spacing_factor = 1e-3
get_cue_pos = lambda cue, table: [
    cue.R + np.random.rand() * (table.w - 2 * cue.R),
    table.l / 4,
    cue.R,
]

run = pt.terminal.Run()


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


def process_shots(shots, stats, break_count, session_best, best_break, interface):
    for shot_dict in shots:
        shot = pt.System(d=shot_dict)

        break_count += 1

        if len(shot.events.filter_ball(shot.balls["cue"]).filter_type("ball-pocket")):
            # Cue ball was potted. Illegal shot
            stats["scratch"] += 1

        else:
            # Count how many balls were potted, ignoring cue ball
            numbered_balls = [ball for ball in shot.balls.values() if ball.id != "cue"]
            balls_potted = len(
                shot.events.filter_type("ball-pocket").filter_ball(numbered_balls)
            )
            stats[balls_potted] += 1

            if balls_potted > session_best:
                session_best = balls_potted

            if balls_potted > best_break:
                shot.continuize(dt=0.003)
                shot.save(Path(__file__).parent / "best_break.pkl")
                best_break = balls_potted
                if not args.no_viz:
                    interface.show(shot, f"{best_break} balls potted")

    pt.utils.save_pickle(stats, best_break_stats)

    return stats, break_count, session_best, best_break


def worker(output_queue):
    while True:
        # setup table, cue, and cue ball
        table = pt.PocketTable(model_name="7_foot")
        balls = pt.get_nine_ball_rack(
            table, spacing_factor=spacing_factor, ordered=True
        )
        balls["cue"].rvw[0] = get_cue_pos(balls["cue"], table)
        cue = pt.Cue(cueing_ball=balls["cue"])

        # Aim at the head ball then strike the cue ball
        cue.aim_at_ball(balls["1"])
        cue.strike(V0=8)

        # Evolve the shot
        shot = pt.System(cue=cue, table=table, balls=balls)
        try:
            shot.simulate(continuize=False, quiet=True)
        except Exception as e:
            continue

        if len(shot.events.filter_ball(balls["cue"]).filter_type("ball-pocket")):
            # Cue ball was potted. Illegal shot
            output_queue.put(shot.as_dict())
            continue

        output_queue.put(shot.as_dict())

    # Code never reaches here because worker is terminated by main thread
    return


def print_stats(stats, run):
    run.warning("", header="Cumulative stats", lc="green")
    run.info(f"Num total breaks", sum(stats.values()))
    run.info(f"Num scratch breaks", stats["scratch"])
    for k in sorted([x for x in list(stats.keys()) if x != "scratch"]):
        if k == "scratch":
            continue
        run.info(f"Num breaks with {k} balls potted", stats[k])
    print()


def main(args):
    if args.clear:
        clear()

    interface = pt.ShotViewer() if not args.no_viz else None

    shot, stats = load_prev_data()

    session_best = 0
    best_break = max([x for x in list(stats.keys()) if x != "scratch"])
    break_count = sum(list(stats.values())) + 1

    print_stats(stats, run)

    if not args.no_viz and shot is not None:
        interface.show(
            pt.System(path=best_break_path),
            f"The best break so far ({best_break} balls)",
        )

    shots = []
    buffer_size = 200
    queue_size = args.threads * 5

    manager = multiprocessing.Manager()
    output_queue = manager.Queue(queue_size)

    processes = []
    for _ in range(args.threads):
        processes.append(multiprocessing.Process(target=worker, args=(output_queue,)))

    for proc in processes:
        proc.start()

    while True:
        try:
            shot = output_queue.get()
            shots.append(shot)

            if buffer_size > 0 and len(shots) % buffer_size == 0:
                stats, break_count, session_best, best_break = process_shots(
                    shots, stats, break_count, session_best, best_break, interface
                )
                print_stats(stats, run)
                shots = []

        except KeyboardInterrupt:
            run.info_single("Cancelling upon user request...", nl_before=1, nl_after=1)
            break

        except Exception as worker_error:
            for proc in processes:
                proc.terminate()
            run.info_single("Thread interrupted. Ending...", nl_before=1, nl_after=1)
            break

    for proc in processes:
        proc.terminate()

    shots = []


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser("A good old 9-ball break")
    ap.add_argument(
        "--no-viz", action="store_true", help="If set, the break will not be visualized"
    )
    ap.add_argument(
        "--clear", action="store_true", help="Delete historical best breaks"
    )
    ap.add_argument(
        "-T", "--threads", default=4, type=int, help="How many threads should be used?"
    )

    args = ap.parse_args()
    main(args)
