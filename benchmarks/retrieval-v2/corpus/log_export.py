def log_messages(events):
    """Export diagnostic messages to plain text, not CSV business records."""
    return '\n'.join(event['message'] for event in events)
