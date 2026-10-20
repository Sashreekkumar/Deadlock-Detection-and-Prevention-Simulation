# Deadlock Detection and Prevention Simulator

A two-part project demonstrating **deadlock creation, detection, recovery, and prevention** in a concurrent system. The project combines a Python-based resource-allocation graph (RAG) simulator with a FreeRTOS demonstration running on an ESP32 or in the Wokwi online simulator.

| Part | Where it runs | Purpose |
|---|---|---|
| Python simulator | Any PC | Tick-based simulation, graph drawing, cycle detection, and multiple scenarios |
| FreeRTOS demo | ESP32 or Wokwi | Demonstrates concurrent RTOS tasks, mutexes, deadlock detection, recovery, and resource-ordering prevention |

---

## 1. Project Objectives

- Understand deadlocks in multitasking operating systems.
- Represent resource allocation and requests using a resource-allocation graph.
- Detect cycles and identify deadlocked processes.
- Demonstrate timeout-based recovery after deadlock occurs.
- Prevent circular wait through resource ordering.
- Compare system behavior with and without prevention.
- Demonstrate these concepts through Python and FreeRTOS.

## 2. Theoretical Background

### 2.1 What is deadlock?

A **deadlock** occurs when a group of processes cannot proceed because each process is waiting for a resource held by another process in the group.

The classic example used in this project is:

```text
P1 holds R1 and requests R2
P2 holds R2 and requests R1
```

P1 cannot proceed until P2 releases R2, while P2 cannot proceed until P1 releases R1.

### 2.2 The four Coffman conditions

Deadlock is associated with four necessary conditions:

1. **Mutual exclusion:** A resource can be held by only one process at a time.
2. **Hold and wait:** A process holds at least one resource while waiting for another.
3. **No preemption:** A resource cannot be forcibly taken away from a process; in this demonstration, the tasks release their resources during recovery.
4. **Circular wait:** A closed chain exists in which each process waits for a resource held by the next process.

This project prevents deadlock by breaking the **circular-wait condition** through a global resource-acquisition order.

### 2.3 Resource-allocation graph (RAG)

The resource-allocation graph represents processes and resources using directed edges.

| Edge | Meaning |
|---|---|
| `P -> R` | Process P requests or waits for resource R |
| `R -> P` | Resource R is allocated to process P |

The classic deadlock creates the following cycle:

```text
P1 -> R2 -> P2 -> R1 -> P1
```

P1 waits for R2, which is held by P2. P2 waits for R1, which is held by P1.

For the single-instance resources in this scenario, a cycle indicates deadlock. With multiple instances of a resource type, a cycle alone is not generally sufficient to prove deadlock.

### 2.4 Deadlock detection

**Python simulator**

The Python detector uses depth-first search (DFS) with three node states:

- White: unvisited.
- Grey: currently on the DFS path.
- Black: completely explored.

If DFS reaches a grey node again, it has found a cycle. The cycle may be reported as:

```python
['P1', 'R2', 'P2', 'R1', 'P1']
```

DFS cycle detection has time complexity \(O(V+E)\), where \(V\) is the number of vertices and \(E\) is the number of edges.

**FreeRTOS demonstration**

FreeRTOS does not automatically detect arbitrary application-level deadlocks. The sketch maintains its own resource-allocation information:

- `holderOf[]`: Records the process holding each resource.
- `waitingFor[]`: Records the resource each process is waiting for.

A monitor task checks the recorded relationships approximately every 300 ms and reports a cycle when it detects one.

### 2.5 Deadlock prevention using resource ordering

Each resource is assigned a rank:

```text
R1 < R2 < R3 < ...
```

A process may request a resource only if its rank is higher than every resource it already holds. In other words, all processes must acquire resources in ascending order.

For example:

```text
Original order for P2: R2 -> R1
Enforced order for P2: R1 -> R2
```

This prevents a process holding a higher-ranked resource from waiting for a lower-ranked resource. Therefore, a circular wait cannot form as long as all relevant resource acquisitions obey the global ordering rule.

**Important distinction:** A timeout is a recovery mechanism, not a prevention mechanism. Phase A permits deadlock and recovers from it; Phase B prevents circular wait through resource ordering.

## 3. Project Structure

The project can be organized as follows:

```text
Deadlock-Detection-Prevention/
├── README.md
├── python/
│   ├── main.py
│   ├── graph.py
│   ├── detector.py
│   ├── prevention.py
│   ├── simulator.py
│   ├── scenarios.py
│   ├── visualize.py
│   └── output/
├── freertos_esp32/
│   └── freertos_esp32.ino
└── screenshots/
    ├── deadlock-detection.png
    ├── deadlock-recovery.png
    ├── resource-ordering.png
    └── final-summary.png
```

