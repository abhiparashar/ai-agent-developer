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
async def hello_async() -> str:
    await asyncio.sleep(10)
    return "result"

async def main():
    result = await hello_async()
    print(result)

asyncio.run(main())