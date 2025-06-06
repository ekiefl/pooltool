#! /usr/bin/env python
"""Relations with the console output, Progress and Run classes

Taken from https://github.com/merenlab/anvio/blob/master/anvio/terminal.py"""

from __future__ import annotations

import datetime
import importlib.util
import os
import re
import struct
import sys
import textwrap
import time
from collections import OrderedDict


def get_color_objects():
    """Get objects for coloring the progress bar

    `colored` is a module used for coloring the progress bar, however this module does
    not create wheels for all platform tags.  Therefore not all pooltool distributions
    will have colored. This code imports `colored` if it exists, and provides colorless
    functionality if it does not

    Notes
    - Rather than using fore, back, and style, the progress bar should use the
      pooltool.terminal.tty_colors dictionary so that `colored` can be removed as a
      module altogether
    """

    if importlib.util.find_spec("colored") is not None:
        from colored import back, fore, style
    else:

        class NoColored:
            def __getattr__(self, _):
                return ""

        class Fore(NoColored):
            pass

        class Back(NoColored):
            pass

        class Style(NoColored):
            pass

        fore = Fore()
        back = Back()
        style = Style()
    return fore, back, style


fore, back, style = get_color_objects()

# clean garbage garbage:
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


class Progress:
    """A class for managing progress updates in a terminal environment

    This class is designed to display progress information, manage progress steps, and
    calculate ETA for tasks in a command-line interface. It supports dynamic updates of
    progress information and can handle multiple progress instances with unique
    identifiers.

    Attributes:
        pid:
            Unique identifier for the progress instance.
        verbose:
            Determines whether progress updates are displayed. Defaults to True.
        terminal_width:
            Width of the terminal window in characters.
        current:
            Current progress message being displayed.
        progress_total_items:
            Total number of items to track for progress.
        progress_current_item:
            Current progress item count.
        t:
            Timer object to calculate ETA and track progress time.

    Methods:
        new:
            Starts a new progress with a given pid.
        update:
            Updates the progress display with a new message, optionally incrementing the
            progress.
        end:
            Ends the current progress display and optionally stores timing information.
        reset:
            Resets the progress display.
    """

    def __init__(self, verbose=True):
        self.pid = None
        self.verbose = verbose
        self.is_tty = sys.stdout.isatty()
        self.terminal_width: int

        self.get_terminal_width()

        self.current = None

        self.progress_total_items = None
        self.progress_current_item = 0
        self.t = Timer(self.progress_total_items)

        self.LEN = lambda s: len(s.encode("utf-16-le")) // 2

    def get_terminal_width(self):
        # FIXME Program flow here is not clear. When does try fail?
        try:
            self.terminal_width = max(get_terminal_size()[0], 100)
        except Exception:
            self.terminal_width = 100

    def new(self, pid, discard_previous_if_exists=False, progress_total_items=None):
        if self.pid:
            if discard_previous_if_exists:
                self.end()
            else:
                raise Exception(
                    f"Progress.new() can't be called before ending the previous one "
                    f"(Existing: '{self.pid}', Competing: '{pid}')."
                )

        if not self.verbose:
            return

        self.pid = f"{get_date()} {pid}"
        self.get_terminal_width()
        self.current = None
        self.step = None
        self.progress_total_items = progress_total_items
        self.progress_current_item = 0
        self.t = Timer(self.progress_total_items)

    def update_pid(self, pid):
        self.pid = f"{get_date()} {pid}"

    def increment(self, increment_to=None):
        if increment_to:
            self.progress_current_item = increment_to
        else:
            self.progress_current_item += 1

        self.t.make_checkpoint(increment_to=increment_to)

    def write(self, c, dont_update_current=False):
        eta_c = f" ETA: {str(self.t.eta())}" if self.progress_total_items else ""
        surpass = self.terminal_width - self.LEN(c) - self.LEN(eta_c)

        if surpass < 0:
            c = c[0 : -(-surpass + 6)] + " (...)"
        else:
            if not dont_update_current:
                self.current = c

            c += " " * surpass

        c += eta_c

        if self.verbose:
            if self.progress_total_items and self.is_tty:
                p_text = ""
                p_length = self.LEN(p_text)

                end_point = self.LEN(c) - self.LEN(eta_c)
                break_point = round(
                    end_point * self.progress_current_item / self.progress_total_items
                )

                # see a full list of color codes: https://gitlab.com/dslackw/colored
                if p_length >= break_point:
                    sys.stderr.write(
                        getattr(back, "CYAN")
                        + getattr(fore, "BLACK")
                        + c[:break_point]
                        + getattr(back, "GREY_30")
                        + getattr(fore, "WHITE")
                        + c[break_point:end_point]
                        + getattr(back, "CYAN")
                        + getattr(fore, "CYAN")
                        + c[end_point]
                        + getattr(back, "GREY_50")
                        + getattr(fore, "LIGHT_CYAN")
                        + c[end_point:]
                        + getattr(style, "RESET")
                    )
                else:
                    sys.stderr.write(
                        getattr(back, "CYAN")
                        + getattr(fore, "BLACK")
                        + c[: break_point - p_length]
                        + getattr(back, "SALMON_1")
                        + getattr(fore, "BLACK")
                        + p_text
                        + getattr(back, "GREY_30")
                        + getattr(fore, "WHITE")
                        + c[break_point:end_point]
                        + getattr(back, "GREY_50")
                        + getattr(fore, "LIGHT_CYAN")
                        + c[end_point:]
                        + getattr(style, "RESET")
                    )
                sys.stderr.flush()
            else:
                sys.stderr.write(
                    getattr(back, "CYAN")
                    + getattr(fore, "BLACK")
                    + c
                    + getattr(style, "RESET")
                )
                sys.stderr.flush()

    def reset(self):
        self.clear()

    def clear(self):
        if not self.verbose:
            return

        null = "\r" + " " * (self.terminal_width)
        sys.stderr.write(null)
        sys.stderr.write("\r")
        sys.stderr.flush()
        self.current = None
        self.step = None

    def append(self, msg):
        if not self.verbose:
            return
        self.write(f"{self.current}{msg}")

    def step_start(self, step, symbol="⚙ "):
        if not self.pid:
            raise Exception("You don't have an active progress to do it :/")

        if not self.current:
            raise Exception("You don't have a current progress bad :(")

        if self.step:
            raise Exception(
                f"You already have an unfinished step :( Here it is: '{self.step}'."
            )

        if not self.verbose:
            return

        self.step = f" / {step} "

        self.write(self.current + self.step + symbol, dont_update_current=True)

    def step_end(self, symbol="👍"):
        if not self.step:
            raise Exception("You don't have an ongoing step :(")

        if not self.verbose:
            return

        assert self.current is not None
        self.write(self.current + self.step + symbol)

        self.step = None

    def update(self, msg, increment=False):
        self.msg = msg

        if not self.verbose:
            return

        if not self.pid:
            raise Exception(f'Progress with null pid will not update for msg "{msg}"')

        if increment:
            self.increment()

        self.clear()
        self.write(f"\r[{self.pid}] {msg}")

    def end(self):
        """End the current progress

        Parameters
        ==========
        timing_filepath : str, None
            Store the timings of this progress to the filepath `timing_filepath`. File
            will only be made if a progress_total_items parameter was made during
            self.new()
        """
        self.pid = None

        if not self.verbose:
            return

        self.clear()


