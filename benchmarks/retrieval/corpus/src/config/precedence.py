def resolve_config(defaults: dict, config_file: dict, environment_variables: dict) -> dict:
    """Apply defaults, then config file values, then environment variable overrides."""
    return defaults | config_file | environment_variables
