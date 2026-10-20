# Deadlock Detection and Prevention Simulator

A two-part project that demonstrates **deadlock** in a multi-process system, **detects** it with a
resource-allocation graph (RAG), and **prevents** it with **resource ordering**.

| Part | Where it runs | Purpose |
|------|---------------|---------|
| Python simulator | Any PC | Deterministic, step-by-step simulation, graph drawing, multiple scenarios |
| FreeRTOS demo | ESP32 (or Wokwi online simulator) | Same idea on a real RTOS with real tasks and mutexes |

---

## 1. What the code does, and why

### 1.1 The problem: deadlock

A **deadlock** is a state where a set of processes are all blocked forever, each waiting for a resource
held by another process in the set.

The example used throughout the project:

```
P1 holds R1 and requests R2
P2 holds R2 and requests R1
```

Neither can continue: P1 waits for P2 to release R2, and P2 waits for P1 to release R1.

A deadlock needs **all four Coffman conditions** at the same time:

1. **Mutual exclusion** – a resource can be held by only one process at a time.
2. **Hold and wait** – a process holds some resources while waiting for others.
3. **No preemption** – resources cannot be forcibly taken away.
4. **Circular wait** – there is a closed chain of processes, each waiting for a resource held by the next.

Breaking any one condition prevents deadlock. This project breaks **circular wait**.

### 1.2 The model: resource-allocation graph (RAG)

The system state is stored as a directed graph with two kinds of nodes and two kinds of edges:

| Edge | Direction | Meaning |
|------|-----------|---------|
| Request edge | `P -> R` | Process P is waiting for resource R |
| Assignment edge | `R -> P` | Resource R is currently held by process P |

For the example above the graph is:

```
P1 -> R2 -> P2 -> R1 -> P1        (a cycle)
```

### 1.3 Detection: how the deadlock is found

With **single-instance resources** (one copy of each resource), the rule is:

> **A cycle in the RAG means a deadlock.**

The detector runs a **depth-first search (DFS)** with three node colours (white = unvisited,
grey = on the current path, black = finished). If the search reaches a grey node again, it has found a
back edge, i.e. a cycle. The cycle is returned as a list such as `['P1','R2','P2','R1','P1']`, and the
processes in it are the deadlocked ones.

In Python the detector runs after every simulation tick. On the ESP32 a monitor task checks every 300 ms.

### 1.4 Prevention: how the deadlock is avoided

**Resource ordering** gives every resource a number (R1 = 1, R2 = 2, ...) and enforces one rule:

> A process may request a resource only if its number is **higher** than every resource it already holds.

In practice this means every process acquires resources in **ascending order**. P2, which naturally
wants `R2` then `R1`, is made to acquire `R1` then `R2` instead.

Why this works: a circular wait needs some process holding a *high* resource while waiting for a *low*
one. The rule makes that impossible, so no cycle can ever form, and the circular-wait condition can
never hold.

### 1.5 What happens, step by step

**Python (`classic` scenario, no prevention)**

```
t=01  P1 acquires R1
t=01  P2 acquires R2
t=02  P1 requests R2 (held by P2) -> BLOCKED
t=02  P2 requests R1 (held by P1) -> BLOCKED
t=02  DEADLOCK DETECTED: P1 -> R2 -> P2 -> R1 -> P1
```

**Python (`classic` scenario, with prevention)**

```
t=00  P2: ordering applied ['R2','R1'] -> ['R1','R2']
t=01  P1 acquires R1
t=01  P2 requests R1 (held by P1) -> BLOCKED     (waiting, but no cycle)
...   P1 finishes and releases everything, then P2 gets R1 and R2 and finishes
      All processes completed - no deadlock
```

**FreeRTOS (ESP32)**

- **Phase A – no prevention.** Tasks P1 and P2 start each round together (an event-group barrier),
  take their first mutex, wait 500 ms, then try to take the second one. They deadlock. The monitor task
  detects the cycle and prints it. The tasks use a **timeout** on the second mutex (3 s), so they
  release the first resource and back off (recovery). This repeats for 3 rounds.