class Run:
    def __init__(self, log_file_path=None, verbose=True, width=45):
        self.log_file_path = log_file_path

        self.info_dict = {}
        self.verbose = verbose
        self.width = width

        self.single_line_prefixes = {1: "* ", 2: "    - ", 3: "        > "}

    def log(self, line):
        if not self.log_file_path:
            self.warning(
                "The run object got a logging request, but it was not inherited with "
                "a log file path :("
            )
            return

        with open(self.log_file_path, "a") as log_file:
            log_file.write(f"[{get_date()}] {CLEAR(line)}\n")

    def write(self, line, quiet=False, overwrite_verbose=False):
        if self.log_file_path:
            self.log(line)

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

    def quit(self):
        if self.log_file_path:
            self.log("Bye.")


class Timer:
    """Manages ordered dictionary, key is checkpoint name and value is a timestamp.

    Examples
    ========

    >>> from pooltool.terminal import Timer
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

    def _test_format_time(self):
        """Run this and visually inspect its working"""

        run = Run()
        for exponent in range(1, 7):
            seconds = 10**exponent
            td = datetime.timedelta(seconds=seconds)

            run.warning("", header=f"TESTING {td}", lc="yellow")
            fmts = [
                None,
                "SECONDS {seconds}",
                "MINUTES {minutes}",
                "HOURS   {hours}",
                "DAYS    {days}",
                "WEEKS   {weeks}",
                "MINUTES {minutes} SECONDS {seconds}",
                "SECONDS {seconds} MINUTES {minutes}",
                "HOURS   {hours}   MINUTES {minutes}",
                "DAYS    {days}    HOURS   {hours}",
                "WEEKS   {weeks}   DAYS    {days}",
                "WEEKS   {weeks}   HOURS   {hours}",
                "WEEKS   {weeks}   MINUTES {minutes}",
                "DAYS    {days}    MINUTES {minutes}",
                "HOURS   {hours}   SECONDS {seconds}",
                "DAYS    {days}    MINUTES {minutes} SECONDS {seconds}",
                "WEEKS   {weeks}   HOURS {hours}     DAYS    {days}    SECONDS {seconds} MINUTES {minutes}",
            ]
            for fmt in fmts:
                run.info(str(fmt), self.format_time(td, fmt=fmt))

    @classmethod
    def factory(cls) -> Timer:
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
    >>> import anvio.terminal as terminal
    >>> # EXAMPLE 1
    >>> with terminal.TimeCode() as t:
    >>>     time.sleep(5)
    ✓ Code finished successfully after 05s

    >>> # EXAMPLE 2
    >>> with terminal.TimeCode() as t:
    >>>     time.sleep(5)
    >>>     print(asdf) # undefined variable
    ✖ Code encountered error after 05s

    >>> # EXAMPLE 3
    >>> with terminal.TimeCode(quiet=True) as t:
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
        run=Run(),
        quiet=False,
        suppress_first=0,
    ):
        self.run = run
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


def get_date():
    return time.strftime("%d %b %y %H:%M:%S", time.localtime())


def get_terminal_size():
    """Function was taken from http://stackoverflow.com/a/566752"""

    def ioctl_GWINSZ(fd):
        try:
            # These imports are Windows incompatible
            import fcntl
            import termios

            cr = struct.unpack("hh", fcntl.ioctl(fd, termios.TIOCGWINSZ, "1234"))  # type: ignore
        except Exception:
            return None
        return cr

    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except Exception:
            pass
    if not cr:
        try:
            cr = (os.environ["LINES"], os.environ["COLUMNS"])
        except Exception:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])
