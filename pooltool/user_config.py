from pathlib import Path

HOME = Path.home()

CONFIG_DIR = HOME / ".config/pooltool"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
