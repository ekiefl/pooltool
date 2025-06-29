import sys
import textwrap


def _red_text(text):
    return f"\033[0;31m{text}\033[0m" if sys.stdout.isatty() else text


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


class PoolToolError(Exception):
    error_type = "General Error"

    def __str__(self):
        message = _normalize_whitespace(super().__str__())

        wrapped_lines = textwrap.fill(message, width=80).split("\n")
        max_length = max(len(line) for line in wrapped_lines)
        padded_lines = [line.ljust(max_length) for line in wrapped_lines]
        error_lines = self._format_error_lines(padded_lines)

        return f"\n\n{'\n'.join(error_lines)}\n\n"

    def _format_error_lines(self, lines: list[str]) -> list[str]:
        if not lines:
            return []

        formatted_lines = [f"{_red_text(self.error_type)}: {lines[0]}"]
        indent = " " * (len(self.error_type) + 2)
        formatted_lines.extend(f"{indent}{line}" for line in lines[1:])

        return formatted_lines


class ConfigError(PoolToolError):
    error_type = "Config Error"


class StrokeError(PoolToolError):
    error_type = "Stroke Error"


class SimulateError(PoolToolError):
    error_type = "Simulate Error"
