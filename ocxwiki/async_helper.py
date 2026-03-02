#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""Helper utilities for async operations in the CLI."""

import asyncio
import threading
from typing import TypeVar, Awaitable, Callable
from functools import wraps

T = TypeVar('T')


def run_async(coro: Awaitable[T]) -> T:
    """Run an async coroutine in a synchronous context.

    Handles two situations:

    1. **No running loop** (plain CLI / script): creates a new event loop
       and calls ``run_until_complete``.
    2. **Running loop present** (called from ``asyncio.to_thread`` inside the
       Textual TUI): spins up a *dedicated* event loop in a new thread and
       blocks the caller until the coroutine completes.  This avoids posting
       back to the already-busy Textual event loop (which can cause deadlocks
       or ``NoneType`` errors when the loop is processing other callbacks).

    Args:
        coro: The coroutine to run

    Returns:
        The result of the coroutine
    """
    try:
        asyncio.get_running_loop()
        _has_running_loop = True
    except RuntimeError:
        _has_running_loop = False

    if _has_running_loop:
        # We are inside a worker thread that was spawned by an async event loop
        # (e.g. asyncio.to_thread / Textual worker).  Run the coroutine in a
        # brand-new event loop on a dedicated background thread so we don't
        # re-enter the parent loop.
        result_holder: list = []
        exc_holder: list = []

        def _run_in_new_loop():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                result_holder.append(new_loop.run_until_complete(coro))
            except Exception as exc:
                exc_holder.append(exc)
            finally:
                new_loop.close()

        thread = threading.Thread(target=_run_in_new_loop, daemon=True)
        thread.start()
        thread.join()

        if exc_holder:
            raise exc_holder[0]
        return result_holder[0] if result_holder else None

    # No running loop – plain synchronous context.
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
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
