"""Utilities"""

import datetime
import importlib.util
import linecache
import os
import pickle
import time
import tracemalloc

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
    """Simple timer for measuring elapsed time.

    Examples:

        >>> from pooltool.utils import Timer
        >>> import time
        >>> t = Timer()
        >>> time.sleep(1)
        >>> print(t.time_elapsed())
        00:00:01
    """

    def __init__(self):
        self.timer_start = self.timestamp()

    def timestamp(self):
        return datetime.datetime.fromtimestamp(time.time())

    def timedelta_to_checkpoint(self, timestamp):
        return timestamp - self.timer_start

    def time_elapsed(self):
        return self.format_time(self.timedelta_to_checkpoint(self.timestamp()))

    def format_time(self, timedelta):
        total_seconds = int(timedelta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @classmethod
    def factory(cls):
        return cls()


class TimeCode:
    """Time a block of code.

    This context manager times blocks of code, and calls run.info afterwards to report
    the time (unless quiet = True).

    Attributes:
        success_msg: None
            If None, it is set to 'Code ran succesfully in'
        failure_msg: None
            If None, it is set to 'Code failed within'
        run: Run()
            Provide a pre-existing Run instance if you want
        quiet: False,
            If True, run.info is not called and datetime object is stored
            as `time` (see examples)
        suppress_first: 0,
            Supress output if code finishes within this many seconds.

    Examples:

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
