"""Utilities"""

import datetime
import importlib.util
import linecache
import os
import pickle
import re
import sys
import textwrap
import time
import tracemalloc
from collections import OrderedDict

from panda3d.core import Filename

ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
non_ascii_escape = re.compile(r"[^\x00-\x7F]+")


def CLEAR(line):
    return ansi_escape.sub("", non_ascii_escape.sub("", line.strip()))


tty_colors = {
    "gray": {"normal": "\033[1;30m%s\033[1m", "bold": "\033[0;30m%s\033[0m"},
    "red": {"normal": "\033[1;31m%s\033[1m", "bold": "\033[0;31m%s\033[0m"},
    "green": {"normal": "\033[1;32m%s\033[1m", "bold": "\033[0;32m%s\033[0m"},
    "yellow": {"normal": "\033[1;33m%s\033[1m", "bold": "\033[0;33m%s\033[0m"},
    "blue": {"normal": "\033[1;34m%s\033[1m", "bold": "\033[0;34m%s\033[0m"},
    "magenta": {"normal": "\033[1;35m%s\033[1m", "bold": "\033[0;35m%s\033[0m"},
    "cyan": {"normal": "\033[1;36m%s\033[1m", "bold": "\033[0;36m%s\033[0m"},
    "white": {"normal": "\033[1;37m%s\033[1m", "bold": "\033[0;37m%s\033[0m"},
    "crimson": {"normal": "\033[1;38m%s\033[1m", "bold": "\033[0;38m%s\033[0m"},
}


def color_text(text, color="crimson", weight="bold"):
    if sys.stdout.isatty():
        return tty_colors[color][weight] % text
    else:
        return text


def remove_spaces(text):
    while True:
        if text.find("  ") > -1:
            text = text.replace("  ", " ")
        else:
            break

    return text


def get_date():
    return time.strftime("%d %b %y %H:%M:%S", time.localtime())


def pretty_print(n):
    """Pretty print function for very big integers"""
    if not isinstance(n, int):
        return n

    ret = []
    n = str(n)
    for i in range(len(n) - 1, -1, -1):
        ret.append(n[i])
        if (len(n) - i) % 3 == 0:
            ret.append(",")
    ret.reverse()
    return "".join(ret[1:]) if ret[0] == "," else "".join(ret)


class Run:
    def __init__(self, verbose=True, width=45):
        self.info_dict = {}
        self.verbose = verbose
        self.width = width

        self.single_line_prefixes = {1: "* ", 2: "    - ", 3: "        > "}

    def write(self, line, quiet=False, overwrite_verbose=False):
        if (self.verbose and not quiet) or overwrite_verbose:
            try:
                sys.stderr.write(line)
            except Exception:
                sys.stderr.write(line.encode("utf-8"))

    def info(
        self,
        key,
        value,
        quiet=False,
        display_only=False,
        overwrite_verbose=False,
        nl_before=0,
        nl_after=0,
        lc="cyan",
        mc="yellow",
        progress=None,
    ):
        if not display_only:
            self.info_dict[key] = value

        if isinstance(value, bool):
            pass
        elif isinstance(value, str):
            value = remove_spaces(value)
        elif isinstance(value, int):
            value = pretty_print(value)

        label = key

        info_line = "{}{} {}: {}\n{}".format(
            "\n" * nl_before,
            color_text(label, lc),
            "." * (self.width - len(label)),
            color_text(str(value), mc),
            "\n" * nl_after,
        )

        if progress:
            progress.clear()
            self.write(info_line, overwrite_verbose=False, quiet=quiet)
            progress.update(progress.msg)
        else:
            self.write(info_line, quiet=quiet, overwrite_verbose=overwrite_verbose)

    def info_single(
        self,
        message,
        overwrite_verbose=False,
        mc="yellow",
        nl_before=0,
        nl_after=0,
        cut_after=80,
        level=1,
        progress=None,
    ):
        if isinstance(message, str):
            message = remove_spaces(message)

        if level not in self.single_line_prefixes:
            raise Exception(
                f"the `info_single` function does not know how to deal with a level "
                f"of {level} :/"
            )

        if cut_after:
            message_line = color_text(
                f"{self.single_line_prefixes[level]}{textwrap.fill(str(message), cut_after)}\n",
                mc,
            )
        else:
            message_line = color_text(
                f"{self.single_line_prefixes[level]}{str(message)}\n", mc
            )

        message_line = ("\n" * nl_before) + message_line + ("\n" * nl_after)

        if progress:
            progress.clear()
            self.write(message_line, overwrite_verbose=overwrite_verbose)
            progress.update(progress.msg)
        else:
            self.write(message_line, overwrite_verbose=overwrite_verbose)

    def warning(
        self,
        message,
        header="WARNING",
        lc="red",
        raw=False,
        overwrite_verbose=False,
        nl_before=0,
        nl_after=0,
    ):
        if isinstance(message, str):
            message = remove_spaces(message)

        message_line = ""
        header_line = color_text(
            "{}\n{}\n{}\n".format(("\n" * nl_before), header, "=" * (self.width + 2)),
            lc,
        )
        if raw:
            message_line = color_text("{}\n\n{}".format((message), "\n" * nl_after), lc)
        else:
            message_line = color_text(
                "{}\n\n{}".format(textwrap.fill(str(message), 80), "\n" * nl_after), lc
            )

        self.write(
            (header_line + message_line) if message else header_line,
            overwrite_verbose=overwrite_verbose,
        )


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
        self.run.single_line_prefixes = {0: "✓ ", 1: "✖ "}

        self.quiet = quiet
        self.suppress_first = suppress_first
        self.sc, self.fc = sc, fc
        self.s_msg, self.f_msg = success_msg, failure_msg

        self.s_msg = self.s_msg if self.s_msg else "Code finished after "
        self.f_msg = self.f_msg if self.f_msg else "Code encountered error after "

    def __enter__(self):
        self.timer = Timer()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.time = self.timer.timedelta_to_checkpoint(self.timer.timestamp())

        if self.quiet or self.time <= datetime.timedelta(seconds=self.suppress_first):
            return

        return_code = 0 if exception_type is None else 1

        msg, color = (self.s_msg, self.sc) if not return_code else (self.f_msg, self.fc)

        assert msg is not None

        self.run.info_single(
            msg + str(self.time), nl_before=1, mc=color, level=return_code
        )


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
