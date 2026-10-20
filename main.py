"""Deadlock detection & prevention simulator.

Usage:
  python main.py                       # all scenarios, both modes
  python main.py --scenario classic --mode detect
  python main.py --scenario chain3 --mode prevent --plot-all
"""
import argparse
import os

from scenarios import SCENARIOS
from simulator import Simulator
from visualize import draw_rag, HAVE_MPL

OUT = "output"


def run_one(name, prevention, plot, plot_all):
    sc = SCENARIOS[name]
    mode = "PREVENT (resource ordering)" if prevention else "DETECT (no prevention)"
    print(f"\n=== {name}: {sc['desc']} | mode: {mode} ===")
    sim = Simulator(sc, prevention=prevention)
    res = sim.run()
    print("\n".join(sim.log))
    print(f"RESULT: {res['status'].upper()} after {res['ticks']} ticks")

    if plot and HAVE_MPL:
        os.makedirs(OUT, exist_ok=True)
        tag = "prevent" if prevention else "detect"
        frames = sim.history if plot_all else [sim.history[-1]]
        for tick, edges, cycle in frames:
            path = f"{OUT}/{name}_{tag}_t{tick:02d}.png"
            draw_rag(sim.rag.processes, sim.rag.resources, edges, cycle, path,
                     f"{name} [{tag}] tick {tick}")
            print("saved", path)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="all", choices=["all"] + list(SCENARIOS))
    ap.add_argument("--mode", default="both", choices=["detect", "prevent", "both"])
    ap.add_argument("--no-plot", action="store_true")
    ap.add_argument("--plot-all", action="store_true", help="save a PNG for every tick")
    a = ap.parse_args()

    names = list(SCENARIOS) if a.scenario == "all" else [a.scenario]
    modes = {"detect": [False], "prevent": [True], "both": [False, True]}[a.mode]
    if not a.no_plot and not HAVE_MPL:
        print("(matplotlib not installed: skipping graph images; pip install matplotlib)")

    summary = []
    for n in names:
        for prev in modes:
            r = run_one(n, prev, not a.no_plot, a.plot_all)
            summary.append((n, "prevent" if prev else "detect", r["status"], r["ticks"]))

    print("\n=== SUMMARY ===")
    print(f"{'scenario':<10}{'mode':<10}{'result':<12}{'ticks'}")
    for s in summary:
        print(f"{s[0]:<10}{s[1]:<10}{s[2]:<12}{s[3]}")


if __name__ == "__main__":
    main()
