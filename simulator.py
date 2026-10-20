"""Tick-based round-robin simulator for resource allocation."""
from graph import RAG
from detector import find_cycle, deadlocked_processes, format_cycle
from prevention import order_needs, violates

WORK_TICKS = 2


class _State:
    def __init__(self, needs):
        self.steps = ([("acquire", r) for r in needs]
                      + [("work", None)] * WORK_TICKS
                      + [("release", r) for r in reversed(needs)])
        self.pc = 0
        self.blocked_on = None

    @property
    def done(self):
        return self.pc >= len(self.steps)


class Simulator:
    def __init__(self, scenario, prevention=False, max_ticks=60):
        self.prevention = prevention
        self.max_ticks = max_ticks
        self.rag = RAG()
        self.state = {}
        self.log = []
        self.history = []   # (tick, edges, cycle)
        for p, needs in scenario["processes"].items():
            self.rag.add_process(p)
            for r in needs:
                self.rag.add_resource(r)
            if prevention:
                ordered = order_needs(needs)
                if ordered != needs:
                    self._log(0, f"{p}: ordering applied {needs} -> {ordered}")
                needs = ordered
            self.state[p] = _State(needs)

    def _log(self, tick, msg):
        self.log.append(f"[t={tick:02d}] {msg}")

    def _step(self, p, tick):
        st, rag = self.state[p], self.rag
        if st.blocked_on:
            r = st.blocked_on
            if rag.holder(r) is None:
                rag.assign(r, p)
                st.blocked_on = None
                st.pc += 1
                self._log(tick, f"{p} granted {r} (was waiting)")
            return
        kind, r = st.steps[st.pc]
        if kind == "acquire":
            if self.prevention and violates(rag.held_by(p), r):
                raise RuntimeError(f"{p} violates ordering on {r}")
            if rag.holder(r) is None:
                rag.assign(r, p)
                st.pc += 1
                self._log(tick, f"{p} acquires {r}")
            else:
                rag.request(p, r)
                st.blocked_on = r
                self._log(tick, f"{p} requests {r} held by {rag.holder(r)} -> BLOCKED")
        elif kind == "work":
            st.pc += 1
            self._log(tick, f"{p} working")
        else:
            rag.release(r)
            st.pc += 1
            self._log(tick, f"{p} releases {r}")
            if st.done:
                self._log(tick, f"{p} FINISHED")

    def run(self):
        status, cycle = "timeout", None
        for tick in range(1, self.max_ticks + 1):
            for p in self.rag.processes:
                if not self.state[p].done:
                    self._step(p, tick)
            cycle = find_cycle(self.rag)
            self.history.append((tick, self.rag.edges(), cycle))
            if cycle:
                status = "deadlock"
                self._log(tick, "DEADLOCK DETECTED: " + format_cycle(cycle)
                          + "  processes=" + ",".join(deadlocked_processes(cycle)))
                break
            if all(s.done for s in self.state.values()):
                status = "completed"
                self._log(tick, "All processes completed - no deadlock")
                break
        return {"status": status, "ticks": len(self.history), "cycle": cycle}
