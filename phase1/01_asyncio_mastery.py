"""
╔══════════════════════════════════════════════════════════════╗
║        ASYNCIO MASTERY — Basic to Top 1%                    ║
║        For AI Agent Developers  |  Phase 0                  ║
╚══════════════════════════════════════════════════════════════╝
 
WHY THIS MATTERS FOR AGENTS:
    Every LLM API call is I/O-bound (network). Without async,
    your agent waits idle for each call before starting the next.
    With async, you run 10 LLM calls simultaneously.
    This is the difference between a 2-second and a 20-second agent.
 
JAVA MENTAL MAP:
    async def          →  @Async method / CompletableFuture.supplyAsync()
    await expr         →  future.get() / future.join()
    asyncio.gather()   →  CompletableFuture.allOf()
    asyncio.Queue      →  LinkedBlockingQueue
    asyncio.Lock       →  ReentrantLock
    asyncio.Semaphore  →  java.util.concurrent.Semaphore
    async for          →  Iterator over a reactive stream (Project Reactor)
    async with         →  try-with-resources
 
RUN THIS FILE:
    pip install aiohttp
    python 01_asyncio_mastery.py
"""
import asyncio
import time
import random
# LEVEL 1 — COROUTINES: THE BUILDING BLOCK
async def hello_async()-> str:
    print("  [coroutine] Starting...")
    await asyncio.sleep(5)
    print("  [coroutine] Done!")
    return "result"

# asyncio.run(hello_async())

async def blocking_vs_nonblocking():
    """The most important concept: NEVER call time.sleep() in async code."""
    print("BLOCKING  (time.sleep — freezes the event loop):")
    start = time.perf_counter()
    time.sleep(0.3)   # ← BAD: blocks entire thread, no other coros can run
    time.sleep(0.3)
    time.sleep(0.3)
    print(f"  Sequential blocking: {time.perf_counter() - start:.2f}s")

    print("\nNON-BLOCKING (await asyncio.sleep — yields control):")
    start = time.perf_counter()
    await asyncio.sleep(0.3)
    await asyncio.sleep(0.3)
    await asyncio.sleep(0.3)
    print(f"  Sequential async:   {time.perf_counter() - start:.2f}s  (still ~0.9s — sequential)")

    print("\nCONCURRENT (asyncio.gather — run all at once):")
    start = time.perf_counter()
    await asyncio.gather(
        asyncio.sleep(0.3),
        asyncio.sleep(0.3),
        asyncio.sleep(0.3)
    )
    print(f"  Concurrent async:   {time.perf_counter() - start:.2f}s  (3 tasks in ~0.3s!)")

# asyncio.run(blocking_vs_nonblocking())

# LEVEL 2 — ASYNCIO.GATHER: THE AGENT SUPERPOWER
async def fake_llm_call(prompt:str,latency:float=None)->str:
    """Simulates an LLM API call (I/O bound, network latency)."""
    await asyncio.sleep(latency or random.uniform(0.3,0.8))
    return f"LLM response to: '{prompt[:25]}...'"

async def fake_tool_call(tool:str, args:dict, latency:float=None)->str:
    """Simulates a tool call (web search, DB query, API call)."""
    await asyncio.sleep(latency or random.uniform(0.1,0.5))
    return {"tool": tool, "result": f"Result for {args}"}

async def agent_tool_patterns():
    """
    The #1 performance pattern for agents:
    Run independent tools in parallel, not sequentially.
    """
    # ❌ BAD: Sequential — total time = sum of all latencies
    print("❌ Sequential tool calls:")
    start = time.perf_counter()
    r1 = await fake_tool_call("web_search",  {"q": "AI news"})
    r2 = await fake_tool_call("get_user",    {"id": "123"})
    r3 = await fake_tool_call("query_db",    {"sql": "SELECT..."})
    print(f"   Time: {time.perf_counter() - start:.2f}s — wasteful!")

    # ✅ GOOD: Parallel — total time = max single latency
    print("\n✅ Parallel tool calls:")
    start = time.perf_counter()
    r1,r2,r3 = asyncio.gather(
        await fake_tool_call("web_search",  {"q": "AI news"}),
        await fake_tool_call("get_user",    {"id": "123"}),
        await fake_tool_call("query_db",    {"sql": "SELECT..."})
    )
    print(f"   Time: {time.perf_counter() - start:.2f}s — much faster!")

    # ✅✅ BEST: Parallel with isolated error handling
    print("\n✅✅ Parallel with error isolation (return_exceptions=True):")
    results = asyncio.gather(
        fake_tool_call("web_search",    {"q": "AI news"}),
        fake_tool_call("failing_tool",  {}),  # Will raise in real code
        fake_tool_call("query_db",      {"sql": "SELECT..."}),
        return_exceptions=True   # ← One failure doesn't kill the others
    )

    for i,r in enumerate(results):
        if isinstance(r,Exception):
            print(f"   Tool {i}: FAILED — {r}")
        else:
            print(f"   Tool {i}: OK — {r['tool']}")


