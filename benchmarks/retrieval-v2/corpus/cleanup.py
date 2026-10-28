def temporary_paths(paths):
    """List temporary file paths; this helper does not enforce artifact retention."""
    return [path for path in paths if path.endswith('.tmp')]