- **Phase B – prevention.** The monitor switches on resource ordering. Both tasks now take R1 then R2.
  One of them simply waits for the other, and all 3 rounds complete with no deadlock.
- A final `=== SUMMARY ===` line is printed.

> Note: the timeout in Phase A is a **recovery** mechanism, not prevention. Prevention is the ordering
> rule in Phase B.

---

## 2. Project layout and what each file does

```
deadlock_sim/
├── README.md
├── python/
│   ├── main.py
│   ├── graph.py
│   ├── detector.py
│   ├── prevention.py
│   ├── simulator.py
│   ├── scenarios.py
│   └── visualize.py
└── freertos_esp32/
    └── freertos_esp32.ino
```

### Python files

| File | Role |
|------|------|
| `graph.py` | The `RAG` class. Stores which process holds which resource (assignment edges) and which process waits for which (request edges). Provides `assign`, `release`, `request`, `holder`, `held_by`, `adjacency`, `edges`. |
| `detector.py` | `find_cycle(rag)`: DFS cycle detection. Also `deadlocked_processes(cycle)` and `format_cycle(cycle)` for printing. |
| `prevention.py` | The resource-ordering policy: `rank(r)` (number in the resource name), `order_needs(needs)` (sort ascending), `violates(held, r)` (check the ordering rule). |
| `simulator.py` | The tick-based, round-robin simulator. Each process runs the program *acquire all needs, work 2 ticks, release all in reverse*. Grants free resources, blocks processes on busy ones, runs the detector after every tick, and stops on deadlock or completion. Applies ordering when prevention mode is on. |
| `scenarios.py` | The test cases (`classic`, `chain3`, `safe`). Each process lists the resources it needs in its natural order. Add your own here. |
| `visualize.py` | Draws the RAG with matplotlib (processes = circles, resources = squares, dashed = request, solid = assignment, **red = cycle**). Optional: skipped automatically if matplotlib is missing. |
| `main.py` | Command-line entry point. Runs the chosen scenarios and modes, prints the timeline log, saves graph images to `output/`, and prints a summary table. |

### FreeRTOS file

| File | Role |
|------|------|
| `freertos_esp32.ino` | The whole ESP32 demo in one sketch. Key parts below. |

Key parts of the sketch:

| Part | What it does |
|------|--------------|
| `resMutex[]` | The resources R1, R2 as FreeRTOS mutexes |
| `holderOf[]`, `waitingFor[]` | A hand-built RAG (FreeRTOS has no built-in deadlock detection) |
| `acquire()` / `releaseRes()` | Wrappers that update the graph, log events, apply a timeout, and enforce the ordering rule in prevention mode |
| `procTask` | Tasks P1 and P2 (the "processes") |
| `monitorTask` | Higher-priority task that snapshots the graph every 300 ms, detects cycles, switches to prevention after 3 deadlocks, and prints the summary |
| `xEventGroupSync` | Barrier that makes both tasks start each round together so the deadlock is reproducible |

---

## 3. How to run

### Python

Requires Python 3.8+. Matplotlib is optional (graph images only).

```bash
cd python
pip install matplotlib                          # optional
python main.py                                  # all scenarios, both modes
python main.py --scenario classic --mode detect
python main.py --scenario chain3 --mode prevent --plot-all
python main.py --no-plot                        # text only
```

| Option | Meaning |
|--------|---------|
| `--scenario` | `classic`, `chain3`, `safe`, or `all` (default) |
| `--mode` | `detect` (no prevention), `prevent` (resource ordering), or `both` (default) |
| `--plot-all` | Save a graph image for every tick (default: only the final state) |
| `--no-plot` | Skip image output |

Images are written to `python/output/`.

### FreeRTOS on ESP32

1. **Real board:** Arduino IDE, install the *esp32 by Espressif* board package, select your ESP32 board,
   upload `freertos_esp32.ino`.
