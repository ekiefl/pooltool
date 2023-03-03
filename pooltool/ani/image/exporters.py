from pathlib import Path
from typing import List, Optional

import attrs
import h5py
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from pooltool.ani.image.utils import ImageExt, gif
from pooltool.system.datatypes import System
from pooltool.utils.strenum import StrEnum, auto


@attrs.define
class DataPack:
    system: System
    imgs: NDArray[np.uint8]
    fps: float


class ExporterType(StrEnum):
    IMAGE_DIR = auto()
    HDF5 = auto()


@attrs.define
class ImageDirExporter:
    """Exporter for creating a directory of images"""

    save_dir: Path = attrs.field(converter=Path)
    ext: ImageExt = attrs.field(converter=ImageExt)
    prefix: str = attrs.field(default="shot")
    save_gif: bool = attrs.field(default=False)
    image_count: int = attrs.field(init=False, default=0)
    paths: List[Path] = attrs.field(init=False, factory=list)

    def __attrs_post_init__(self):
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True)

    def save(self, data: DataPack) -> None:
        frames = np.shape(data.imgs)[0]
        for frame in range(frames):
            path = self._get_filepath()
            assert not path.exists(), f"{path} already exists!"

            plt.imsave(path, data.imgs[frame, :, :, :])

            # Increment
            self.image_count += 1
            self.paths.append(path)

        data.system.save(self.save_dir / f"_{self.prefix}.msgpack")

        if self.save_gif:
            gif(
                paths=self.paths,
                output=self.save_dir / f"_{self.prefix}.gif",
                fps=data.fps,
            )

    def _get_filepath(self) -> Path:
        stem = f"{self.prefix}_{self.image_count:06d}"
        name = f"{stem}.{self.ext}"
        return Path(self.save_dir) / name
