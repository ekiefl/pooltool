import numpy as np
import pytest

from pooltool.ani.table_box import TableBox
from pooltool.objects.table.datatypes import Table
from pooltool.objects.table.render import TableRender

R = 0.028575
BOX = TableBox(
    w=1.0, l=2.0, x_min=-0.15, x_max=1.15, y_min=-0.15, y_max=2.15, top=0.05, floor=-0.7
)


def _heights(*positions: tuple[float, float, float]) -> np.ndarray:
    return BOX.surface_heights(np.array(positions), R)


def test_contains_is_the_rail_outline():
    assert BOX.contains(0.5, 1.0)
    assert BOX.contains(-0.1, 2.1)
    assert not BOX.contains(-0.2, 1.0)
    assert not BOX.contains(0.5, 2.2)


def test_shadow_over_the_playing_surface_is_on_the_cloth_at_any_height():
    heights = _heights((0.5, 1.0, R), (0.5, 1.0, R + 0.02), (0.5, 1.0, R + 0.5))
    assert heights == pytest.approx([0.0, 0.0, 0.0])


def test_shadow_follows_a_ball_dropping_into_a_pocket():
    heights = _heights((0.5, 1.0, R - 0.03), (-0.03, -0.03, R - 0.03))
    assert heights == pytest.approx([-0.03, -0.03])


def test_shadow_over_the_rails_is_on_the_rail_top_when_the_ball_clears_it():
    heights = _heights((-0.1, 1.0, R + 0.05), (-0.1, 1.0, R + 0.3))
    assert heights == pytest.approx([BOX.top, BOX.top])


def test_shadow_beyond_the_rails_is_on_the_floor():
    heights = _heights((-0.2, 1.0, R + 0.3), (-0.2, 1.0, R - 0.7))
    assert heights == pytest.approx([BOX.floor, BOX.floor])


def test_bounding_box_is_measured_without_a_window():
    table = Table.default()
    box = TableRender(table).bounding_box()

    assert box.w == table.w
    assert box.l == table.l
    assert box.x_min < 0.0 < table.w < box.x_max
    assert box.y_min < 0.0 < table.l < box.y_max
    assert 0.0 < box.top < 0.1
    assert box.floor == -table.height
