from copy import deepcopy

from retention import removable


def test_projects_pins_and_strict_boundary():
    rows = [{'id': 'b', 'project': 'one', 'created': 5},
            {'id': 'a', 'project': 'one', 'created': 1},
            {'id': 'c', 'project': 'two', 'created': 2},
            {'id': 'p', 'project': 'two', 'created': 1, 'pinned': True},
            {'id': 'd', 'project': 'three', 'created': 10}]
    saved = deepcopy(rows)
    assert removable(rows, 20, 10, 1) == ['a']
    assert rows == saved


def test_zero_minimum_sorted_and_empty():
    rows = [{'id': key, 'project': 'x', 'created': 1} for key in ['z', 'a']]
    assert removable(rows, 20, 10, 0) == ['a', 'z']
    assert removable([], 20, 10, 1) == []
    assert removable(rows, 20, 10, 5) == []
    assert removable(rows, 20, 10, 1) == ['z']
