"""Utilities for bridging asyncio with tkinter's main thread."""

import asyncio
import threading
from typing import Callable, Coroutine, Any, Optional
from concurrent.futures import Future
import logging

logger = logging.getLogger(__name__)


class AsyncBridge:
    """Bridge between asyncio and tkinter's main thread.

    This class runs an asyncio event loop in a background thread,
    allowing async operations to run without blocking the GUI.
    """

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if the async bridge is running."""
        return self._running and self._loop is not None

    def start(self) -> None:
        """Start the async event loop in a background thread."""
        if self._running:
            return

        self._loop = asyncio.new_event_loop()
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AsyncBridge")
        self._thread.start()
        logger.info("AsyncBridge started")

    def _run_loop(self) -> None:
        """Run the event loop (called in background thread)."""
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
            logger.info("AsyncBridge event loop closed")

    def run_async(
        self,
        coro: Coroutine[Any, Any, Any],
        callback: Optional[Callable[[Any], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> Optional[Future]:
        """Schedule a coroutine to run in the async loop.

        Args:
            coro: The coroutine to run
            callback: Optional callback for successful result (called in async thread)
            error_callback: Optional callback for exceptions (called in async thread)

        Returns:
            A Future that can be used to get the result, or None if not running
        """
        if not self._loop or not self._running:
            logger.warning("AsyncBridge not running, cannot schedule coroutine")
            return None

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        if callback or error_callback:

            def handle_result(f: Future):
                try:
                    result = f.result()
                    if callback:
                        callback(result)
                except Exception as e:
                    logger.error(f"Error in async operation: {e}")
                    if error_callback:
                        error_callback(e)

            future.add_done_callback(handle_result)

        return future

    def run_async_with_gui_callback(
        self,
        coro: Coroutine[Any, Any, Any],
        gui_schedule: Callable[[int, Callable], None],
        callback: Optional[Callable[[Any], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> Optional[Future]:
        """Schedule a coroutine and call back on the GUI thread.

        Args:
            coro: The coroutine to run
            gui_schedule: Function to schedule callbacks on GUI thread (e.g., root.after)
                          Must accept (delay_ms, callback) signature like tkinter's after()
            callback: Optional callback for successful result (called on GUI thread)
            error_callback: Optional callback for exceptions (called on GUI thread)

        Returns:
            A Future that can be used to get the result, or None if not running
        """
        if not self._loop or not self._running:
            logger.warning("AsyncBridge not running, cannot schedule coroutine")
            return None

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)

        if callback or error_callback:

            def handle_result(f: Future):
                try:
                    result = f.result()
                    if callback:
                        gui_schedule(0, lambda: callback(result))
                except Exception as e:
                    logger.error(f"Error in async operation: {e}")
                    if error_callback:
                        gui_schedule(0, lambda: error_callback(e))

            future.add_done_callback(handle_result)

        return future

    def stop(self) -> None:
        """Stop the async event loop."""
        if not self._running:
            return

        self._running = False

        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        logger.info("AsyncBridge stopped")

    def __enter__(self) -> "AsyncBridge":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
