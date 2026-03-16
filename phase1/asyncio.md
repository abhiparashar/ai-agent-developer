# Asyncio Deep Dive — Part 1: Foundations

### For Java Developers building AI Agents

---

## 0. The Most Important Thing First: What IS the Event Loop?

Before any code makes sense, you need a genuine mental model of **what actually runs async code**.

In Java, `CompletableFuture.supplyAsync(() -> ...)` hands your task to a **thread pool** (ForkJoinPool by default).  
Multiple OS threads run in parallel. This is **true parallelism** — multiple threads physically executing simultaneously on multiple CPU cores.

Python asyncio is **fundamentally different**. There is **one thread**. One.  
There is no thread pool (by default). Instead there is an **event loop** — a scheduler that runs inside that single thread.

```
JAVA (Multi-threaded):
┌─────────────────────────────────────────────────┐
│  Thread 1: ──[Task A]──────────────────────     │
│  Thread 2: ──[Task B]──────────────────────     │  ← True parallelism (multiple CPUs)
│  Thread 3: ──[Task C]──────────────────────     │
└─────────────────────────────────────────────────┘

PYTHON ASYNCIO (Single-threaded, Cooperative):
┌─────────────────────────────────────────────────┐
│  Thread 1 only:                                  │
│    [Task A runs] → hits await → PAUSES           │
│    [Task B runs] → hits await → PAUSES           │
│    [Task C runs] → hits await → PAUSES           │
│    [Task A resumes] → completes                  │  ← Interleaved on ONE thread
│    [Task B resumes] → completes                  │
│    [Task C resumes] → completes                  │
└─────────────────────────────────────────────────┘
```

The event loop runs something like this internally:

```python
# Pseudocode of what asyncio.run() does under the hood
while tasks_exist:
    for task in ready_tasks:
        task.run_until_next_await()   # Run until it hits an `await`
    wait_for_io_events()              # Ask OS: "any network/disk I/O done?"
    mark_finished_tasks_as_ready()
```

**Closest Java analogy:** A single-threaded `ExecutorService` combined with Java NIO's `Selector`.  
The asyncio event loop uses the OS's `select()`/`epoll()` under the hood to monitor I/O — exactly like Java NIO does.

---

## Why Does Single-Threaded Async Work for I/O at All?

This is the key insight most tutorials skip.

When your code calls a network API, your CPU is **not actually doing anything** during the wait.  
It sends bytes out through the network card, then sits idle waiting for bytes to come back. The OS kernel handles all of this.

```
Without async — your thread waits:
Thread: [send request] ──── IDLE 300ms waiting ──── [read response]
CPU useful work:         ░░░░░░░░░░░░░░░░░░░░░░░░░  (mostly nothing)

With async — your thread yields to other work:
Thread: [send req A] → [run Task B] → [run Task C] → [read response A]
CPU useful work:     ████████████████████████████  (always busy)
```

`await asyncio.sleep(0.3)` tells the event loop:  
_"I don't need the CPU right now. Come back to me in 0.3 seconds."_  
The event loop then runs other tasks in the meantime.

**Java parallel (Project Loom, Java 21):** `Thread.sleep()` in a virtual thread unmounts it from the carrier thread — same concept. Python's asyncio predates Loom by years and implements the same idea manually via `await`.

---

## Level 1: `async def` and `await` — Deep Mechanics

```python
async def hello_async() -> str:
    await asyncio.sleep(1)
    return "result"
```

**Java comparison:**

```java
CompletableFuture<String> helloAsync() {
    return CompletableFuture.supplyAsync(() -> {
        Thread.sleep(1000);   // blocks a thread from the pool
        return "result";
    });
}
```

Key difference: the Java version **creates a new thread** (or borrows one from the pool).  
The Python version uses **zero extra threads**.

---

### Critical Gotcha: Calling `hello_async()` Does Nothing

```python
hello_async()        # Returns a coroutine object. NOT executed. Not even started.
await hello_async()  # NOW it runs.
```

