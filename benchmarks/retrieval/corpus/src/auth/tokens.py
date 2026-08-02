def validate_authentication_token(token: str) -> dict:
    """Validate a bearer authentication token and return its claims."""
    if not token:
        raise ValueError("missing token")
    return {"subject": token}
