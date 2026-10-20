"""Deadlock detection: cycle search (DFS) on the resource-allocation graph.
With single-instance resources, a cycle <=> deadlock."""


def find_cycle(rag):
    """Return a cycle like ['P1','R2','P2','R1','P1'] or None."""
    adj = rag.adjacency()
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in adj}
    path = []

    def dfs(u):
        color[u] = GREY
        path.append(u)
        for v in adj[u]:
            if color[v] == GREY:
                return path[path.index(v):] + [v]
            if color[v] == WHITE:
                found = dfs(v)
                if found:
                    return found
        path.pop()
        color[u] = BLACK
        return None

    for node in sorted(adj):
        if color[node] == WHITE:
            cycle = dfs(node)
            if cycle:
                return cycle
    return None


def deadlocked_processes(cycle):
    return sorted({n for n in cycle if n.startswith("P")})


def format_cycle(cycle):
    return " -> ".join(cycle)
