"""Utilities"""

import datetime
import importlib.util
import linecache
import os
import pickle
import time
import tracemalloc
from collections import OrderedDict

from panda3d.core import Filename
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class Run:
    def __init__(self):
        self.console = Console(stderr=True)

    def info(self, message, style="cyan"):
        text = Text(f"* {message}", style=style)
        self.console.print(text)

    def table(self, data, title="Info", border_style="cyan"):
        """Display information as a formatted table inside a panel"""
        table = Table(expand=True)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white", ratio=1)

        for key, value in data.items():
            if isinstance(value, int):
                value = f"{value:,}"
            table.add_row(key, str(value))

        panel = Panel(
            table, title=title, title_align="left", border_style=border_style, width=80
        )
        self.console.print(panel)


class Timer:
    """Manages ordered dictionary, key is checkpoint name and value is a timestamp.

    Examples
    ========

    >>> from pooltool.utils import Timer
    >>> import time
    >>> t = Timer(); time.sleep(1)
    >>> t.make_checkpoint('checkpoint_name'); time.sleep(1)
    >>> timedelta = t.timedelta_to_checkpoint(timestamp=t.timestamp(), checkpoint_key='checkpoint_name')
    >>> print(t.format_time(timedelta, fmt = '{days} days, {hours} hours, {seconds} seconds', zero_padding=0))
    >>> print(t.time_elapsed())
    0 days, 0 hours, 1 seconds
    00:00:02

    >>> t = Timer(3) # 3 checkpoints expected until completion
    >>> for _ in range(3):
    >>>     time.sleep(1); t.make_checkpoint()
    >>>     print('complete: %s' % t.complete)
    >>>     print(t.eta(fmt='ETA: {seconds} seconds'))
    complete: False
    ETA: 02 seconds
    complete: False
    ETA: 01 seconds
    complete: True
    ETA: 00 seconds
    """

    def __init__(
        self, required_completion_score=None, initial_checkpoint_key=0, score=0
    ):
        self.timer_start = self.timestamp()
        self.initial_checkpoint_key = initial_checkpoint_key
        self.last_checkpoint_key = self.initial_checkpoint_key
        self.checkpoints = OrderedDict([(initial_checkpoint_key, self.timer_start)])
        self.num_checkpoints = 0

        self.required_completion_score = required_completion_score
        self.score = score
        self.complete = False

        self.last_eta = None
        self.last_eta_timestamp = self.timer_start

        self.scores = {self.initial_checkpoint_key: self.score}

    def timestamp(self):
        return datetime.datetime.fromtimestamp(time.time())

    def timedelta_to_checkpoint(self, timestamp, checkpoint_key=None):
        if not checkpoint_key:
            checkpoint_key = self.initial_checkpoint_key
        timedelta = timestamp - self.checkpoints[checkpoint_key]
        return timedelta

    def make_checkpoint(self, checkpoint_key=None, increment_to=None):
        if not checkpoint_key:
            checkpoint_key = self.num_checkpoints + 1

        if checkpoint_key in self.checkpoints:
            raise Exception(
                f"Timer.make_checkpoint :: {str(checkpoint_key)} already exists as a checkpoint key. "
                "All keys must be unique"
            )

        checkpoint = self.timestamp()

        self.checkpoints[checkpoint_key] = checkpoint
        self.last_checkpoint_key = checkpoint_key

        self.num_checkpoints += 1

        if increment_to:
            self.score = increment_to
        else:
            self.score += 1

        self.scores[checkpoint_key] = self.score

        if (
            self.required_completion_score
            and self.score >= self.required_completion_score
        ):
            self.complete = True

        return checkpoint

    def calculate_time_remaining(self, infinite_default="∞:∞:∞"):
        if self.complete:
            return datetime.timedelta(seconds=0)
        if not self.required_completion_score:
            return None
        if not self.score:
            return infinite_default

        time_elapsed = self.checkpoints[self.last_checkpoint_key] - self.checkpoints[0]
        fraction_completed = self.score / self.required_completion_score
        time_remaining_estimate = time_elapsed / fraction_completed - time_elapsed

        return time_remaining_estimate

    def eta(self, fmt=None, zero_padding=0):
        # Calling format_time hundreds or thousands of times per second is expensive.
        # Therefore if eta was called within the last half second, the previous ETA is
        # returned without further calculation.
        eta_timestamp = self.timestamp()
        if (
            eta_timestamp - self.last_eta_timestamp < datetime.timedelta(seconds=0.5)
            and self.num_checkpoints > 0
        ):
            return self.last_eta

        eta = self.calculate_time_remaining()
        eta = (
            self.format_time(eta, fmt, zero_padding)
            if isinstance(eta, datetime.timedelta)
            else str(eta)
        )

        self.last_eta = eta
        self.last_eta_timestamp = eta_timestamp

        return eta

    def time_elapsed(self, fmt=None):
        return self.format_time(
            self.timedelta_to_checkpoint(self.timestamp(), checkpoint_key=0), fmt=fmt
        )

    def time_elapsed_precise(self):
        return self.timedelta_to_checkpoint(self.timestamp(), checkpoint_key=0)

    def format_time(
        self,
        timedelta,
        fmt: str | None = "{hours}:{minutes}:{seconds}",
        zero_padding: int = 2,
    ):
        """Formats time

        Examples of `fmt`. Suppose the timedelta is seconds = 1, minutes = 1, hours = 1.

            {hours}h {minutes}m {seconds}s  --> 01h 01m 01s
            {seconds} seconds               --> 3661 seconds
            {weeks} weeks {minutes} minutes --> 0 weeks 61 minutes
            {hours}h {seconds}s             --> 1h 61s
        """

        unit_hierarchy = ["seconds", "minutes", "hours", "days", "weeks"]
        unit_denominations = {
            "weeks": 7,
            "days": 24,
            "hours": 60,
            "minutes": 60,
            "seconds": 1,
        }

        if fmt is None:
            # use the highest two non-zero units, e.g. if it is 7200s, use
            # {hours}h{minutes}m
            seconds = int(timedelta.total_seconds())
            if seconds < 60:
                fmt = "{seconds}s"
            else:
                m = 1
                for i, unit in enumerate(unit_hierarchy):
                    if not seconds // (m * unit_denominations[unit]) >= 1:
                        fmt = f"{{{unit_hierarchy[i - 1]}}}{unit_hierarchy[i - 1][0]}{{{unit_hierarchy[i - 2]}}}{unit_hierarchy[i - 2][0]}"
                        break
                    elif unit == unit_hierarchy[-1]:
                        fmt = f"{{{unit_hierarchy[i]}}}{unit_hierarchy[i][0]}{{{unit_hierarchy[i - 1]}}}{unit_hierarchy[i - 1][0]}"
                        break
                    else:
                        m *= unit_denominations[unit]

        assert isinstance(fmt, str)

        # parse units present in fmt
        format_order = []
        for i, x in enumerate(fmt):
            if x == "{":
                for j, k in enumerate(fmt[i:]):
                    if k == "}":
                        unit = fmt[i + 1 : i + j]
                        format_order.append(unit)
                        break

        if not format_order:
            raise Exception(
                f"Timer.format_time :: fmt = '{fmt}' contains no time units."
            )

        for unit in format_order:
            if unit not in unit_hierarchy:
                raise Exception(
                    "Timer.format_time :: '{}' is not a valid unit. Use any of {}.".format(
                        unit, ", ".join(unit_hierarchy)
                    )
                )

        # calculate the value for each unit (e.g. 'seconds', 'days', etc) found in fmt
        format_values_dict = {}
        smallest_unit = unit_hierarchy[
            [unit in format_order for unit in unit_hierarchy].index(True)
        ]
        units_less_than_or_equal_to_smallest_unit = unit_hierarchy[::-1][
            unit_hierarchy[::-1].index(smallest_unit) :
        ]
        seconds_in_base_unit = 1
        for a in [
            v
            for k, v in unit_denominations.items()
            if k in units_less_than_or_equal_to_smallest_unit
        ]:
            seconds_in_base_unit *= a
        r = int(timedelta.total_seconds()) // seconds_in_base_unit

        for i, lower_unit in enumerate(unit_hierarchy):
            if lower_unit in format_order:
                m = 1
                for upper_unit in unit_hierarchy[i + 1 :]:
                    m *= unit_denominations[upper_unit]
                    if upper_unit in format_order:
                        (
                            format_values_dict[upper_unit],
                            format_values_dict[lower_unit],
                        ) = divmod(r, m)
                        break
                else:
                    format_values_dict[lower_unit] = r
                    break
                r = format_values_dict[upper_unit]

        format_values = [format_values_dict[unit] for unit in format_order]

        style_str = "0" + str(zero_padding) if zero_padding else ""
        for unit in format_order:
            fmt = fmt.replace(f"{{{unit}}}", "%" + f"{style_str}" + "d")
        formatted_time = fmt % (*[format_value for format_value in format_values],)

        return formatted_time

    @classmethod
    def factory(cls):
        return cls()


