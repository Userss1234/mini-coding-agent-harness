class SingleFlight:
    """Coalesce concurrent work that shares one operation key."""

    def execute(self, operation_key: str, operation):
        raise NotImplementedError
