from pathlib import Path
from typing import Sequence, Union

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from pooltool.utils.strenum import StrEnum, auto


class ImageExt(StrEnum):
    PNG = auto()
    JPG = auto()

    @classmethod
    def regex(cls) -> str:
        return "(" + "|".join(ext.value for ext in cls) + ")"


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


def rgb2gray(rgb: NDArray[np.uint8]) -> NDArray[np.uint8]:
    """Convert an image (or image stack) to grayscale"""
    return np.array(Image.fromarray(rgb).convert(mode="L"))


def path2imgarray(img_path: Path):
    """Read an image from a file as a numpy array"""
    return img2array(Image.open(img_path))


def img2array(img):
    """Get the alpha-snuffed numpy array from a PIL Image"""
    return np.asarray(img)[:, :, :3] if img.mode == "RGB" else np.asarray(img)
