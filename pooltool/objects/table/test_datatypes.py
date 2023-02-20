import pytest

from pooltool.objects.table.datatypes import Table


@pytest.fixture
def table():
    return Table.pocket_table()


def test_table_copy(table):
    new = table.copy()

    # new and table equate
    assert new is not table
    assert new == table

    assert new.cushion_segments is not table.cushion_segments
    assert new.pockets is not table.pockets

    # `specs` object _is_ shared, but its frozen so its OK
    assert new.specs is table.specs
    assert new.specs.__dataclass_params__.frozen
