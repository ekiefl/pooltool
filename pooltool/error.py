#! /usr/bin/env python

import textwrap


def color_text(x: str, *args, **kwargs) -> str:
    return x


def remove_spaces(text: str | None) -> str:
    if not text:
        return ""

    while "  " in text:
        text = text.replace("  ", " ")

    return text


class PoolToolError(Exception):
    def __init__(self, e: str | None = None) -> None:
        super().__init__()
        self.e: str = e if e is not None else ""
        self.error_type = "General Error"

    def __str__(self):
        max_len = max([len(line) for line in textwrap.fill(self.e, 80).split("\n")])
        error_lines = [
            "{}{}".format(line, " " * (max_len - len(line)))
            for line in textwrap.fill(self.e, 80).split("\n")
        ]

        error_message = [
            "{}: {}".format(color_text(self.error_type, "red"), error_lines[0])
        ]
        for error_line in error_lines[1:]:
            error_message.append(
                "{}{}".format(" " * (len(self.error_type) + 2), error_line)
            )

        return "\n\n" + "\n".join(error_message) + "\n\n"

    def clear_text(self):
        return self.e


class ConfigError(PoolToolError):
    def __init__(self, e: str | None = None) -> None:
        super().__init__(remove_spaces(e))
        self.error_type = "Config Error"


class StrokeError(PoolToolError):
    def __init__(self, e: str | None = None) -> None:
        super().__init__(remove_spaces(e))
        self.error_type = "Stroke Error"


class SimulateError(PoolToolError):
    def __init__(self, e: str | None = None) -> None:
        super().__init__(remove_spaces(e))
        self.error_type = "Simulate Error"