**Java comparison of this mistake:**

```java
helloAsync();        // Called but ignored — work STILL STARTS in the thread pool!
helloAsync().join(); // This blocks until the result is ready
```

|                         | Python `async def`                       | Java `CompletableFuture.supplyAsync()` |
| ----------------------- | ---------------------------------------- | -------------------------------------- |
| When is work submitted? | Only when `await`ed or wrapped in `Task` | **Immediately** when called            |
| Evaluation strategy     | **Lazy**                                 | **Eager**                              |
| Returns                 | Inert coroutine object                   | A running future                       |

This is one of the most common bugs for Java developers moving to Python async.

---

### `time.sleep()` vs `await asyncio.sleep()` — Why This Kills You

```python
# BAD — freezes the entire event loop
time.sleep(0.3)           # Calls the OS: "freeze this thread for 0.3s"
                          # Since there is only ONE thread, your whole app is frozen.

# GOOD — yields control cooperatively
await asyncio.sleep(0.3)  # Tells event loop: "come back to me in 0.3s"
                          # Event loop is free to run other tasks
```

**Java analogy:**

```java
Thread.sleep(300);  // In Java: only freezes ONE of many threads — others keep running
                    // In Python: freezes THE thread — entire app stops
```

Why it's catastrophic in Python: since everything runs on one thread,  
freezing that thread freezes **your entire application** — all concurrent tasks stop.

---

## Level 2: `asyncio.gather()` — The Agent Superpower

```python
r1, r2, r3 = await asyncio.gather(
    fake_tool_call("web_search", {"q": "AI news"}),
    fake_tool_call("get_user",   {"id": "123"}),
    fake_tool_call("query_db",   {"sql": "SELECT..."}),
)
```

**Java comparison:**

```java
CompletableFuture<Result> f1 = webSearch("AI news");
CompletableFuture<Result> f2 = getUser("123");
CompletableFuture<Result> f3 = queryDb("SELECT...");

CompletableFuture.allOf(f1, f2, f3).join();  // wait for all

Result r1 = f1.join();
Result r2 = f2.join();
Result r3 = f3.join();
```

`gather()` is analogous to `CompletableFuture.allOf()`.

| Behavior                       | `asyncio.gather()`          | `CompletableFuture.allOf()`        |
| ------------------------------ | --------------------------- | ---------------------------------- |
| Runs all concurrently          | ✅                          | ✅                                 |
| Returns results in input order | ✅ always                   | ❌ need `.join()` per future       |
| One failure cancels others     | ✅ by default               | ❌ others keep running             |
| Isolate failures               | ✅ `return_exceptions=True` | need `.exceptionally()` per future |

---

### `return_exceptions=True` — Critical for Agents

```python
results = await asyncio.gather(
    tool_a(),
    tool_b(),   # raises ValueError at runtime
    tool_c(),
    return_exceptions=True   # ← tool_b's exception becomes a value, not a crash
)
# results = [ResultA, ValueError("something broke"), ResultC]

for r in results:
    if isinstance(r, Exception):
        print(f"Tool failed: {r}")
    else:
        process(r)
```

Without `return_exceptions=True`:  
`ValueError` propagates and **cancels all other tasks** — you lose the results from `tool_a` and `tool_c`.

**Java equivalent (verbose):**

```java
CompletableFuture<Result> safe_b = tool_b.exceptionally(ex -> new ErrorResult(ex));
```

---

## Level 3: Tasks — Eager Execution

```python
# Coroutine (lazy — nothing runs yet)
coro = fake_llm_call("Summarize")

# Task (eager — starts running immediately on the event loop)
task = asyncio.create_task(fake_llm_call("Summarize"), name="summarizer")

# Do other work while it runs concurrently
await asyncio.sleep(0.1)   # task is running during this sleep

# Collect result (may already be done by now)
result = await task
```

**Java comparison:**

