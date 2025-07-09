import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager


class Keysmith:
    def __init__(self) -> None:
        self._master_lock = asyncio.Lock()
        self._locks: dict[str, asyncio.Lock] = {}

        self._count_locks = 0
        self._cv = asyncio.Condition(asyncio.Lock())

    @asynccontextmanager
    async def lock(self, key: str) -> AsyncIterator[None]:
        async with self._master_lock:
            async with self._cv:
                if self._count_locks == 0:
                    self._clear()
                self._count_locks += 1
            lock = self._get_lock(key)

        try:
            async with lock:
                yield
        finally:
            async with self._cv:
                self._count_locks -= 1
                assert self._count_locks >= 0
                if self._count_locks == 0:
                    self._cv.notify()

    @asynccontextmanager
    async def lock_all(self) -> AsyncIterator[None]:
        predicate: Callable[[], bool] = lambda: self._count_locks == 0
        async with self._master_lock:
            async with self._cv:
                await self._cv.wait_for(predicate)
                assert predicate()
                self._clear()
            yield
            assert predicate()
            assert self._num_of_locked() == 0

    def _get_lock(self, key: str) -> asyncio.Lock:
        assert self._master_lock.locked()
        try:
            lock = self._locks[key]
        except KeyError:
            lock = asyncio.Lock()
            self._locks[key] = lock
        return lock

    def _clear(self) -> None:
        assert self._master_lock.locked()
        assert self._num_of_locked() == 0
        assert self._count_locks == 0
        self._locks = {}

    def _num_of_locked(self) -> int:
        assert self._master_lock.locked()
        return sum(lock.locked() for lock in self._locks.values())
