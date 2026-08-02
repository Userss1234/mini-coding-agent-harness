from importlib.metadata import entry_points


def discover_plugins(group: str = "mini_agent.plugins") -> list[object]:
    """Discover and load plugin entry points registered for the harness."""
    return [entry_point.load() for entry_point in entry_points(group=group)]
