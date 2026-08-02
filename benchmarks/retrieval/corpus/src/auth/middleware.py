def extract_bearer_token(authorization: str) -> str:
    """Extract the bearer token used by authentication middleware."""
    scheme, token = authorization.split(" ", 1)
    if scheme.lower() != "bearer":
        raise ValueError("unsupported authentication scheme")
    return token