# LEVEL 3 — TASKS: BACKGROUND WORK
async def tasks_demo():
    """
    Tasks start immediately and run in the background.
    Use when you want to kick off work and do other things
    before collecting the result.
    """

    # Create tasks — they START running right now
    task_a  = asyncio.create_task(
        fake_llm_call("Summarize this document"),
        name="summarizer"
    )

    task_b = asyncio.create_task(
        fake_llm_call("Extract key entities"),
        name="extractor"
    )
 
    # While they run, do other work
    print("  Tasks started. Doing other work...")
    await asyncio.sleep(0.1)
    print("  Still doing other work...")
    await asyncio.sleep(0.1)

    # Now collect results (they may already be done!)
    summary = await task_a
    entities = await task_b
    print(f"  Summary:  {summary}")
    print(f"  Entities: {entities}")

    # ── Task cancellation ──────────────────────────────
    long_task = asyncio.create_task(fake_llm_call("very long task", latency=5.0))
    await asyncio.sleep(0.2)

    long_task.cancel()   # Cancel it
    try:
        await long_task()
    except asyncio.CancelledError:
        print("  Task was cancelled cleanly")

# LEVEL 4 — TIMEOUTS: NON-NEGOTIABLE IN PRODUCTION
async def timeout_patterns():
    """
    ALWAYS set timeouts on external calls.
    A hung API call = your agent hangs forever = production incident.
    """
    # ── Pattern 1: Single call timeout ────────────────
    async def slow_api():
        await asyncio.sleep(10)
        return "finally done"
    
    try:
        result = await asyncio.wait_for(slow_api(), timeout=2.0)
    except asyncio.TimeoutError:
        result = None
        print("  API timed out after 2s — handled gracefully")

    # ── Pattern 2: Timeout wrapper utility ────────────
    async def with_timeout(coro, timeout: float, fallback=None):
        """Wrap any coroutine with a timeout, return fallback on timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            return fallback
        
    # Use it everywhere
    result = await with_timeout(slow_api(), timeout=1.0, fallback={"error": "timeout"})
    print(f"  With fallback: {result}")

    # ── Pattern 3: Multiple calls, each with own timeout ──
    results = await asyncio.gather(
        with_timeout(fake_tool_call("fast", {}),  timeout=2.0),
        with_timeout(slow_api(),                  timeout=0.5, fallback=None),
        with_timeout(fake_tool_call("also_fast", {}), timeout=2.0),
    )
    print(f"  Mixed results: {[r is not None for r in results]}")  # [True, False, True]


# LEVEL 5 — SEMAPHORE: RATE LIMITING LLM CALLS
async def semaphore_rate_limiting():
    """
    LLM APIs enforce rate limits (e.g. 60 req/min).
    Semaphores let you cap concurrent calls.
 
    Without: blast 100 requests → 429 rate limit errors
    With:    cap at 10 concurrent → stays within limit
    """
 
    # Claude/OpenAI free tier: ~5-10 req/sec
    MAX_CONCURRENT = 5
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
 
    async def rate_limited_call(prompt: str) -> str:
        async with semaphore:   # Blocks if MAX_CONCURRENT already running
            return await fake_llm_call(prompt)
 
    prompts = [f"Analyze document {i}" for i in range(30)]
    start = time.perf_counter()
    results = await asyncio.gather(*[
        rate_limited_call(p) for p in prompts
    ])
    elapsed = time.perf_counter() - start
    print(f"  Processed {len(results)} prompts in {elapsed:.2f}s")
    print(f"  Throughput: {len(results)/elapsed:.1f} calls/sec (capped at {MAX_CONCURRENT} concurrent)")



 

