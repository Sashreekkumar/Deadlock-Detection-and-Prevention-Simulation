"""Resource-Allocation Graph (single-instance resources).

Edge types:
  request edge   : P -> R   (process P is waiting for resource R)
  assignment edge: R -> P   (resource R is held by process P)
"""


class RAG:
    def __init__(self):
        self.processes = []
        self.resources = []
        self.assigned = {}   # resource -> process
        self.requests = {}   # process  -> set(resources)

    def add_process(self, p):
        if p not in self.processes:
            self.processes.append(p)
            self.requests.setdefault(p, set())

    def add_resource(self, r):
        if r not in self.resources:
            self.resources.append(r)

    def holder(self, r):
        return self.assigned.get(r)

    def held_by(self, p):
        return [r for r, h in self.assigned.items() if h == p]

    def request(self, p, r):
        self.requests[p].add(r)

    def assign(self, r, p):
        self.requests[p].discard(r)
        self.assigned[r] = p

    def release(self, r):
        self.assigned.pop(r, None)

    def adjacency(self):
        adj = {n: [] for n in self.processes + self.resources}
        for p, rs in self.requests.items():
            adj[p].extend(sorted(rs))
        for r, p in self.assigned.items():
            adj[r].append(p)
        return adj

    def edges(self):
        out = []
        for p, rs in self.requests.items():
            out += [(p, r, "request") for r in sorted(rs)]
        out += [(r, p, "assign") for r, p in sorted(self.assigned.items())]
        return out
