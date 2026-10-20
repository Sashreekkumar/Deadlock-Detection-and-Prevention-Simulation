/*
 * Deadlock Detection & Prevention demo on FreeRTOS (ESP32, Arduino core)
 *
 * Resources : R1, R2  (FreeRTOS mutexes)
 * Processes : P1 (needs R1 then R2), P2 (needs R2 then R1)  -> FreeRTOS tasks
 * Monitor   : builds the resource-allocation graph and detects a cycle
 *
 * Phase A (no prevention)      : tasks deadlock DEADLOCK_ROUNDS times, the
 *                                monitor detects the cycle, tasks recover
 *                                through a timeout.
 * Phase B (resource ordering)  : each task acquires resources in ascending
 *                                order (R1 before R2) -> no deadlock.
 *
 * Run: Arduino IDE (ESP32 board) or Wokwi (ESP32). Serial monitor 115200.
 */
#include <Arduino.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "freertos/event_groups.h"
#include <stdarg.h>

#define NUM_PROC        2
#define NUM_RES         2
#define DEADLOCK_ROUNDS 3     // rounds of Phase A
#define OK_ROUNDS       3     // rounds of Phase B

SemaphoreHandle_t resMutex[NUM_RES];
SemaphoreHandle_t logMutex;
EventGroupHandle_t syncGroup;
portMUX_TYPE graphMux = portMUX_INITIALIZER_UNLOCKED;

// Resource-allocation graph state
volatile int holderOf[NUM_RES];     // resource -> process (-1 = free)   (assignment edge R->P)
volatile int waitingFor[NUM_PROC];  // process  -> resource (-1 = none)  (request edge  P->R)

volatile bool prevention = false;
volatile int  deadlockCount = 0;
volatile int  okRounds[NUM_PROC] = {0, 0};

// natural (unordered) acquisition order of each process
const int firstNeed[NUM_PROC]  = {0, 1};   // P1: R1 first, P2: R2 first
const int secondNeed[NUM_PROC] = {1, 0};   // P1: R2 second, P2: R1 second

void logMsg(const char *fmt, ...) {
  char buf[160];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(buf, sizeof(buf), fmt, ap);
  va_end(ap);
  xSemaphoreTake(logMutex, portMAX_DELAY);
  Serial.printf("[%7lu ms] %s\n", (unsigned long)millis(), buf);
  xSemaphoreGive(logMutex);
}

void setWaiting(int p, int r) {
  portENTER_CRITICAL(&graphMux);
  waitingFor[p] = r;
  portEXIT_CRITICAL(&graphMux);
}

void setHolder(int r, int p) {
  portENTER_CRITICAL(&graphMux);
  holderOf[r] = p;
  portEXIT_CRITICAL(&graphMux);
}

// Acquire resource r for process p. Enforces the ordering rule in prevention mode.
bool acquire(int p, int r, TickType_t timeout) {
  if (prevention) {
    int maxHeld = -1;
    for (int i = 0; i < NUM_RES; i++)
      if (holderOf[i] == p && i > maxHeld) maxHeld = i;
    if (maxHeld > r) {
      logMsg("P%d REJECTED: requesting R%d while holding R%d violates ordering", p + 1, r + 1, maxHeld + 1);
      return false;
    }
  }
  logMsg("P%d requests R%d", p + 1, r + 1);
  setWaiting(p, r);
  BaseType_t ok = xSemaphoreTake(resMutex[r], timeout);
  setWaiting(p, -1);
  if (ok == pdTRUE) {
    setHolder(r, p);
    logMsg("P%d acquired R%d", p + 1, r + 1);
    return true;
  }
  logMsg("P%d TIMEOUT waiting for R%d", p + 1, r + 1);
  return false;
}

void releaseRes(int p, int r) {
  setHolder(r, -1);
  xSemaphoreGive(resMutex[r]);
  logMsg("P%d released R%d", p + 1, r + 1);
}