```java
Future<String> future = executorService.submit(() -> llmCall("Summarize"));
// ↑ Also starts immediately, equivalent to create_task()

Thread.sleep(100);         // task runs concurrently

String result = future.get();  // blocks if not done yet
```

### Summary: Three ways to run a coroutine

| Method              | When does it run?         | Java equivalent                       |
| ------------------- | ------------------------- | ------------------------------------- |
| `coro = fn()`       | Never (just an object)    | — no equivalent, Java is always eager |
| `await fn()`        | Right now, sequentially   | `future.get()` immediately            |
| `create_task(fn())` | Immediately, concurrently | `executorService.submit()`            |

---

### Task Cancellation — Python Does It Better

```python
task = asyncio.create_task(slow_llm_call(latency=5.0))
await asyncio.sleep(0.2)

task.cancel()   # Send cancellation signal
try:
    await task
except asyncio.CancelledError:
    print("Cancelled cleanly — can release resources here")
```

**Java comparison:**

```java
future.cancel(true);   // Sends interrupt signal
                       // BUT the task can catch InterruptedException and IGNORE it
                       // No guarantee it actually stops
```

Python's `CancelledError` propagates through every `await` point automatically.  
You cannot accidentally ignore it the way Java's `InterruptedException` can be silently swallowed.

---

## The Most Important Conceptual Difference: Cooperative vs Preemptive Scheduling

This is the source of most asyncio bugs for Java developers.

**Java (Preemptive):** The OS can pause your thread at **any instruction**, at any time, without your permission.  
This is why Java needs `synchronized`, `volatile`, `ReentrantLock`, `AtomicInteger` — threads can be interrupted mid-operation.

**Python asyncio (Cooperative):** A task runs **uninterrupted** until it explicitly hits an `await`.  
The event loop cannot preempt it. Tasks voluntarily yield control.

```python
# SAFE in asyncio — no lock needed
counter = 0
async def increment():
    global counter
    value = counter        # read
    # ← No await here: NOTHING else can run between read and write
    counter = value + 1    # write — guaranteed safe

# UNSAFE — there's an await between read and write
async def bad_increment():
    global counter
    value = counter
    await asyncio.sleep(0)   # ← event loop can switch to another task HERE
    counter = value + 1      # another task may have modified counter already!
```

**Java equivalent of the danger:**

```java
// In Java, this is ALWAYS unsafe (OS can preempt anywhere):
int value = counter;
// OS might switch thread HERE
counter = value + 1;
// You need AtomicInteger or synchronized — always
```

In Python asyncio, you only need a `Lock` if there is an `await` between your read and write of shared state.  
This is far simpler to reason about than Java's threading model.

---

## Full Mental Map (so far)

```
Python asyncio              Java                          Key Difference
──────────────────────────────────────────────────────────────────────────
async def fn()            CompletableFuture.supplyAsync  Python: lazy (no thread)
                                                          Java:   eager (thread pool)

await expr                future.join()                  Same semantics

asyncio.gather()          CompletableFuture.allOf()      Python: ordered results built-in
                                                          Java:   need .join() on each

create_task(fn())         executorService.submit()       Both eager; Python: zero threads

asyncio.Semaphore         java.util.concurrent.Semaphore Nearly identical

asyncio.Lock              ReentrantLock                  Python: only needed across awaits

asyncio.Queue             LinkedBlockingQueue            Python: single-threaded, simpler

async for                 Flux/Flow (Project Reactor)    Python: simpler syntax

asyncio.sleep(0)          Thread.yield()                 Yield to event loop
```

---

## What's Next

Suggested order for the next file:

1. **Semaphore + Retry patterns** (Level 5 + 8) — core of real agent infrastructure, LLM rate limiting
2. **Error propagation deep dive** — how exceptions travel through `gather`/`Task`, vs Java's `ExecutionException` wrapping
3. **Async generators + streaming** (Level 7) — critical for LLM token streaming
4. **Shared state with Lock** (Level 9) — token counters, cost tracking across parallel calls
