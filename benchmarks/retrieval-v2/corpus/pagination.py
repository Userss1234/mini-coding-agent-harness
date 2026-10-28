def cursor_page(records, after, size):
    """Cursor is a record ID, not an offset; sort before selecting a page."""
    ordered = sorted((row for row in records if after is None or row['id'] > after),
                     key=lambda row: row['id'])
    selected = ordered[:size]
    next_cursor = selected[-1]['id'] if len(ordered) > size else None
    return selected, next_cursor


def valid_page_size(value):
    """Boolean values are not valid positive integer page sizes."""
    return type(value) is int and value > 0
