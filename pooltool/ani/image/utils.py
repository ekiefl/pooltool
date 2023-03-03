from pathlib import Path
from typing import Sequence, Union

from PIL import Image

from pooltool.utils.strenum import StrEnum, auto


class ImageExt(StrEnum):
    PNG = auto()
    JPG = auto()


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