2. **No hardware:** create a new ESP32 project on [wokwi.com](https://wokwi.com), paste the sketch into
   `sketch.ino`, and press Play. No wiring is needed.
3. Open the Serial Monitor at **115200 baud**.

Expected output (shape; timings will vary):

```
=== PHASE A: NO PREVENTION (deadlock expected) ===
P1 requests R1 / P2 requests R2 / both acquired
P1 requests R2 / P2 requests R1
*** DEADLOCK DETECTED (#1): P1 -> R2 -> P2 -> R1 -> P1
P1 TIMEOUT waiting for R2 ... recovery: releasing R1 and backing off
... (repeats 3 times)
=== PHASE B: RESOURCE ORDERING PREVENTION ENABLED ===
P2 applies resource ordering: R1 before R2
... rounds complete, no deadlock
=== SUMMARY: Phase A deadlocks detected = 3, Phase B deadlocks = 0 ... ===
```

---

## 4. Test cases and expected results

| Scenario | Description | No prevention | With ordering |
|----------|-------------|---------------|---------------|
| `classic` | P1: R1,R2 / P2: R2,R1 | **Deadlock** at tick 2 | Completes (11 ticks) |
| `chain3` | P1: R1,R2 / P2: R2,R3 / P3: R3,R1 | **Deadlock** at tick 2 (3-process cycle) | Completes (16 ticks) |
| `safe` | P1: R1,R2 / P2: R1,R2 | Completes (11 ticks) | Completes (11 ticks) |

The `safe` case shows that waiting is not the same as deadlock: P2 is blocked for a while, but no cycle
exists, so it eventually runs.

---

## 5. Adding your own scenario

Edit `python/scenarios.py`:

```python
"my_case": {
    "desc": "my description",
    "processes": {"P1": ["R1", "R3"], "P2": ["R3", "R2"], "P3": ["R2", "R1"]},
},
```

Then run `python main.py --scenario my_case`. Resource names must end in a number (R1, R2, ...) because
the ordering rank is read from that number.

---

## 6. Assumptions and limitations

- **Single-instance resources.** "Cycle = deadlock" is exact only in this case. With several instances
  of a resource, a cycle is necessary but not sufficient; you would use the Banker's algorithm or a
  wait-for-graph reduction instead.
- **Fixed process programs.** Each process acquires everything it needs, works, then releases. There
  are no dynamic request patterns.
- **Round-robin ticks.** The Python scheduler gives each process one action per tick, in order P1, P2,
  P3. Different scheduling could change the interleaving (and in some interleavings an unordered
  scenario may not deadlock; the order used here exposes the deadlock reliably).
- **Prevention has a cost.** Ordering can force a process to acquire a resource earlier than it needs
  it, which can reduce concurrency. Choosing a sensible global order matters.
- **ESP32 timings** (500 ms hold delay, 3 s timeout, 300 ms monitor period) are tuned for readable
  output, not performance. The exact millisecond values in your log will differ from run to run.
- **Detection in FreeRTOS is cooperative.** The monitor only sees what the `acquire()` wrapper records;
  code that calls `xSemaphoreTake` directly would be invisible to it.
- **Recovery vs prevention.** The timeout-and-release in Phase A recovers from a deadlock after it
  happens. Resource ordering in Phase B stops it from happening at all.

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: matplotlib` | `pip install matplotlib`, or run with `--no-plot` |
| No images appear | Check the `python/output/` folder; images are saved, not displayed |
| Nothing prints on ESP32 | Set the Serial Monitor to 115200 baud, press the board's reset/EN button |
| Compile error on `freertos/...` headers | Make sure the board selected is an ESP32 (not Arduino Uno/Nano) |
| Phase B never starts | Phase A must detect 3 deadlocks first; wait roughly 25 to 30 seconds |

---

<!-- ## 8. Material to include in the report

- The four Coffman conditions and which one is broken (circular wait).
- The RAG model and the cycle-detection algorithm (DFS), with its complexity O(V + E).
- Console output and graph images from the Python runs (deadlock case in red, prevented case).
- The Serial Monitor log from the ESP32 showing Phase A (detection and recovery) and Phase B
  (prevention).
- The comparison table from section 4, and a short discussion of the limitations in section 6. -->