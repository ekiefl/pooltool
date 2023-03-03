from pathlib import Path
from typing import List, Union

import attrs
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray

from pooltool.ani.image.utils import ImageExt


@attrs.define
class ImageDirExporter:
    """Exporter for creating a directory of images"""

    save_dir: Union[str, Path] = attrs.field(converter=Path)
    ext: ImageExt = attrs.field(converter=ImageExt)
    prefix: str = attrs.field(default="shot")
    image_count: int = attrs.field(default=0)
    paths: List[Path] = attrs.field(factory=list)

    def __attrs_post_init__(self):
        if not self.save_dir.exists():
            self.save_dir.mkdir(parents=True)

    def save(self, img: NDArray[np.uint8]) -> Path:
        """Save an image"""
        path = self._get_filepath()
        assert not path.exists()

        plt.imsave(path, img)

        # Increment
        self.image_count += 1
        self.paths.append(path)

        return path

    def _get_filepath(self) -> Path:
        stem = f"{self.prefix}_{self.image_count:06d}"
        name = f"{stem}.{self.ext}"
        return Path(self.save_dir) / name
