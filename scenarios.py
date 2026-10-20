"""Each process lists the resources it needs, in the order it would naturally
acquire them. It holds all of them, works for a few ticks, then releases."""

SCENARIOS = {
    "classic": {
        "desc": "P1 holds R1 wants R2; P2 holds R2 wants R1",
        "processes": {"P1": ["R1", "R2"], "P2": ["R2", "R1"]},
    },
    "chain3": {
        "desc": "3-process circular chain P1->P2->P3->P1",
        "processes": {"P1": ["R1", "R2"], "P2": ["R2", "R3"], "P3": ["R3", "R1"]},
    },
    "safe": {
        "desc": "No deadlock: both processes already acquire in the same order",
        "processes": {"P1": ["R1", "R2"], "P2": ["R1", "R2"]},
    },
}
