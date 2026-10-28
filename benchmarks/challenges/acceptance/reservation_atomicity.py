from copy import deepcopy

import pytest

from service import reserve


def test_combined_and_input_preservation():
    stock = {'a': 7, 'b': 3}
    items = [('a', 2), ('a', 3), ('b', 1)]
    saved = deepcopy(items)
    assert reserve(stock, items) is True
    assert stock == {'a': 2, 'b': 2} and items == saved


@pytest.mark.parametrize('items', [[('a', 2), ('missing', 1)], [('a', 4), ('a', 4)],
                                  [('a', 1), ('b', 9)], [('a', True)], [('a', 0)],
                                  [('a', -1)], [('a', 1.5)]])
def test_failure_is_atomic(items):
    stock = {'a': 7, 'b': 3}
    assert reserve(stock, items) is False
    assert stock == {'a': 7, 'b': 3}


def test_empty():
    assert reserve({}, []) is True
