from copy import deepcopy

import pytest

from pages import page


def test_order_cursor_and_preservation():
    rows = [{'id': value} for value in [90, 10, 40, 70]]
    saved = deepcopy(rows)
    assert page(rows, None, 2) == ([{'id': 10}, {'id': 40}], 40)
    assert page(rows, 40, 2) == ([{'id': 70}, {'id': 90}], None)
    assert page(rows, 39, 1) == ([{'id': 40}], 40)
    assert rows == saved


@pytest.mark.parametrize('size', [0, -1, True, 1.5])
def test_invalid_size(size):
    with pytest.raises(ValueError):
        page([{'id': 10}], size=size)


def test_empty_or_exhausted():
    assert page([], size=1) == ([], None)
    assert page([{'id': 5}], 5, 2) == ([], None)
