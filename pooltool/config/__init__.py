from __future__ import annotations

import shutil
import traceback
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import attrs
from panda3d.core import loadPrcFileData

from pooltool.config.paths import GENERAL_CONFIG
from pooltool.game.datatypes import GameType
from pooltool.objects.table.collection import TableName
from pooltool.serialize import conversion
from pooltool.utils import Run
from pooltool.utils.strenum import StrEnum, auto

run = Run()


class SettingsCategory(StrEnum):
    # Values must match the `Settings` attribute names
    GRAPHICS = "graphics"
    GAMEPLAY = "gameplay"
    SYSTEM = "system"


class DisplayType(StrEnum):
    NONE = auto()
    CHECKBOX = auto()
    DROPDOWN = auto()
    INTEGER = auto()
    FLOAT = auto()
    STRING = auto()


@attrs.define(kw_only=True, frozen=True)
class SettingsMetadata:
    display_name: str
    description: str = ""
    category: SettingsCategory = SettingsCategory.GRAPHICS
    display_type: DisplayType = DisplayType.NONE


def settings_field(*args, **kwargs) -> Any:
    if "metadata" in kwargs:
        assert isinstance(kwargs["metadata"], SettingsMetadata)
        kwargs["metadata"] = attrs.asdict(kwargs["metadata"])
    return attrs.field(*args, **kwargs)


@attrs.define(kw_only=True)
class SystemConfig:
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


@attrs.define(kw_only=True)
class GraphicsConfig:
    room: bool = settings_field(
        default=True,
        metadata=SettingsMetadata(
            display_name="Room",
            description="Whether to render the room or not.",
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    floor: bool = settings_field(
        default=True,
        metadata=SettingsMetadata(
            display_name="Floor",
            description="Whether to render the floor or not.",
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    table: bool = settings_field(
        default=True,
        metadata=SettingsMetadata(
            display_name="Table",
            description="Whether to render the table or not.",
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    shadows: bool = settings_field(
        default=False,
        metadata=SettingsMetadata(
            display_name="Environment Shadows",
            description=(
                "Whether to render environmental shadows. Ball and cushion shadows "
                "are unaffected by this setting."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    shader: bool = settings_field(
        default=True,
        metadata=SettingsMetadata(
            display_name="Advanced Shader",
            description=(
                "Whether to use the advanced shader. Uncheck for a cartoony "
                "visual effect."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    lights: bool = settings_field(
        default=True,
        metadata=SettingsMetadata(
            display_name="Lighting",
            description=(
                "Whether to render scene lighting. When disabled, uses flat shading."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    max_lights: int = settings_field(
        default=13,
        metadata=SettingsMetadata(
            display_name="Maximum Lights",
            description=(
                "Maximum number of dynamic lights that can be rendered simultaneously."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.NONE,
        ),
    )
    physical_based_rendering: bool = settings_field(
        default=False,
        metadata=SettingsMetadata(
            display_name="Physically-Based Rendering",
            description=(
                "Use PBR materials for more realistic lighting and surface appearance."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    debug: bool = settings_field(
        default=False,
        metadata=SettingsMetadata(
            display_name="Debug Visualizations",
            description=(
                "Show collision shapes and debug wireframes for balls, table, and cue."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    fps: int = settings_field(
        default=45,
        metadata=SettingsMetadata(
            display_name="Frame Rate",
            description=(
                "Target frames per second when the application window is active."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.NONE,
        ),
    )
    fps_inactive: int = settings_field(
        default=5,
        metadata=SettingsMetadata(
            display_name="Inactive Frame Rate",
            description=(
                "Reduced frame rate when the application window loses focus "
                "to save resources."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.NONE,
        ),
    )
    hud: bool = settings_field(
        default=True,
        metadata=SettingsMetadata(
            display_name="HUD Elements",
            description=(
                "Show heads-up display elements like english indicator, power "
                "gauge, and stroke jack."
            ),
            category=SettingsCategory.GRAPHICS,
            display_type=DisplayType.CHECKBOX,
        ),
    )


@attrs.define(kw_only=True)
class GameplayConfig:
    cue_collision: bool = settings_field(
        default=True,
        metadata=SettingsMetadata(
            display_name="Cue Collision",
            description=(
                "If selected, the cue stick respects cushion and ball geometry, which "
                "constrains the cue's possible orientations. If unselected, the "
                "cuestick ignores all geometry."
            ),
            category=SettingsCategory.GAMEPLAY,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    game_type: GameType = settings_field(
        default=GameType.NINEBALL,
        metadata=SettingsMetadata(
            display_name="Game Type",
            description="Choose the type of pool game to play.",
            category=SettingsCategory.GAMEPLAY,
            display_type=DisplayType.DROPDOWN,
        ),
    )
    enforce_rules: bool = settings_field(
        default=False,
        metadata=SettingsMetadata(
            display_name="Enforce Rules",
            description="Whether to enforce game rules or allow free play.",
            category=SettingsCategory.GAMEPLAY,
            display_type=DisplayType.CHECKBOX,
        ),
    )
    table_name: TableName = settings_field(
        default=TableName.SEVEN_FOOT_SHOWOOD,
        metadata=SettingsMetadata(
            display_name="Table",
            description="Select the table you wish to play on.",
            category=SettingsCategory.GAMEPLAY,
            display_type=DisplayType.DROPDOWN,
        ),
    )


@attrs.define
class Settings:
    graphics: GraphicsConfig
    gameplay: GameplayConfig
    system: SystemConfig

    def save(self, path: Path) -> None:
        conversion.unstructure_to(self, path)

    def apply_panda_settings(self) -> None:
        """Apply Panda3D configuration settings."""
        self.system.apply_settings()

    @classmethod
    def default(cls) -> Settings:
        return cls(
            GraphicsConfig(),
            GameplayConfig(),
            SystemConfig(),
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
