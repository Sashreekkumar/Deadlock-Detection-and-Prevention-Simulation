"""Draw the RAG with matplotlib (optional). Cycle edges are red."""
import math

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, Circle, Rectangle
    HAVE_MPL = True
except ImportError:
    HAVE_MPL = False


def draw_rag(processes, resources, edges, cycle, path, title=""):
    if not HAVE_MPL:
        return False
    nodes = []
    for i in range(max(len(processes), len(resources))):
        if i < len(processes):
            nodes.append(processes[i])
        if i < len(resources):
            nodes.append(resources[i])
    pos = {}
    for i, n in enumerate(nodes):
        a = 2 * math.pi * i / len(nodes) + math.pi / 2
        pos[n] = (math.cos(a), math.sin(a))

    cyc_edges = set(zip(cycle, cycle[1:])) if cycle else set()
    fig, ax = plt.subplots(figsize=(6, 6))
    for u, v, kind in edges:
        red = (u, v) in cyc_edges
        ax.add_patch(FancyArrowPatch(
            pos[u], pos[v], arrowstyle="-|>", mutation_scale=18,
            shrinkA=22, shrinkB=22, connectionstyle="arc3,rad=0.12",
            color="red" if red else "black", lw=2.2 if red else 1.4,
            linestyle="dashed" if kind == "request" else "solid"))
    for n, (x, y) in pos.items():
        if n in processes:
            ax.add_patch(Circle((x, y), 0.14, fc="#cfe8ff", ec="black", zorder=3))
        else:
            ax.add_patch(Rectangle((x - 0.12, y - 0.12), 0.24, 0.24,
                                   fc="#ffe9b3", ec="black", zorder=3))
        ax.text(x, y, n, ha="center", va="center", zorder=4, fontsize=11)
    ax.set_xlim(-1.5, 1.5)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title + "\nsolid: R->P assigned   dashed: P->R requested   red: cycle")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return True
