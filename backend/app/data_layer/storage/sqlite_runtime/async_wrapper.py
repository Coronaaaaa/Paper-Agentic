"""异步包装：将同步 I/O 操作移到线程池，避免阻塞事件循环"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from functools import partial
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


async def run_sync(fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    return await asyncio.to_thread(partial(fn, *args, **kwargs))
