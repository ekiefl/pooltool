from __future__ import annotations

import attrs

from pooltool.ani.menu._datatypes import MenuCheckbox, MenuDropdown
from pooltool.config import Settings, settings


def create_elements_from_dataclass(
    obj: attrs.AttrsInstance,
) -> list[MenuCheckbox | MenuDropdown]:
    return [create_menu_element(obj, key) for key in attrs.fields_dict(obj.__class__)]


def create_menu_element(
    obj: attrs.AttrsInstance, attr_name: str
) -> MenuCheckbox | MenuDropdown:
    """Create a menu element from an attrs field with metadata."""
    field = attrs.fields_dict(obj.__class__)[attr_name]
    current_value = getattr(obj, attr_name)

    display_name = field.metadata["display_name"]
    description = field.metadata["description"]

    # Determine the settings path (e.g., "graphics" or "gameplay")
    settings_fields = attrs.fields_dict(Settings)
    for field_name, settings_field in settings_fields.items():
        if settings_field.type == obj.__class__:
            obj_type_name = field_name
            break
    else:
        raise NotImplementedError(f"Unknown settings class '{obj.__class__}'.")

    if field.type is bool:

        def _update_bool(value: bool) -> None:
            with settings.write() as s:
                setattr(getattr(s, obj_type_name), attr_name, value)

        return MenuCheckbox.create(
            name=display_name,
            initial_state=current_value,
            description=description,
            command=_update_bool,
        )
    elif hasattr(field.type, "__members__"):  # Check if it's an enum-like class

        def _update_enum(value: str) -> None:
            with settings.write() as s:
                enum_value = field.type(value)  # type ignore
                setattr(getattr(s, obj_type_name), attr_name, enum_value)

        return MenuDropdown.from_enum(
            name=display_name,
            enum_class=field.type,  # type: ignore
            initial_selection=current_value,
            description=description,
            command=_update_enum,
        )

    raise NotImplementedError(
        f"Menu element creation not implemented for type {field.type}"
    )
