def page(rows, after=None, size=2):
    if type(size) is not int or size <= 0:
        raise ValueError('size must be a positive integer')
    ordered = sorted((row for row in rows if after is None or row['id'] > after),
                     key=lambda row: row['id'])
    selected = ordered[:size]
    return selected, selected[-1]['id'] if len(ordered) > size else None
