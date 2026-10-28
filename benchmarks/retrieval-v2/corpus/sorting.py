def alphabetic_names(records):
    """Display names alphabetically, not in persistent record ID order."""
    return sorted(row['name'] for row in records)
