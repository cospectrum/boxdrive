import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Callable


class Keysmith:
    def __init__(self) -> None:
        self.master_lock = asyncio.Lock()
        self.locks: dict[str, asyncio.Lock] = {}

        self.count_guards = 0
        self.cv = asyncio.Condition(asyncio.Lock())

    @asynccontextmanager
    async def lock(self, key: str) -> AsyncIterator[None]:
        async with self.master_lock:
            async with self.cv:
                if self.count_guards == 0:
                    self._clear()
                self.count_guards += 1
            guard = self._get_lock(key)

        try:
            async with guard:
                yield
        finally:
            async with self.cv:
                self.count_guards -= 1
                assert self.count_guards >= 0
                if self.count_guards == 0:
                    self.cv.notify()

    @asynccontextmanager
    async def lock_all(self) -> AsyncIterator[None]:
        predicate: Callable[[], bool] = lambda: self.count_guards == 0
        async with self.master_lock:
            async with self.cv:
                await self.cv.wait_for(predicate)
                assert predicate()
                self._clear()
            yield
            assert predicate()
            assert self._num_of_locked() == 0

    def _get_lock(self, key: str) -> asyncio.Lock:
        assert self.master_lock.locked()
        try:
            lock = self.locks[key]
        except KeyError:
            lock = asyncio.Lock()
            self.locks[key] = lock
        return lock

    def _clear(self) -> None:
        assert self.master_lock.locked()
        assert self._num_of_locked() == 0
        assert self.count_guards == 0
        self.locks = {}

    def _num_of_locked(self) -> int:
        assert self.master_lock.locked()
        return sum(lock.locked() for lock in self.locks.values())