class TimeCode:
    """Time a block of code.

    This context manager times blocks of code, and calls run.info afterwards to report
    the time (unless quiet = True).

    Parameters
    ==========
    sc: 'green'
        run info color with no runtime error
    success_msg: None
        If None, it is set to 'Code ran succesfully in'
    fc: 'green'
        run info color with runtime error
    failure_msg: None
        If None, it is set to 'Code failed within'
    run: Run()
        Provide a pre-existing Run instance if you want
    quiet: False,
        If True, run.info is not called and datetime object is stored
        as `time` (see examples)
    suppress_first: 0,
        Supress output if code finishes within this many seconds.

    Examples
    ========

    >>> import time
    >>> import pooltool.utils as utils
    >>> # EXAMPLE 1
    >>> with utils.TimeCode() as t:
    >>>     time.sleep(5)
    ✓ Code finished successfully after 05s

    >>> # EXAMPLE 2
    >>> with utils.TimeCode() as t:
    >>>     time.sleep(5)
    >>>     print(asdf) # undefined variable
    ✖ Code encountered error after 05s

    >>> # EXAMPLE 3
    >>> with utils.TimeCode(quiet=True) as t:
    >>>     time.sleep(5)
    >>> print(t.time)
    0:00:05.000477
    """

    def __init__(
        self,
        success_msg=None,
        sc="green",
        fc="red",
        failure_msg=None,
        run=None,
        quiet=False,
        suppress_first=0,
    ):
        self.run = run if run is not None else Run()

        self.quiet = quiet
        self.suppress_first = suppress_first
        self.s_msg = success_msg if success_msg else "Code finished after "
        self.f_msg = failure_msg if failure_msg else "Code encountered error after "

    def __enter__(self):
        self.timer = Timer()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.time = self.timer.timedelta_to_checkpoint(self.timer.timestamp())

        if self.quiet or self.time <= datetime.timedelta(seconds=self.suppress_first):
            return

        message = f"{self.s_msg if exception_type is None else self.f_msg}{self.time}"

        if exception_type is None:
            self.run.info(message)
        else:
            self.run.info(message, style="red")


