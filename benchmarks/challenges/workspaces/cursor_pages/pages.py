def page(rows, after=None, size=2):
    start = 0 if after is None else after
    selected = rows[start:start + size]
    return selected, selected[-1]['id'] if selected else None
