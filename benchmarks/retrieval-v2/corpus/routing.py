def route_specificity(pattern):
    """An exact route outranks a directory prefix, which outranks the fallback."""
    return (0, 0) if pattern == '*' else ((1, len(pattern)) if pattern.endswith('/*') else (2, len(pattern)))


def matches_directory_prefix(path, prefix):
    """Directory boundary prevents /api from matching /apix."""
    return path == prefix.rstrip('/') or path.startswith(prefix.rstrip('/') + '/')
