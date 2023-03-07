import gzip
import re
import shutil
import zipfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Union

import attrs
import h5py
import numpy as np
from numpy.typing import NDArray
from PIL import Image

from pooltool.ani.image.utils import DataPack, ImageExt, gif, img2array, path2imgarray


class ImageStorageMethod(ABC):
    path: Path

    @abstractmethod
    def save(self, data: DataPack) -> Any:
        pass

    @staticmethod
    @abstractmethod
    def read(path: Union[str, Path]) -> NDArray[np.uint8]:
        pass


def _img_regex_pattern():
    return re.compile(r".*_[0-9]{6,6}\." + ImageExt.regex())


@attrs.define
class ImageZip(ImageStorageMethod):
    """Exporter for creating a zipfile of images"""

    path: Path = attrs.field(converter=Path)
    ext: ImageExt = attrs.field(converter=ImageExt)
    prefix: str = attrs.field(default="shot")
    compress: bool = attrs.field(default=True)
    save_gif: bool = attrs.field(default=False)
    image_count: int = attrs.field(init=False, default=0)
    paths: List[Path] = attrs.field(init=False, factory=list)

    def __attrs_post_init__(self):
        if self.path.exists():
            raise FileExistsError(f"{self.path} shouldn't exist, but does.")

        if self.compress:
            assert (
                self.path.suffix == ".zip"
            ), f"{self.path} must end with .zip if compress is True"

    def save(self, data: DataPack) -> None:
        if self.compress:
            # Write contents to a temp directory that will be deleted after the contents
            # have been zipped
            save_dir = self.path.parent / "tmp"
        else:
            save_dir = self.path

        save_dir.mkdir(parents=True)

        frames = np.shape(data.imgs)[0]
        for frame in range(frames):
            path = self._get_filepath(root=save_dir)
            assert not path.exists(), f"{path} already exists!"

            Image.fromarray(data.imgs[frame, ...]).save(path)

            # Increment
            self.image_count += 1
            self.paths.append(path)

        if data.system is not None:
            data.system.save(save_dir / f"_{self.prefix}.msgpack")

        if self.save_gif:
            gif(
                paths=self.paths,
                output=save_dir / f"_{self.prefix}.gif",
                fps=data.fps,
            )

        if not self.compress:
            return

        # Compress the directory as a zip file and delete tmp dir
        with zipfile.ZipFile(self.path, mode="w") as archive:
            for path in save_dir.iterdir():
                archive.write(path, arcname=path.name)
        shutil.rmtree(save_dir)

    def _get_filepath(self, root: Path) -> Path:
        stem = f"{self.prefix}_{self.image_count:06d}"
        name = f"{stem}.{self.ext}"
        return root / name

    @staticmethod
    def read(path: Union[str, Path]) -> NDArray[np.uint8]:
        path = Path(path)
        assert path.exists(), f"{path} doesn't exist"

        if path.is_dir():
            return ImageZip._read_dir(path)
        else:
            assert path.suffix == ".zip"
            return ImageZip._read_zip(path)

    @staticmethod
    def _read_dir(path: Path) -> NDArray[np.uint8]:
        img_pattern = _img_regex_pattern()

        img_arrays: List[NDArray] = []
        for img_path in sorted(path.glob("*")):
            if not img_pattern.match(str(img_path)):
                continue
            img_arrays.append(path2imgarray(img_path))

        return np.array(img_arrays, dtype=np.uint8)

    @staticmethod
    def _read_zip(path: Path) -> NDArray[np.uint8]:
        img_pattern = _img_regex_pattern()

        img_arrays: List[NDArray] = []
        with zipfile.ZipFile(path, "r") as archive:
            content_list = sorted(archive.namelist())

            for filename in content_list:
                if not img_pattern.match(filename):
                    continue

                img_arrays.append(img2array(Image.open(archive.open(filename))))

        return np.array(img_arrays, dtype=np.uint8)


@attrs.define
class HDF5Images(ImageStorageMethod):
    path: Path = attrs.field(converter=Path)

    def save(self, data: DataPack) -> None:
        with h5py.File(self.path, "w") as fp:
            fp.create_dataset(
                "images", np.shape(data.imgs), h5py.h5t.STD_U8BE, data=data.imgs
            )

        if data.system is not None:
            data.system.save(self.path.with_suffix(".msgpack"))

    @staticmethod
    def read(path: Union[str, Path]) -> NDArray[np.uint8]:
        with h5py.File(path, "r+") as fp:
            return np.array(fp["/images"]).astype("uint8")


@attrs.define
class NpyImages(ImageStorageMethod):
    path: Path = attrs.field(converter=Path)

    def save(self, data: DataPack) -> None:
        np.save(self.path, data.imgs)

        if data.system is not None:
            data.system.save(self.path.with_suffix(".msgpack"))

    @staticmethod
    def read(path: Union[str, Path]) -> NDArray[np.uint8]:
        return np.load(path)


@attrs.define
class GzipArrayImages(ImageStorageMethod):
    path: Path = attrs.field(converter=Path)

    def save(self, data: DataPack) -> None:
        with open(self.path, "wb") as fp:
            fp.write(
                gzip.compress(memoryview(data.imgs), compresslevel=1)  # type: ignore
            )

        if data.system is not None:
            data.system.save(self.path.with_suffix(".msgpack"))

    @staticmethod
    def read(path: Union[str, Path]) -> NDArray[np.uint8]:
        with open(path, "rb") as fp:
            return np.frombuffer(gzip.decompress(fp.read()), dtype=np.uint8)
