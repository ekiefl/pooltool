import pytest

from pooltool.physics.resolve.types import ModelArgs
from pooltool.serialize import conversion


def test_model_args_serialize_flat(tmp_path):
    d = {
        "a": 42,
        "b": True,
        "c": "string",
        "d": None,
    }
    conversion.unstructure_to(d, tmp_path / "test.yaml")
    assert d == conversion.structure_from(tmp_path / "test.yaml", ModelArgs)


def test_model_args_serialize_recursive(tmp_path):
    d = {
        "a": 42,
        "b": True,
        "c": {
            "1": 42,
            "2": True,
            "3": {
                "x": 42,
                "y": True,
                "z": "string",
            },
        },
    }
    conversion.unstructure_to(d, tmp_path / "test.yaml")
    assert d == conversion.structure_from(tmp_path / "test.yaml", ModelArgs)


def test_model_args_serialize_bad_keys(tmp_path):
    # Only string keys  allowed
    d = {("a", "b"): 1}
    with pytest.raises(Exception):
        assert d != conversion.unstructure_to(d, tmp_path / "test.yaml")

    # Unfortunately ints are valid because of YAML type casting
    d = {42: 1}
    conversion.unstructure_to(d, tmp_path / "test.yaml")
    with pytest.raises(Exception):
        # But at least round trip fails.
        assert d == conversion.structure_from(tmp_path / "test.yaml", ModelArgs)
