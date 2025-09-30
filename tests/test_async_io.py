"""Async I/O Enforcement Tests"""
import pytest
import asyncio
import time
import aiofiles
import httpx
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import aiosqlite
from pathlib import Path

class TestAsyncIOEnforcement:
    """Test that all I/O operations use async patterns"""

    @pytest.mark.asyncio
    async def test_file_io_async(self):
        """Test async file operations vs sync blocking"""
        test_file = Path("test_async_file.txt")
        content = "x" * 10000  # 10KB content

        # Test async file write (non-blocking)
        start = time.time()
        async with aiofiles.open(test_file, "w") as f:
            await f.write(content)
        async_write_time = time.time() - start

        # Test sync file write (blocking) - THIS IS BAD
        start = time.time()
        with open(test_file, "w") as f:
            f.write(content)
        sync_write_time = time.time() - start

        # Clean up
        test_file.unlink()

        # Async should not block event loop
        assert async_write_time < sync_write_time * 2  # Some overhead is OK
        print(f"Async write: {async_write_time:.4f}s, Sync write: {sync_write_time:.4f}s")

    @pytest.mark.asyncio
    async def test_database_async(self):
        """Test async database operations"""
        db_path = "test_async.db"

        # Setup database
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS breakers (
                    id INTEGER PRIMARY KEY,
                    sku TEXT,
                    rating INTEGER
                )
            """)
            await db.commit()

        # Test async insert (non-blocking)
        start = time.time()
        async with aiosqlite.connect(db_path) as db:
            for i in range(100):
                await db.execute(
                    "INSERT INTO breakers (sku, rating) VALUES (?, ?)",
                    (f"BKR-{i:03d}", 32 + i)
                )
            await db.commit()
        async_insert_time = time.time() - start

        # Test sync insert (blocking) - THIS IS BAD
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        start = time.time()
        for i in range(100, 200):
            cursor.execute(
                "INSERT INTO breakers (sku, rating) VALUES (?, ?)",
                (f"BKR-{i:03d}", 32 + i)
            )
        conn.commit()
        sync_insert_time = time.time() - start
        conn.close()

        # Clean up
        Path(db_path).unlink()

        print(f"Async DB insert: {async_insert_time:.4f}s, Sync DB insert: {sync_insert_time:.4f}s")

        # Verify async doesn't block
        assert async_insert_time < sync_insert_time * 3

    @pytest.mark.asyncio
    async def test_http_client_async(self):
        """Test async HTTP client vs sync requests"""
        urls = [
            "http://localhost:8000/health",
            "http://localhost:8000/ready",
        ] * 5  # 10 requests total

        # Test async HTTP (non-blocking)
        start = time.time()
        async with httpx.AsyncClient() as client:
            tasks = [client.get(url, timeout=1.0) for url in urls]
            try:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
            except:
                responses = []
        async_time = time.time() - start

        # Test sync HTTP (blocking) - THIS IS BAD
        import requests
        start = time.time()
        sync_responses = []
        for url in urls:
            try:
                r = requests.get(url, timeout=1.0)
                sync_responses.append(r)
            except:
                sync_responses.append(None)
        sync_time = time.time() - start

        print(f"Async HTTP: {async_time:.4f}s, Sync HTTP: {sync_time:.4f}s")

        # Async should be significantly faster for parallel requests
        if len([r for r in responses if not isinstance(r, Exception)]) > 0:
            assert async_time < sync_time / 2  # Async should be at least 2x faster

    @pytest.mark.asyncio
    async def test_concurrent_tasks(self):
        """Test proper async concurrency patterns"""

        async def cpu_bound_task(n: int) -> int:
            """Simulate CPU-bound work"""
            total = 0
            for i in range(n * 1000):
                total += i
            return total

        async def io_bound_task(delay: float) -> str:
            """Simulate I/O-bound work"""
            await asyncio.sleep(delay)
            return f"Completed after {delay}s"

        # Test concurrent I/O tasks (good pattern)
        start = time.time()
        io_tasks = [io_bound_task(0.1) for _ in range(10)]
        io_results = await asyncio.gather(*io_tasks)
        io_time = time.time() - start

        # Should complete in ~0.1s (parallel), not 1.0s (serial)
        assert io_time < 0.5
        assert len(io_results) == 10

        # Test CPU-bound tasks (should use executor)
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=4) as executor:
            start = time.time()
            cpu_tasks = [
                loop.run_in_executor(executor, lambda n=i: sum(range(n * 1000)))
                for i in range(10)
            ]
            cpu_results = await asyncio.gather(*cpu_tasks)
            cpu_time = time.time() - start

        assert len(cpu_results) == 10
        print(f"I/O concurrent: {io_time:.4f}s, CPU concurrent: {cpu_time:.4f}s")

    @pytest.mark.asyncio
    async def test_async_context_managers(self):
        """Test proper async context manager usage"""

        class AsyncResource:
            """Mock async resource"""
            def __init__(self, name: str):
                self.name = name
                self.is_open = False

            async def __aenter__(self):
                await asyncio.sleep(0.01)  # Simulate async setup
                self.is_open = True
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                await asyncio.sleep(0.01)  # Simulate async cleanup
                self.is_open = False

        # Test async context manager
        async with AsyncResource("test") as resource:
            assert resource.is_open
            await asyncio.sleep(0.01)

        assert not resource.is_open

    @pytest.mark.asyncio
    async def test_async_generators(self):
        """Test async generator patterns"""

        async def fetch_breakers_async(count: int):
            """Async generator for breakers"""
            for i in range(count):
                await asyncio.sleep(0.001)  # Simulate async fetch
                yield {
                    "id": f"BKR-{i:03d}",
                    "rating": 32 + i,
                    "phase": chr(65 + (i % 3))  # A, B, C
                }

        # Consume async generator
        breakers = []
        async for breaker in fetch_breakers_async(10):
            breakers.append(breaker)

        assert len(breakers) == 10
        assert breakers[0]["id"] == "BKR-000"
        assert breakers[9]["phase"] == "A"  # 9 % 3 = 0 -> A

    @pytest.mark.asyncio
    async def test_async_queue_pattern(self):
        """Test async queue for producer-consumer pattern"""
        queue = asyncio.Queue(maxsize=5)
        results = []

        async def producer(q: asyncio.Queue, n: int):
            """Produce items"""
            for i in range(n):
                await asyncio.sleep(0.01)
                await q.put(f"item-{i}")
            await q.put(None)  # Sentinel

        async def consumer(q: asyncio.Queue, results: List):
            """Consume items"""
            while True:
                item = await q.get()
                if item is None:
                    break
                await asyncio.sleep(0.005)  # Process
                results.append(item)
                q.task_done()

        # Run producer and consumer concurrently
        await asyncio.gather(
            producer(queue, 10),
            consumer(queue, results)
        )

        assert len(results) == 10
        assert results[0] == "item-0"
        assert results[-1] == "item-9"

    @pytest.mark.asyncio
    async def test_async_lock_pattern(self):
        """Test async lock for shared resource access"""
        lock = asyncio.Lock()
        shared_counter = {"value": 0}

        async def increment_counter(lock: asyncio.Lock, counter: Dict, n: int):
            """Increment shared counter with lock"""
            for _ in range(n):
                async with lock:
                    current = counter["value"]
                    await asyncio.sleep(0.001)  # Simulate work
                    counter["value"] = current + 1

        # Run multiple tasks concurrently
        tasks = [increment_counter(lock, shared_counter, 10) for _ in range(5)]
        await asyncio.gather(*tasks)

        # Should be 50 (5 tasks * 10 increments)
        assert shared_counter["value"] == 50

    @pytest.mark.asyncio
    async def test_async_timeout_pattern(self):
        """Test async timeout handling"""

        async def slow_operation():
            """Simulate slow operation"""
            await asyncio.sleep(5.0)
            return "completed"

        # Test with timeout
        try:
            result = await asyncio.wait_for(slow_operation(), timeout=0.1)
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            pass  # Expected

        # Test without timeout
        async def fast_operation():
            await asyncio.sleep(0.01)
            return "completed"

        result = await asyncio.wait_for(fast_operation(), timeout=1.0)
        assert result == "completed"

    @pytest.mark.asyncio
    async def test_async_semaphore_pattern(self):
        """Test async semaphore for rate limiting"""
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent
        active_count = {"value": 0, "max": 0}

        async def limited_operation(sem: asyncio.Semaphore, counter: Dict):
            """Operation with concurrency limit"""
            async with sem:
                counter["value"] += 1
                counter["max"] = max(counter["max"], counter["value"])
                await asyncio.sleep(0.05)
                counter["value"] -= 1

        # Try to run 10 concurrent tasks
        tasks = [limited_operation(semaphore, active_count) for _ in range(10)]
        await asyncio.gather(*tasks)

        # Should never exceed 3 concurrent
        assert active_count["max"] <= 3
        assert active_count["value"] == 0  # All completed

    def test_detect_blocking_io(self):
        """Test detection of blocking I/O in async context"""

        async def bad_async_function():
            """Function that incorrectly uses blocking I/O"""
            # THIS IS BAD - blocking I/O in async function
            with open("test.txt", "w") as f:
                f.write("blocking write")

            # THIS IS BAD - blocking sleep
            time.sleep(0.1)

            # THIS IS BAD - sync database
            conn = sqlite3.connect(":memory:")
            conn.execute("SELECT 1")
            conn.close()

        # These patterns should be detected and avoided
        import inspect
        source = inspect.getsource(bad_async_function)

        # Check for blocking patterns
        blocking_patterns = [
            "open(",  # Should use aiofiles
            "time.sleep(",  # Should use asyncio.sleep
            "sqlite3.connect(",  # Should use aiosqlite
            "requests.",  # Should use httpx.AsyncClient
        ]

        violations = []
        for pattern in blocking_patterns:
            if pattern in source:
                violations.append(pattern)

        assert len(violations) == 3  # Found blocking patterns

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])