For Wokwi, the FreeRTOS sketch can be pasted into the default `sketch.ino` file. If you keep the sketch at the repository root instead, adjust the structure accordingly.

### 3.1 Python files

| File | Responsibility |
|---|---|
| `graph.py` | Implements the `RAG` class and stores assignment and request edges. Provides `assign`, `release`, `request`, `holder`, `held_by`, `adjacency`, and `edges`. |
| `detector.py` | Implements `find_cycle(rag)`, `deadlocked_processes(cycle)`, and `format_cycle(cycle)`. |
| `prevention.py` | Implements resource-ordering helpers such as `rank(r)`, `order_needs(needs)`, and `violates(held, r)`. |
| `simulator.py` | Runs the tick-based, round-robin simulation. Processes acquire resources, perform work, release resources, and are checked for deadlock. |
| `scenarios.py` | Defines the `classic`, `chain3`, and `safe` scenarios. |
| `visualize.py` | Optionally draws resource-allocation graphs using Matplotlib. |
| `main.py` | Command-line entry point that runs scenarios, prints timelines, saves graph images, and displays summary results. |

### 3.2 FreeRTOS components

| Component | Responsibility |
|---|---|
| `resMutex[]` | Represents R1 and R2 using FreeRTOS mutexes. |
| `holderOf[]`, `waitingFor[]` | Store ownership and waiting information for the application's resource-allocation graph. |
| `acquire()` | Logs requests, records waiting state, applies timeouts, and enforces resource ordering during prevention. |
| `releaseRes()` | Updates resource ownership and releases the corresponding mutex. |
| `procTask` | Implements the P1 and P2 tasks. |
| `monitorTask` | Checks the graph, reports cycles, enables prevention after three detected deadlocks, and prints the final summary. |
| `xEventGroupSync()` | Synchronizes task starts at round boundaries to make the initial deadlock scenario reproducible. |

## 4. Python Simulator: How to Run

### 4.1 Requirements

- Python 3.8 or later.
- Matplotlib is optional and used for graph image generation.

Navigate to the Python directory:

```bash
cd python
```

Install Matplotlib if graph visualization is required:

```bash
pip install matplotlib
```

Run all scenarios in both modes:

```bash
python main.py
```

Run the classic scenario without prevention:

```bash
python main.py --scenario classic --mode detect
```

Run the three-process scenario with prevention and graph output for every tick:

```bash
python main.py --scenario chain3 --mode prevent --plot-all
```

Run without graph output:

```bash
python main.py --no-plot
```

### 4.2 Command-line options

| Option | Meaning |
|---|---|
| `--scenario` | `classic`, `chain3`, `safe`, or `all` (default) |
| `--mode` | `detect`, `prevent`, or `both` (default) |
| `--plot-all` | Save a graph image for every tick rather than only the final state |
| `--no-plot` | Disable graph image output |

Graph images are saved to `python/output/`.

### 4.3 Test scenarios

| Scenario | Resource requirements | Without prevention | With resource ordering |
|---|---|---|---|
| `classic` | P1: R1, R2; P2: R2, R1 | Designed to demonstrate a two-process deadlock | Expected to complete without deadlock |
| `chain3` | P1: R1, R2; P2: R2, R3; P3: R3, R1 | Designed to demonstrate a three-process cycle | Expected to complete without deadlock |
| `safe` | P1: R1, R2; P2: R1, R2 | Expected to complete; waiting does not necessarily imply deadlock | Expected to complete without deadlock |

The exact tick counts depend on the supplied implementation and its scheduling order. Use the actual program output when documenting execution results.

### 4.4 Example Python behavior

Without prevention, the classic scenario is expected to produce a sequence similar to:

```text
P1 acquires R1
P2 acquires R2
P1 requests R2 -> blocked
P2 requests R1 -> blocked
DEADLOCK DETECTED: P1 -> R2 -> P2 -> R1 -> P1
```

With prevention, P2's resource order is changed:

```text
P2: ['R2', 'R1'] -> ['R1', 'R2']
P1 acquires R1
P2 waits for R1
P1 acquires R2 and completes
P1 releases its resources
P2 acquires R1 and R2 and completes
```

The second sequence contains waiting but no circular wait. A process waiting for a resource is not necessarily deadlocked.

## 5. FreeRTOS Demonstration on ESP32 or Wokwi

### 5.1 Running on Wokwi