void procTask(void *arg) {
  int p = (int)(intptr_t)arg;
  for (;;) {
    if (prevention && okRounds[p] >= OK_ROUNDS) {
      logMsg("P%d finished all rounds", p + 1);
      vTaskDelete(NULL);
    }
    // start each round together so the conflict is reproducible
    xEventGroupSync(syncGroup, 1 << p, (1 << NUM_PROC) - 1, portMAX_DELAY);

    int a = firstNeed[p], b = secondNeed[p];
    if (prevention && a > b) {
      int t = a; a = b; b = t;
      logMsg("P%d applies resource ordering: R%d before R%d", p + 1, a + 1, b + 1);
    }

    if (!acquire(p, a, pdMS_TO_TICKS(5000))) { vTaskDelay(pdMS_TO_TICKS(1000)); continue; }
    vTaskDelay(pdMS_TO_TICKS(500));            // lets the other process grab its first resource

    if (!acquire(p, b, pdMS_TO_TICKS(3000))) { // recovery: give up, release, back off
      logMsg("P%d recovery: releasing R%d and backing off", p + 1, a + 1);
      releaseRes(p, a);
      vTaskDelay(pdMS_TO_TICKS(1500));
      continue;
    }

    logMsg("P%d in critical section (holds R%d and R%d)", p + 1, a + 1, b + 1);
    vTaskDelay(pdMS_TO_TICKS(300));
    releaseRes(p, b);
    releaseRes(p, a);
    if (prevention) okRounds[p]++;
    logMsg("P%d round complete", p + 1);
    vTaskDelay(pdMS_TO_TICKS(500));
  }
}

// Detects a cycle in the wait chain: P -> R(waiting) -> holder(R) -> ...
void monitorTask(void *arg) {
  bool reported = false;
  for (;;) {
    vTaskDelay(pdMS_TO_TICKS(300));

    int h[NUM_RES], w[NUM_PROC];
    portENTER_CRITICAL(&graphMux);
    for (int i = 0; i < NUM_RES; i++)  h[i] = holderOf[i];
    for (int i = 0; i < NUM_PROC; i++) w[i] = waitingFor[i];
    portEXIT_CRITICAL(&graphMux);

    int cycleStart = -1;
    for (int s = 0; s < NUM_PROC && cycleStart < 0; s++) {
      int cur = s;
      for (int step = 0; step <= NUM_PROC; step++) {
        if (w[cur] < 0) break;
        int nxt = h[w[cur]];
        if (nxt < 0) break;
        if (nxt == s) { cycleStart = s; break; }
        cur = nxt;
      }
    }

    if (cycleStart >= 0 && !reported) {
      reported = true;
      deadlockCount++;
      char chain[96];
      int len = 0, cur = cycleStart;
      do {
        len += snprintf(chain + len, sizeof(chain) - len, "P%d -> R%d -> ", cur + 1, w[cur] + 1);
        cur = h[w[cur]];
      } while (cur != cycleStart && len < (int)sizeof(chain) - 16);
      snprintf(chain + len, sizeof(chain) - len, "P%d", cycleStart + 1);
      logMsg("*** DEADLOCK DETECTED (#%d): %s", deadlockCount, chain);
    }
    if (cycleStart < 0) {
      reported = false;
      if (!prevention && deadlockCount >= DEADLOCK_ROUNDS) {
        prevention = true;
        logMsg("=== PHASE B: RESOURCE ORDERING PREVENTION ENABLED ===");
      }
    }

    if (prevention && okRounds[0] >= OK_ROUNDS && okRounds[1] >= OK_ROUNDS) {
      logMsg("=== SUMMARY: Phase A deadlocks detected = %d, Phase B deadlocks = 0, rounds completed per process = %d ===",
             deadlockCount, OK_ROUNDS);
      vTaskDelete(NULL);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  logMutex  = xSemaphoreCreateMutex();
  syncGroup = xEventGroupCreate();
  for (int i = 0; i < NUM_RES; i++)  { resMutex[i] = xSemaphoreCreateMutex(); holderOf[i] = -1; }
  for (int i = 0; i < NUM_PROC; i++) { waitingFor[i] = -1; }

  logMsg("=== PHASE A: NO PREVENTION (deadlock expected) ===");
  xTaskCreate(monitorTask, "Monitor", 4096, NULL, 3, NULL);
  xTaskCreate(procTask,    "P1",      4096, (void *)(intptr_t)0, 2, NULL);
  xTaskCreate(procTask,    "P2",      4096, (void *)(intptr_t)1, 2, NULL);
}

void loop() {
  vTaskDelay(pdMS_TO_TICKS(1000));
}
