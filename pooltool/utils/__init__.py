"""Utilities"""

from __future__ import annotations

import datetime
import os
import time
from pathlib import Path
from typing import Any

from panda3d.core import Filename
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class Run:
    def __init__(self):
        self.console = Console(stderr=True)

    def info(self, message: str, style: str = "cyan"):
        text = Text(f"* {message}", style=style)
        self.console.print(text)

    def table(
        self, data: dict[Any, Any], title: str = "Info", border_style: str = "cyan"
    ):
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

    def timestamp(self) -> datetime.datetime:
        return datetime.datetime.fromtimestamp(time.time())

    def timedelta_to_checkpoint(
        self, timestamp: datetime.datetime
    ) -> datetime.timedelta:
        return timestamp - self.timer_start

    def time_elapsed(self) -> str:
        return self.format_time(self.timedelta_to_checkpoint(self.timestamp()))

    def format_time(self, timedelta: datetime.timedelta) -> str:
        total_seconds = int(timedelta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    @classmethod
    def factory(cls) -> Timer:
        return cls()


class TimeCode:
    """Time a block of code.

    This context manager times blocks of code and optionally reports the elapsed time.

    Args:
        quiet: If True, no output is printed. Access timing via the `time` attribute.
        message: Custom message prefix for output. Defaults to "Code finished after".

    Examples:

        >>> import time
        >>> import pooltool.utils as utils
        >>> # Basic usage with automatic reporting
        >>> with utils.TimeCode() as t:
        >>>     time.sleep(1)
        Code finished after 0:00:01

        >>> # Silent timing for benchmarking
        >>> with utils.TimeCode(quiet=True) as t:
        >>>     time.sleep(1)
        >>> print(t.time.total_seconds())
        1.0

        >>> # Custom message
        >>> with utils.TimeCode(message="Operation completed in") as t:
        >>>     time.sleep(1)
        Operation completed in 0:00:01
    """

    def __init__(self, quiet: bool = False, message: str | None = None):
        self.quiet: bool = quiet
        self.message: str = message or "Code finished after"

        self.start_time: float
        self.time: datetime.timedelta

        self._console = Console(stderr=True)

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.time = datetime.timedelta(seconds=time.time() - self.start_time)

        if not self.quiet:
            style = "red" if exception_type else "green"
            if exception_type:
                message = f"Code encountered error after {self.time}"
            else:
                message = f"{self.message} {self.time}"
            self._console.print(message, style=style)


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


def panda_path(path: Path | str) -> str:
    panda_path = Filename.fromOsSpecific(str(path))
    panda_path.makeTrueCase()
    return str(panda_path)


def get_total_memory_usage() -> int:
    """Get the total memory, including children."""
    import psutil

    current_process = psutil.Process(os.getpid())
    mem = current_process.memory_info().rss
    for child in current_process.children(recursive=True):
        try:
            mem += child.memory_info().rss
        except Exception:
            pass

    return mem


def human_readable_file_size(nbytes: float) -> str:
    suffixes = ["B", "KB", "MB", "GB", "TB", "PB"]
    if nbytes == 0:
        return "0 B"
    i = 0
    while nbytes >= 1024 and i < len(suffixes) - 1:
        nbytes /= 1024.0
        i += 1
    f = (f"{nbytes:.2f}").rstrip("0").rstrip(".")
    return f"{f} {suffixes[i]}"
