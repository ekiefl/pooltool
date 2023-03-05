from pathlib import Path
from typing import Optional, Sequence, Union

import attrs
import numpy as np
from numpy.typing import NDArray
from PIL import Image

from pooltool.system import System
from pooltool.utils.strenum import StrEnum, auto


class ImageExt(StrEnum):
    PNG = auto()
    JPG = auto()

    @classmethod
    def regex(cls) -> str:
        return "(" + "|".join(ext.value for ext in cls) + ")"


@attrs.define
class DataPack:
    imgs: NDArray[np.uint8]
    system: Optional[System] = attrs.field(default=None)
    fps: float = attrs.field(default=10)


def gif(
    paths: Sequence[Union[str, Path]], output: Union[str, Path], fps: float
) -> Path:
    """Create a gif from a sequence of image paths"""

    output = Path(output)

    imgs = (Image.open(Path(path)) for path in paths)
    img = next(imgs)
    img.save(
        fp=output,
        format="GIF",
        append_images=imgs,
        save_all=True,
        duration=(1 / fps) * 1e3,
        loop=0,  # loop infinitely
    )

    return output
