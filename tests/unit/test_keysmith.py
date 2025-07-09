import asyncio
import random

import pytest

from boxdrive._keysmith import Keysmith

WAIT_FOR_DEADLOCK = 0.01


@pytest.mark.parametrize(
    ["repeat"],
    [
        (1,),
        (2,),
    ],
)
async def test_lock(repeat: int) -> None:
    kv = Keysmith()

    key = "a"
    for _ in range(repeat):
        assert_key_is_not_locked(kv, key)
        async with kv.lock(key):
            assert_key_is_locked(kv, key)
        assert_key_is_not_locked(kv, key)


async def test_lock_finally() -> None:
    kv = Keysmith()

    key = "a"
    with pytest.raises(ValueError):
        async with kv.lock(key):
            assert_key_is_locked(kv, key)
            assert kv._count_locks == 1
            raise ValueError
    assert_key_is_not_locked(kv, key)
    assert kv._count_locks == 0


@pytest.mark.parametrize(
    ["repeat"],
    [
        (1,),
        (2,),
    ],
)
async def test_nested_lock(repeat: int) -> None:
    kv = Keysmith()

    key1, key2 = ["a", "b"]
    for _ in range(repeat):
        assert_key_is_not_locked(kv, key1)

        async with kv.lock(key1):
            assert_key_is_locked(kv, key1)

            assert_key_is_not_locked(kv, key2)
            async with kv.lock(key2):
                assert_key_is_locked(kv, key1)
                assert_key_is_locked(kv, key2)
            assert_key_is_not_locked(kv, key2)

            assert_key_is_locked(kv, key1)

        assert_key_is_not_locked(kv, key1)


@pytest.mark.parametrize(
    ["repeat"],
    [
        (1,),
        (2,),
    ],
)
async def test_deadlock_key_and_key(repeat: int) -> None:
    kv = Keysmith()

    key = "a"
    for _ in range(repeat):
        assert_key_is_not_locked(kv, key)

        async with kv.lock(key):
            assert_key_is_locked(kv, key)

            with pytest.raises(TimeoutError):
                async with asyncio.timeout(WAIT_FOR_DEADLOCK), kv.lock(key):
                    raise Exception("expected deadlock")

            assert_key_is_locked(kv, key)

        assert_key_is_not_locked(kv, key)


@pytest.mark.parametrize(
    ["repeat"],
    [
        (1,),
        (2,),
    ],
)
async def test_deadlock_all_and_all(repeat: int) -> None:
    kv = Keysmith()

    for _ in range(repeat):
        async with kv.lock_all():
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(WAIT_FOR_DEADLOCK), kv.lock_all():
                    raise Exception("expected deadlock")


@pytest.mark.parametrize(
    ["repeat"],
    [
        (1,),
        (2,),
    ],
)
async def test_deadlock_all_and_key(repeat: int) -> None:
    kv = Keysmith()

    key = "a"
    for _ in range(repeat):
        async with kv.lock_all():
            assert_key_is_not_locked(kv, key)
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(WAIT_FOR_DEADLOCK), kv.lock(key):
                    raise Exception("expected deadlock")
            assert_key_is_not_locked(kv, key)


@pytest.mark.parametrize(
    ["repeat"],
    [
        (1,),
        (2,),
    ],
)
async def test_deadlock_key_and_all(repeat: int) -> None:
    kv = Keysmith()

    key = "a"
    for _ in range(repeat):
        assert_key_is_not_locked(kv, key)

        async with kv.lock(key):
            assert_key_is_locked(kv, key)
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(WAIT_FOR_DEADLOCK), kv.lock_all():
                    raise Exception("expected deadlock")
            assert_key_is_locked(kv, key)

        assert_key_is_not_locked(kv, key)


@pytest.mark.parametrize(
    [
        "num_of_keys",
        "num_of_lock_workers",
        "num_of_lock_all_workers",
        "sleep_at_most",
    ],
    [
        (3, 5, 3, 0.05),
        (3, 5, 0, 0.05),
        (3, 0, 3, 0.05),
    ],
)
async def test_concurrent_access(
    num_of_keys: int,
    num_of_lock_workers: int,
    num_of_lock_all_workers: int,
    sleep_at_most: float,
) -> None:
    kv = Keysmith()

    keys = [str(i) for i in range(num_of_keys)]

    async def lock() -> None:
        key = random.choice(keys)
        async with kv.lock(key):
            assert_key_is_locked(kv, key)
            await asyncio.sleep(sleep_at_most)

    async def lock_all() -> None:
        async with kv.lock_all():
            await asyncio.sleep(sleep_at_most)

    lock_coros = [lock() for _ in range(num_of_lock_workers)]
    lock_all_coros = [lock_all() for _ in range(num_of_lock_all_workers)]

    coros = lock_coros + lock_all_coros
    random.shuffle(coros)
    await asyncio.gather(*coros)


def assert_key_is_locked(kv: Keysmith, key: str) -> None:
    assert key in kv._locks
    assert kv._locks[key].locked()


def assert_key_is_not_locked(kv: Keysmith, key: str) -> None:
    if key not in kv._locks:
        return
    assert not kv._locks[key].locked()
