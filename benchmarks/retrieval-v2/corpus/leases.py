class Lease:
    """Fencing generation increases on acquisition; expired owners cannot renew."""

    def __init__(self, expires, generation):
        self.expires = expires
        self.generation = generation

    def renew(self, now, duration, expected_generation):
        if now >= self.expires or expected_generation != self.generation:
            return False
        self.expires = now + duration
        return True

    def expired(self, now):
        return now >= self.expires
