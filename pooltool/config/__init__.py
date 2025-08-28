from __future__ import annotations

import shutil
import traceback
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import attrs
from panda3d.core import loadPrcFileData

from pooltool.config.paths import GENERAL_CONFIG
from pooltool.game.datatypes import GameType
from pooltool.objects.table.collection import TableName
from pooltool.serialize import conversion
from pooltool.utils import Run

run = Run()


@attrs.define
class PandaConfig:
    show_frame_rate: bool = True
    window_width: int = 1400
    sync_video: bool = False
    gl_check_errors: bool = False
    gl_version_major: int = 3
    gl_version_minor: int = 2
    aspect_ratio: float = attrs.field(init=False, default=1.6)  # Hard-coded.

    @property
    def window_height(self) -> int:
        return int(self.window_width / self.aspect_ratio)

    def apply_settings(self) -> None:
        """Apply Panda3D configuration settings at runtime."""
        loadPrcFileData(
            "", f"show-frame-rate-meter {'#t' if self.show_frame_rate else '#f'}"
        )
        loadPrcFileData("", f"win-size {self.window_width} {self.window_height}")
        loadPrcFileData("", "fullscreen #f")  # hard-coded, fullscreen broken
        loadPrcFileData("", f"sync-video {'#t' if self.sync_video else '#f'}")
        loadPrcFileData("", f"gl-check-errors {'#t' if self.gl_check_errors else '#f'}")
        loadPrcFileData(
            "", f"gl-version {self.gl_version_major} {self.gl_version_minor}"
        )


@attrs.define
class GraphicsConfig:
    room: bool = attrs.field(
        default=True,
        metadata=dict(
            display_name="Room",
            description="Whether to render the room or not.",
        ),
    )
    floor: bool = attrs.field(
        default=True,
        metadata=dict(
            display_name="Floor",
            description="Whether to render the floor or not.",
        ),
    )
    table: bool = attrs.field(
        default=True,
        metadata=dict(
            display_name="Table",
            description="Whether to render the table or not.",
        ),
    )
    shadows: bool = False
    shader: bool = True
    lights: bool = True
    max_lights: int = 13
    physical_based_rendering: bool = False
    debug: bool = False
    fps: int = 45
    fps_inactive: int = 5
    hud: bool = True


@attrs.define
class GameplayConfig:
    cue_collision: bool = attrs.field(
        default=True,
        metadata=dict(
            display_name="Cue Collision",
            description=(
                "If selected, the cue stick respects cushion and ball geometry, which "
                "constrains the cue's possible orientations. If unselected, the cuestick "
                "ignores all geometry."
            ),
        ),
    )
    game_type: GameType = attrs.field(
        default=GameType.NINEBALL,
        metadata=dict(
            display_name="Game Type",
            description="Choose the type of pool game to play.",
        ),
    )
    enforce_rules: bool = attrs.field(
        default=False,
        metadata=dict(
            display_name="Enforce Rules",
            description="Whether to enforce game rules or allow free play.",
        ),
    )
    table_name: TableName = attrs.field(
        default=TableName.SEVEN_FOOT_SHOWOOD,
        metadata=dict(
            display_name="Table",
            description="Select the table you wish to play on.",
        ),
    )


@attrs.define
class Settings:
    graphics: GraphicsConfig
    gameplay: GameplayConfig
    panda: PandaConfig

    def save(self, path: Path) -> None:
        conversion.unstructure_to(self, path)

    def apply_panda_settings(self) -> None:
        """Apply Panda3D configuration settings."""
        self.panda.apply_settings()

    @classmethod
    def default(cls) -> Settings:
        return cls(
            GraphicsConfig(),
            GameplayConfig(),
            PandaConfig(),
        )

    @classmethod
    def load(cls, path: Path) -> Settings:
        return conversion.structure_from(path, Settings)

    @staticmethod
    def _attrs() -> set[str]:
        return set([attr.name for attr in attrs.fields_dict(Settings).values()])


# Inherits from Settings so the LSP recognizes Settings attributes. Yet truthfully these
# are never properly initialized.
class SettingsProxy(Settings):
    """A lazy-loading settings proxy that reads configuration from disk on each access.

    This class acts as a transparent proxy to Settings, dynamically loading the
    configuration file whenever a settings attribute is accessed. If the file doesn't
    exist or is corrupted, it automatically creates/repairs the configuration file
    with default values.

    For read-only access, simply access attributes directly (e.g., `settings.graphics.fps`).
    For modifications, use the `write()` context manager to ensure changes are saved:

    Examples:
        # Read settings
        fps = settings.graphics.fps

        # Modify settings
        with settings.write() as s:
            s.graphics.fps = 60
            s.gameplay.game_type = GameType.EIGHTBALL

    Args:
        path: Path to the configuration file to load from
    """

    def __init__(self, path: Path) -> None:
        self.path: Path = path
        self._valid_cache: bool = True
        self._cache: Settings = self.read()

    def __getattribute__(self, name: str):
        if name in Settings._attrs():
            if not self._valid_cache:
                self._cache = self.read()
                self._valid_cache = True

            return getattr(self._cache, name)

        return object.__getattribute__(self, name)

    def read(self) -> Settings:
        """Load settings from disk, creating defaults if file is missing or corrupted.

        This method handles file I/O errors gracefully by backing up corrupted files
        and creating fresh defaults. The returned Settings object is independent of
        the file system - modifications to it won't be persisted unless explicitly saved.

        Returns:
            A Settings instance loaded from disk or created with default values
        """
        if self.path.exists():
            try:
                cfg = Settings.load(self.path)
            except Exception:
                full_traceback = traceback.format_exc()
                dump_path = self.path.parent / f".{self.path.name}"
                run.info(
                    f"{self.path} is malformed and can't be loaded. It is being "
                    f"replaced with a default working version. Your version has been moved to "
                    f"{dump_path} if you want to diagnose it. Here is the error:\n{full_traceback}"
                )
                shutil.move(self.path, dump_path)
                cfg = Settings.default()
                cfg.save(self.path)
        else:
            cfg = Settings.default()
            cfg.save(self.path)

        return cfg

    @contextmanager
    def write(self) -> Generator[Settings, None, None]:
        """Context manager for modifying settings with automatic persistence.

        Loads the current settings, yields them for modification, then automatically
        saves the changes back to disk when the context exits. All modifications
        within the context are saved as a single atomic operation.

        Yields:
            Settings instance that can be modified

        Examples:
            with settings.write() as s:
                s.graphics.fps = 60
                s.gameplay.game_type = GameType.NINEBALL
        """
        settings_inst = self.read()
        yield settings_inst
        settings_inst.save(self.path)
        self._valid_cache = False


settings = SettingsProxy(GENERAL_CONFIG)

# Apply Panda3D settings from the config
settings.read().apply_panda_settings()
