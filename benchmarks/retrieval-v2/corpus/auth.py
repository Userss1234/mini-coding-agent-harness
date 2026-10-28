def bearer_header(headers):
    """Extract authentication token without renewing worker ownership."""
    return headers.get('Authorization', '').removeprefix('Bearer ')
