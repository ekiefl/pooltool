from __future__ import annotations
from pathlib import Path
from typing import Dict, Tuple
import attrs
import sys
import importlib

MODELS_ROOT = Path(__file__).parent

@attrs.define
class ModelDescr:
    name: str = attrs.field()
    checkpoint: Path = attrs.field()
    config: Path = attrs.field()


def is_model_dir(path: Path) -> bool:
    if not path.is_dir():
        return False

    if not (path / "formatted_total_config.py").exists():
        return False

    if not (path / "ckpt").is_dir():
        return False

    return True


sum_to_three_descriptions: Dict[Tuple[str, str], ModelDescr] = {}

for model_dir in MODELS_ROOT.glob("*"):
    if not model_dir.is_dir():
        continue

    if model_dir.name == "__pycache__":
        continue

    assert is_model_dir(model_dir), f"'{model_dir}' doesn't fit model dir format"

    for model_path in (model_dir / "ckpt").glob("*.pth.tar"):

        checkpoint_path = model_path.stem
        checkpoint_name = model_path.name.replace(".pth.tar", "")

        sum_to_three_descriptions[(model_dir.name, checkpoint_name)] = ModelDescr(
            name=model_dir.name,
            checkpoint=model_path,
            config=(model_dir / "formatted_total_config.py"),
        )

def get_model_descr(name: str, checkpoint: str) -> ModelDescr:
    try:
        return sum_to_three_descriptions[(name, checkpoint)]
    except KeyError:
        raise KeyError(
            f"{name=}, {checkpoint=} doesn't correspond to a model. "
            f"Available models: {list(sum_to_three_descriptions.keys())}"
        )
