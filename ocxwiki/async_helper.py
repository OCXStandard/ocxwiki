#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""Helper utilities for async operations in the CLI."""

import asyncio
from typing import TypeVar, Awaitable, Callable
from functools import wraps

T = TypeVar('T')


def run_async(coro: Awaitable[T]) -> T:
    """Run an async coroutine in a synchronous context.

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)


def async_command(func: Callable[..., Awaitable[T]]) -> Callable[..., T]:
    """Decorator to make async functions work as synchronous CLI commands.

    Args:
        func: The async function to wrap

    Returns:
        A synchronous wrapper function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return run_async(func(*args, **kwargs))

    return wrapper
