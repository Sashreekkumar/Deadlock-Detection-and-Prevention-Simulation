"""Deadlock prevention by resource ordering (breaks the circular-wait condition).

Rule: every resource has a rank (R1=1, R2=2, ...). A process may request a
resource only if its rank is higher than the rank of every resource it holds.
"""


def rank(r):
    return int("".join(ch for ch in r if ch.isdigit()))


def order_needs(needs):
    """Acquire resources in ascending rank order."""
    return sorted(needs, key=rank)


def violates(held, r):
    """True if requesting r while holding `held` breaks the ordering rule."""
    return any(rank(h) > rank(r) for h in held)
