#!/usr/bin/env python

import attrs
import click

from pooltool.ani.animate import Game, ShowBaseConfig


@click.command()
@click.option("--monitor", is_flag=True, help="Spit out per-frame info about game")
def run(monitor):
    config = attrs.evolve(ShowBaseConfig.default(), monitor=monitor)

    play = Game(config)
    play.start()


if __name__ == "__main__":
    run()
