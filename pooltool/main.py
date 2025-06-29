#!/usr/bin/env python

import sys

import attrs
import click

from pooltool.ani.animate import Game, ShowBaseConfig
from pooltool.error import ConfigError, SimulateError, StrokeError


@click.command()
@click.option("--monitor", is_flag=True, help="Spit out per-frame info about game")
def run(monitor):
    config = attrs.evolve(ShowBaseConfig.default(), monitor=monitor)

    play = Game(config)
    play.start()


if __name__ == "__main__":
    try:
        run()
    except ConfigError as e:
        print(e)
        sys.exit(1)
    except StrokeError as e:
        print(e)
        sys.exit(1)
    except SimulateError as e:
        print(e)
        sys.exit(1)
