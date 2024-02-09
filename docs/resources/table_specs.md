:::{note}
**This is under construction (work in progress)!**
:::

# Table Specification

There are many ways to create a table object, each with varying levels of complexity and customizability. This resource will demonstrate each available option, least to most customizability.

## The `Table` object

The endpoint for table generation is the [](#pooltool.objects.table.datatypes.Table) [](#pooltool.system.datatypes.System) object.

:::{admonition} The Table Object

From the API docs:

```{eval-rst}
.. autoclass:: pooltool.objects.table.datatypes.Table
    :noindex:
```
:::

## Using default and prebuilt tables

There are several ways to build a table. This document will describe 

For pocket table specifications I have created a parametrization for table dimensions and cushion geometries involving several parameters. The point of this document is to make clear what each of these parameters does.

The class that holds the table specs is `pooltool.objects.table.specs.PocketTableSpecs`:

```python
@define(frozen=True)
class PocketTableSpecs(TableSpecs):
    """Parameters that specify a pocket table"""

    l: float = field(default=1.9812)
    w: float = field(default=1.9812 / 2)

    cushion_width: float = field(default=2 * 2.54 / 100)
    cushion_height: float = field(default=0.64 * 2 * 0.028575)
    corner_pocket_width: float = field(default=0.118)
    corner_pocket_angle: float = field(default=5.3)  # degrees
    corner_pocket_depth: float = field(default=0.0398)
    corner_pocket_radius: float = field(default=0.124 / 2)
    corner_jaw_radius: float = field(default=0.0419 / 2)
    side_pocket_width: float = field(default=0.137)
    side_pocket_angle: float = field(default=7.14)  # degrees
    side_pocket_depth: float = field(default=0.00437)
    side_pocket_radius: float = field(default=0.129 / 2)
    side_jaw_radius: float = field(default=0.0159 / 2)

    (...)
```

What do each of these parameters do? Let's go through it in detail

## Table dimensions

**`l`** is the length of the surface playing area (direction parallel with the y-axis), measured cushion tip to cushion tip.

**`w`** is the width of the surface playing area (direction parallel with the x-axis), measured cushion tip to cushion tip.

**`cushion_width`** is the horizontal distance from the cushion tip to the edge of the cushion (where it is mounted onto the table framing). This has important implications for how long the cushion segments are in the pockets' openings. For example, here is a cushion width of 2 inches and then 4 inches:

<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/fdb3a0b2-a8a6-4686-83f4-9c2a628ce37d">

<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/fba39af2-c375-46b0-9ca0-ec73093bff6a">

**`cushion_height`** is the vertical distance between the cushion tip and the playing surface. It is supposed to be around 64% of a ball radius.

## Corner pockets

**`corner_jaw_radius`** defines the curvature of the jaw tips. For example, snooker has curved jaws and has a large `corner_jaw_radius`. All jaw tips have at least some radius. Here is a small value followed by a large value:

<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/213d5db2-f679-4ecc-8f8b-45c4a38e4c66">
<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/f0adb1c5-cc2e-4205-963f-5ab5e6595a9a">

**`corner_pocket_width`** is the opening width of the corner pockets. The distance is drawn from jaw tip to jaw tip in the scenario where `corner_jaw_radius` is set to 0. Here is a jaw width of 0.10 and then 0.05:

<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/b6f40c7d-eb7d-4a83-bcf8-f5f29b9b0590">
<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/f6fc17eb-705e-4303-be70-3bae9f99ae13">

**`corner_pocket_depth`** defines how far back the pocket is from the pocket opening. Formally, I've parameterized things such that when `corner_pocket_depth` is 0, the pocket's center coincides with the intersection between the adjacent cushion lines. Here is a value of 0 followed by 0.0417: 

<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/f9660426-7fbe-4b60-b603-49af0ae733e1">
<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/be31eaeb-58eb-4fe8-b118-9af973ebe7d1">

**`corner_pocket_radius`** defines the curvature of the pocket lip. Here is a small pocket radius followed by a large pocket radius:

<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/5e38ffef-2d7e-43f6-93c4-eaa51d65a920">
<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/98c3c4e9-a5ba-4ab6-91a7-90797837e01a">

Note that you'll likely have to increase the `corner_pocket_depth` when you increase the `corner_pocket_radius`

**`corner_pocket_angle`** defines the angle of the jaw cushions. 0 refers to jaw cushions that are 45 degrees from the adjacent table cushions. Here is 0 followed by 10 degrees:

<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/2066f0a2-90e2-40e8-80bf-c78566b8921b">
<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/3d72c074-dd34-45f4-9f3b-d64b4dd24d15">

## Side pockets

**`side_pocket_width`** see `corner_pocket_width`

**`side_pocket_depth`** see `corner_pocket_depth`

**`side_pocket_radius`** see `corner_pocket_radius`

**`side_jaw_radius`** see `corner_jaw_radius`

**`side_pocket_angle`** is similar `corner_pocket_angle`, except 0 refers to jaw cushions that are 90 degrees from the adjacent table cushions. Here is 0 followed by 10 degrees:

<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/ee5272d2-db26-41ec-8719-5af190872e81">
<img width="300" alt="image" src="https://github.com/ekiefl/pooltool/assets/8688665/b3561c73-7020-4ef0-8a43-f7629adcbc92">
