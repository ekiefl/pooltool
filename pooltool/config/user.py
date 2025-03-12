from pathlib import Path

HOME = Path.home()

CONFIG_DIR = HOME / ".config/pooltool"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

PHYSICS_DIR = CONFIG_DIR / "physics"
PHYSICS_DIR.mkdir(exist_ok=True)