1. Open [Wokwi](https://wokwi.com/) and create an ESP32 Arduino project.
2. Paste the FreeRTOS implementation into `sketch.ino`.
3. No external components or wiring are required.
4. Click **Start Simulation**.
5. Open the Serial Monitor and set the baud rate to **115200**.
6. Let the simulation continue through Phase A and Phase B until the final summary appears.

### 5.2 Running on a physical ESP32

1. Install the Arduino IDE and the ESP32 board package by Espressif.
2. Open the sketch and select the appropriate ESP32 board and serial port.
3. Upload the sketch.
4. Open the Serial Monitor at 115200 baud.
5. Observe the deadlock detection, recovery, prevention, and summary messages.

### 5.3 Phase A: No prevention

During Phase A, P1 and P2 start each round together using an event-group barrier. P1 first acquires R1, while P2 first acquires R2. After a delay, each requests the resource held by the other.

The monitor detects the circular dependency. The tasks then time out while waiting for their second mutex, release their first resources, and retry. The cycle is reproduced three times.

### 5.4 Phase B: Resource ordering

After three deadlocks have been detected and the cycle has cleared, the monitor enables resource ordering.

Both tasks now acquire R1 before R2. One task may wait for the other, but the circular-wait condition cannot arise under this ordering policy. Each process completes three successful rounds, and the monitor prints the final summary.

## 6. Experimental Results from Wokwi

The following results were observed in the captured ESP32 Serial Monitor output.

### 6.1 Deadlock detection

The first deadlock was reported at approximately 2.102 seconds:

```text
[  1502 ms] P2 acquired R2
[  1513 ms] P1 acquired R1
[  2012 ms] P2 requests R1
[  2013 ms] P1 requests R2
[  2102 ms] *** DEADLOCK DETECTED (#1):
             P1 -> R2 -> P2 -> R1 -> P1
```

This confirms that each task held one resource and waited for the resource held by the other.

### 6.2 Deadlock recovery

The first recovery sequence was:

```text
[  5012 ms] P2 TIMEOUT waiting for R1
[  5013 ms] P1 TIMEOUT waiting for R2
[  5013 ms] P2 recovery: releasing R2 and backing off
[  5023 ms] P1 recovery: releasing R1 and backing off
```

Both tasks timed out, released their held resources, and backed off before retrying.

### 6.3 Deadlock detection timestamps

| Deadlock | Detection time in captured log | Observed outcome |
|---|---:|---|
| 1 | 2.102 s | Detected; timeout recovery followed |
| 2 | 7.202 s | Detected; timeout recovery followed |
| 3 | 12.302 s | Detected; timeout recovery followed |

The timestamps are elapsed simulator times from the captured log. They may vary in subsequent runs.

### 6.4 Prevention enabled

After the third deadlock was recovered, the monitor enabled prevention:

```text
[ 15301 ms] === PHASE B: RESOURCE ORDERING PREVENTION ENABLED ===
[ 16546 ms] P2 applies resource ordering: R1 before R2
```

P1 subsequently acquired both resources and entered its critical section:

```text
[ 17045 ms] P1 requests R2
[ 17046 ms] P1 acquired R2
[ 17046 ms] P1 in critical section (holds R1 and R2)
[ 17346 ms] P1 released R2
[ 17347 ms] P1 released R1
[ 17347 ms] P1 round complete
```

P2 also completed its critical section using the same resource order. This process alternation continued until each task completed three rounds.

### 6.5 Final observed summary

The final Serial Monitor output reported:

```text
[ 22501 ms] === SUMMARY:
Phase A deadlocks detected = 3,
Phase B deadlocks = 0,
rounds completed per process = 3 ===
[ 22884 ms] P2 finished all rounds
```

The captured results are summarized below.

| Measurement | Observed result |
|---|---:|
| Number of process tasks | 2 |
| Number of shared resources | 2 |
| Deadlocks detected in Phase A | 3 |
| Deadlocks reported in Phase B | 0 |
| Successful Phase B rounds completed by P1 | 3 |
| Successful Phase B rounds completed by P2 | 3 |
| Total successful Phase B process-rounds | 6 |

**Interpretation:** The captured run demonstrates that the unordered acquisition pattern repeatedly produced a circular wait and that timeout recovery broke each occurrence. After resource ordering was enabled, both processes completed three rounds and the monitor reported zero deadlocks in Phase B.

This is the result of the observed run, not a proof that every possible concurrent program is deadlock-free.

## 7. Python and FreeRTOS Comparison

| Feature | Python simulator | FreeRTOS demonstration |
|---|---|---|
| Execution model | Tick-based, deterministic simulation | Concurrent RTOS tasks |
| Resources | Graph-modelled resources | FreeRTOS mutexes |
| Deadlock detection | DFS cycle detection | Monitor examines recorded ownership and waiting relationships |
| Recovery | Depends on the Python simulator's modeled behavior | Timeout, release, and retry |
| Prevention | Reorders resource requirements | Enforces resource ordering in the acquisition wrapper |
| Visualization | Optional graph images using Matplotlib | Serial Monitor logs |
| Main purpose | Explore graph states and alternative scenarios | Demonstrate the concepts with RTOS synchronization primitives |

The Python version helps explore different resource dependencies, while the FreeRTOS version demonstrates how concurrent tasks interact with mutexes.

## 8. Adding a Python Scenario

Edit `python/scenarios.py` and add an entry following the existing scenario structure:

```python
"my_case": {
    "desc": "Example three-process resource dependency",
    "processes": {
        "P1": ["R1", "R3"],
        "P2": ["R3", "R2"],
        "P3": ["R2", "R1"]
    },
},
```

Run it using:

```bash
python main.py --scenario my_case
```

Resource names should end in a number, such as `R1`, `R2`, and `R3`, because the ordering policy derives resource ranks from the number in the name.

## 9. Assumptions and Limitations

- **Single-instance resources:** The rule that a cycle implies deadlock applies to the single-instance scenario. With multiple resource instances, a cycle alone is not generally sufficient to establish deadlock.
- **Fixed process programs:** The example processes follow predefined resource-acquisition sequences rather than arbitrary dynamic request patterns.
- **Scheduling:** Different process interleavings can affect when a deadlock occurs. The Python scheduler follows its own tick and process-order rules.
- **Prevention trade-off:** Resource ordering may reduce concurrency because a process can be required to acquire a resource earlier than it otherwise would.
- **Simulation timings:** ESP32 delays and timeouts are selected to make behavior visible in Wokwi, not to benchmark real-time performance.
- **Cooperative graph tracking:** The FreeRTOS monitor sees requests and ownership changes recorded by the sketch. Mutex operations that bypass the wrapper would not be represented correctly in its graph.
- **Recovery versus prevention:** Timeouts recover from deadlocks after they occur. Resource ordering prevents circular wait when consistently followed.
- **Scope of results:** The observed successful Phase B run validates this scenario and the implemented ordering policy, not every possible resource interaction in a larger system.

## 10. Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: matplotlib` | Run `pip install matplotlib`, or use `python main.py --no-plot`. |
| Graph images do not appear in the terminal | Check `python/output/`; the supplied implementation saves graph images to files. |
| No ESP32 output | Ensure the simulation is running and the Serial Monitor is set to 115200 baud. |
| Compilation errors involving ESP32/FreeRTOS headers | Select an ESP32 board rather than an AVR-based Arduino Uno or Nano. |
| Phase B never starts | Phase A must detect three deadlocks and the cycle must clear. Inspect the Serial Monitor for errors or stalled tasks. |
| Final summary is missing | Let the simulation continue. If it remains stuck, inspect the event-group barrier and task-exit logic. |

## 11. Screenshots and Report Evidence

Store screenshots of the Wokwi Serial Monitor in the `screenshots/` directory.

| Screenshot | What it should show |
|---|---|
| `deadlock-detection.png` | The first `DEADLOCK DETECTED` message and the cycle `P1 -> R2 -> P2 -> R1 -> P1` |
| `deadlock-recovery.png` | Timeout messages, resource releases, and backoff |
| `resource-ordering.png` | The Phase B transition and P2's resource-ordering message |
| `final-summary.png` | Three Phase A deadlocks, zero Phase B deadlocks, and three rounds completed per process |

If you have run the Python simulator, also include representative RAG images from `python/output/` showing a deadlock cycle and a completed execution with prevention.

### Suggested discussion for the project report

Explain the four Coffman conditions, the RAG representation, and the cycle-detection algorithm. Then distinguish detection, recovery, and prevention. Use the Python graph images to illustrate resource dependencies and the Wokwi screenshots to document the actual RTOS behavior. Include the observed results table and discuss the assumptions and limitations.

## 12. Conclusion

This project demonstrates deadlock detection, recovery, and prevention using a Python simulator and a FreeRTOS-based ESP32 implementation.

In the captured Wokwi experiment, the monitor detected three deadlocks while processes acquired resources in opposite orders. Timeout-based recovery released the held resources and allowed execution to continue. After resource ordering was enabled, both tasks acquired resources in the same order, completed three rounds each, and the final summary reported zero deadlocks in Phase B.

The experiment illustrates how a resource-allocation graph can expose circular wait and how a consistent global resource order can prevent circular wait in the modeled system.
