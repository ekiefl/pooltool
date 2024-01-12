#! /usr/bin/env python

import importlib.util
import linecache
import os
import pickle
import tracemalloc

import pandas as pd
import pprofile
from numba import jit
from panda3d.core import Filename

import pooltool.constants as c


class classproperty(property):
    """Decorator for a class property

    Examples:
        >>> from pooltool.utils import classproperty
        >>> class Test:
        >>>     @classproperty
        >>>     def foo(cls):
        >>>         return cls.__name__
    """

    def __get__(self, owner_self, owner_cls):
        return self.fget(owner_cls)


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

    print("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        print(
            "#%s: %s:%s: %.1f KiB" % (index, filename, frame.lineno, stat.size / 1024)
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s" % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    print("Total allocated size: %.1f KiB" % (total / 1024))


def memory_usage_to_dataframe(snapshot, key_type="lineno", limit=10):
    """
    Convert memory usage data from tracemalloc into a pandas DataFrame.

    Args:
    snapshot (tracemalloc.Snapshot): The snapshot of memory allocation.
    key_type (str): The type of key to categorize memory usage.
    limit (int): The number of top entries to include.

    Returns:
    pd.DataFrame: DataFrame containing memory usage information.
    """

    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    # Initialize lists to store data
    ranks = []
    files = []
    line_numbers = []
    memory_usages = []
    code_snippets = []
    categories = []

    # Process top statistics
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        line = linecache.getline(frame.filename, frame.lineno).strip()

        ranks.append(index)
        files.append(filename)
        line_numbers.append(frame.lineno)
        memory_usages.append(stat.size / 1024)
        code_snippets.append(line)
        categories.append("Top")

    # Process other statistics
    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        ranks.append(None)
        files.append(None)
        line_numbers.append(None)
        memory_usages.append(size / 1024)
        code_snippets.append(None)
        categories.append("Other")

    # Create DataFrame
    data = {
        "Rank": ranks,
        "File": files,
        "Line Number": line_numbers,
        "Memory Usage (KiB)": memory_usages,
        "Code Snippet": code_snippets,
        "Category": categories,
    }

    return pd.DataFrame(data)


def human_readable_file_size(nbytes):
    suffixes = ["B", "KB", "MB", "GB", "TB", "PB"]
    if nbytes == 0:
        return "0 B"
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    f = ("%.2f" % nbytes).rstrip("0").rstrip(".")
    return "%s %s" % (f, suffixes[i])


@jit(nopython=True, cache=c.use_numba_cache)
def orientation(p, q, r):
    """Find the orientation of an ordered triplet (p, q, r)

    See https://www.geeksforgeeks.org/orientation-3-ordered-points/amp/

    Notes
    =====
    - 3D points may be passed but only the x and y components are used

    Returns
    =======
    output : int
        0 : Collinear points, 1 : Clockwise points, 2 : Counterclockwise
    """
    val = ((q[1] - p[1]) * (r[0] - q[0])) - ((q[0] - p[0]) * (r[1] - q[1]))
    if val > 0:
        # Clockwise orientation
        return 1
    elif val < 0:
        # Counterclockwise orientation
        return 2
    else:
        # Collinear orientation
        return 0


class PProfile(pprofile.Profile):
    """Small wrapper for pprofile that accepts a filepath and outputs cachegrind file"""

    def __init__(self, path, run=True):
        self.run = run
        self.path = path
        pprofile.Profile.__init__(self)

    def __enter__(self):
        if self.run:
            return pprofile.Profile.__enter__(self)
        else:
            return self

    def __exit__(self, *args):
        if self.run:
            pprofile.Profile.__exit__(self, *args)
            self.dump_stats(self.path)