class classproperty(property):
    """Decorator for a class property

    Examples:
        >>> from pooltool.utils import classproperty
        >>> class Test:
        >>>     @classproperty
        >>>     def foo(cls):
        >>>         return cls.__name__
    """

    def __get__(self, owner_self, owner_cls):  # type: ignore
        return self.fget(owner_cls)  # type: ignore


def save_pickle(x, path):
    """Save an object `x` to filepath `path`"""
    with open(path, "wb") as f:
        pickle.dump(x, f)


def load_pickle(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def is_pickleable(obj):
    """https://stackoverflow.com/a/53398070"""
    try:
        pickle.dumps(obj)
    except pickle.PicklingError:
        return False
    except TypeError:
        return False
    return True


def panda_path(path) -> str:
    panda_path = Filename.fromOsSpecific(str(path))
    panda_path.makeTrueCase()
    return str(panda_path)


def get_total_memory_usage(keep_raw=False):
    """Get the total memory, including children

    Parameters
    ==========
    keep_raw : bool, False
        A human readable format is returned, e.g. "1.41 GB". If keep_raw, the raw number
        is returned, e.g. 1515601920
    """
    if importlib.util.find_spec("psutil") is None:
        # psutil does not exist in this distribution
        return "??"
    else:
        import psutil

    current_process = psutil.Process(os.getpid())
    mem = current_process.memory_info().rss
    for child in current_process.children(recursive=True):
        try:
            mem += child.memory_info().rss
        except Exception:
            pass

    return mem if keep_raw else human_readable_file_size(mem)


def display_top_memory_usage(snapshot, key_type="lineno", limit=10):
    """A pretty-print for the tracemalloc memory usage module

    Modified from https://docs.python.org/3/library/tracemalloc.html

    Examples
    ========
    >>> import tracemalloc
    >>> import pooltool.utils as utils
    >>> tracemalloc.start()
    >>> snap = tracemalloc.take_snapshot
    >>> utils.display_top_memory_usage(snap)
    Top 10 lines
    #1: anvio/bamops.py:160: 4671.3 KiB
        constants.cigar_consumption,
    #2: anvio/bamops.py:96: 2571.6 KiB
        self.cigartuples = np.array(read.cigartuples)
    #3: python3.6/linecache.py:137: 1100.0 KiB
        lines = fp.readlines()
    #4: <frozen importlib._bootstrap_external>:487: 961.4 KiB
    #5: typing/templates.py:627: 334.3 KiB
        return type(base)(name, (base,), dct)
    #6: typing/templates.py:923: 315.7 KiB
        class Template(cls):
    #7: python3.6/_weakrefset.py:84: 225.2 KiB
        self.data.add(ref(item, self._remove))
    #8: targets/npyimpl.py:411: 143.2 KiB
        class _KernelImpl(_Kernel):
    #9: _vendor/pyparsing.py:3349: 139.7 KiB
        self.errmsg = "Expected " + _ustr(self)
    #10: typing/context.py:456: 105.1 KiB
        def on_disposal(wr, pop=self._globals.pop):
    3212 other: 4611.9 KiB
    Total allocated size: 15179.4 KiB
    """

    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print(f"Top {limit} lines")
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print(f"#{index}: {filename}:{frame.lineno}: {stat.size / 1024:.1f} KiB")
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print(f"    {line}")

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print(f"{len(other)} other: {size / 1024:.1f} KiB")
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def human_readable_file_size(nbytes):
    suffixes = ["B", "KB", "MB", "GB", "TB", "PB"]
    if nbytes == 0:
        return "0 B"
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    f = (f"{nbytes:.2f}").rstrip("0").rstrip(".")
    return f"{f} {suffixes[i]}"
