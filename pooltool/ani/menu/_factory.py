from __future__ import annotations

from collections.abc import Generator
from typing import Any

import attrs

from pooltool.ani.menu._datatypes import MenuCheckbox, MenuDropdown, MenuInput
from pooltool.config import DisplayType, SettingsMetadata, settings


def create_elements_from_dataclass(
    obj: attrs.AttrsInstance,
) -> Generator[
    tuple[MenuCheckbox | MenuDropdown | MenuInput, attrs.Attribute], None, None
]:
    for field in attrs.fields_dict(obj.__class__).values():
        if SettingsMetadata(**field.metadata).display_type == DisplayType.NONE:
            continue

        yield create_menu_element(obj, field), field


def _create_checkbox(
    field: attrs.Attribute, field_metadata: SettingsMetadata, current_value: Any
) -> MenuCheckbox:
    def _update_bool(value: bool) -> None:
        with settings.write() as s:
            setattr(getattr(s, field_metadata.category), field.name, value)

    return MenuCheckbox.create(
        name=field_metadata.display_name,
        initial_state=current_value,
        description=field_metadata.description,
        command=_update_bool,
    )


def _create_dropdown(
    field: attrs.Attribute, field_metadata: SettingsMetadata, current_value: Any
) -> MenuDropdown:
    def _update_enum(value: str) -> None:
        with settings.write() as s:
            enum_value = field.type(value)  # type: ignore
            setattr(getattr(s, field_metadata.category), field.name, enum_value)

    return MenuDropdown.from_enum(
        name=field_metadata.display_name,
        enum_class=field.type,  # type: ignore
        initial_selection=current_value,
        description=field_metadata.description,
        command=_update_enum,
    )


def _create_numeric_input(
    field: attrs.Attribute,
    field_metadata: SettingsMetadata,
    current_value: float | int,
) -> MenuInput:
    def _process_input(value: str) -> str:
        try:
            assert field.type is not None
            numeric_value = field.type(value)
        except ValueError:
            raise TypeError("Error. Not a number.")

        with settings.write() as s:
            setattr(getattr(s, field_metadata.category), field.name, numeric_value)

        return str(numeric_value)

    return MenuInput.create(
        name=field_metadata.display_name,
        initial_value=str(current_value),
        description=field_metadata.description,
        command=_process_input,
    )


def _create_string_input(
    field: attrs.Attribute, field_metadata: SettingsMetadata, current_value: Any
) -> MenuInput:
    def _process_input(value: str) -> str:
        if field.type is not str:
            raise TypeError(f"{value} must be a string.")
        elif len(value) > 20:
            raise ValueError("Character limit is 20.")

        with settings.write() as s:
            setattr(getattr(s, field_metadata.category), field.name, value)

        return value

    return MenuInput.create(
        name=field_metadata.display_name,
        initial_value=str(current_value),
        description=field_metadata.description,
        command=_process_input,
    )


_menu_item_fn_lookup = {
    DisplayType.CHECKBOX: _create_checkbox,
    DisplayType.DROPDOWN: _create_dropdown,
    DisplayType.INTEGER: _create_numeric_input,
    DisplayType.FLOAT: _create_numeric_input,
    DisplayType.STRING: _create_string_input,
}


def create_menu_element(
    obj: attrs.AttrsInstance, field: attrs.Attribute
) -> MenuCheckbox | MenuDropdown | MenuInput:
    """Create a menu element from an attrs field.

    An opinionated function that adds generic callbacks.
    """
    current_value = getattr(obj, field.name)
    field_metadata = SettingsMetadata(**field.metadata)

    if field_metadata.display_type == DisplayType.NONE:
        raise ValueError(f"Field display type is set to NONE: {field_metadata}")

    if field_metadata.display_type not in _menu_item_fn_lookup:
        raise NotImplementedError(
            f"Menu element creation not implemented for type {field.type}"
        )

    return _menu_item_fn_lookup[field_metadata.display_type](
        field, field_metadata, current_value
    )
