#  Copyright (c) 2023-2026. OCX Consortium https://3docx.org. See the LICENSE
"""TUI integration tests: verify progress bar and summary callback during async publish.

These tests use Textual's built-in ``App.run_test()`` / Pilot API so the real
widget tree is mounted and we can assert widget state after the publish loop
completes.

Strategy
--------
* The ``WikiManager.publish_complete_schema_async`` method is **patched** so no
  real network call is made.
* The patched coroutine calls the *real* ``progress_callback`` that
  ``CLIApp._make_progress_callback()`` creates, exactly as the production code
  path does.
* After the async operation finishes we use the Pilot to inspect:
  - ``TextualProgressSink._current`` and ``._total`` (progress state)
  - ``RichLog`` content in ``#output-log`` (summary text)
"""

import asyncio
import threading
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from textual.widgets import ProgressBar, RichLog

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_wiki_manager(
    n_pages: int = 3,
    n_enums: int = 2,
    n_attrs: int = 2,
    n_simples: int = 1,
):
    """Return a WikiManager mock with a connected client and a populated transformer."""
    from ocxwiki.wiki_manager import WikiManager

    manager = WikiManager(wiki_url="http://mock.wiki")

    # Patch the client so is_connected() returns True
    mock_client = Mock()
    mock_client.is_connected.return_value = True
    mock_client.current_url.return_value = "http://mock.wiki"
    manager._client = mock_client

    # Build mock transformer data
    mock_pages = []
    for i in range(n_pages):
        page = Mock()
        page.get_prefix.return_value = "ocx"
        page.get_name.return_value = f"Element{i}"
        page.get_tag.return_value = f"{{http://mock.namespace}}Element{i}"
        mock_pages.append(page)

    mock_enums = {}
    for i in range(n_enums):
        enum = Mock()
        enum.prefix = "ocx"
        enum.name = f"Enum{i}"
        mock_enums[f"Enum{i}"] = enum

    mock_attrs = []
    for i in range(n_attrs):
        attr = Mock()
        attr.prefix = "ocx"
        attr.name = f"Attr{i}"
        mock_attrs.append(attr)

    mock_simples = []
    for i in range(n_simples):
        simple = Mock()
        simple.prefix = "ocx"
        simple.name = f"Simple{i}"
        mock_simples.append(simple)

    mock_transformer = Mock()
    mock_transformer.get_ocx_elements.return_value = mock_pages
    mock_transformer.get_enumerators.return_value = mock_enums
    mock_transformer.get_global_attributes.return_value = mock_attrs
    mock_transformer.get_simple_types.return_value = mock_simples
    mock_transformer.parser = Mock()
    mock_transformer.parser.get_schema_version.return_value = "3.0.0"

    manager._transformer = mock_transformer

    # Pre-populate _wiki_schema so publish helpers don't crash
    from ocxwiki.struct_data import WikiSchema
    manager._wiki_schema = WikiSchema(
        author="test",
        namespace="http://mock.namespace",
        ocx_location="http://mock.namespace",
        ocx_version="3.0.0",
        date="Jan 01 2026 00:00:00",
        status="DRAFT",
        wiki_version="1.0.0",
    )

    return manager, n_pages + n_enums + n_attrs + n_simples


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_wiki_manager():
    """A fully configured mock WikiManager (no network calls)."""
    return _make_mock_wiki_manager()


# ---------------------------------------------------------------------------
# Unit tests: _make_progress_callback and _make_summary_callback in isolation
# ---------------------------------------------------------------------------

class TestProgressCallbackUnit:
    """Unit-test the callback factories without running the full TUI."""

    def test_progress_callback_initialises_sink(self):
        """progress_callback(0, total, …) sets sink total and resets it."""
        from ocxwiki.ui.logging import TextualProgressSink
        from textual.widgets import ProgressBar

        # Create a mock ProgressBar
        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)

        calls = []

        # Simulate what _make_progress_callback returns but using call_from_thread inline
        def progress_callback(advance, total, description):
            if total is not None and advance == 0:
                sink.set_total(total)
                sink.reset()
            else:
                sink.update(advance=advance, description=description)
            calls.append((advance, total, description))

        # Signal total
        progress_callback(0, 8.0, "Starting…")
        assert sink._total == 8.0
        assert sink._current == 0.0

        # Advance 8 times
        for i in range(8):
            progress_callback(1, None, f"item {i}")

        assert sink._current == 8.0
        assert len(calls) == 9  # 1 init + 8 advances

    def test_progress_callback_clamps_to_total(self):
        """Advancing past the total should clamp to total."""
        from ocxwiki.ui.logging import TextualProgressSink

        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)

        def progress_callback(advance, total, description):
            if total is not None and advance == 0:
                sink.set_total(total)
                sink.reset()
            else:
                sink.update(advance=advance, description=description)

        progress_callback(0, 3.0, "Starting…")
        for _ in range(10):  # more advances than total
            progress_callback(1, None, None)

        assert sink._current == 3.0

    def test_summary_callback_marks_complete(self):
        """summary_callback should mark the sink complete."""
        from ocxwiki.ui.logging import TextualProgressSink

        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)
        sink.set_total(5.0)

        summary_received = []

        def summary_callback(text):
            sink.complete()
            summary_received.append(text)

        summary_callback("Done! Pages: 3")
        assert sink._current == 5.0
        assert summary_received == ["Done! Pages: 3"]


# ---------------------------------------------------------------------------
# Integration tests: real CLIApp + Textual Pilot
# ---------------------------------------------------------------------------

class TestTUIProgressIntegration:
    """Run the TUI under Textual's test driver and verify progress + summary."""

    @pytest.mark.asyncio
    async def test_progress_bar_updated_during_publish(self):
        """
        Mount CLIApp, inject a mocked publish_complete_schema_async that calls
        the real progress_callback, and verify the progress sink advances.
        """
        from ocxwiki.app import CLIApp
        from ocxwiki.wiki_manager import WikiManager

        manager, grand_total = _make_mock_wiki_manager(
            n_pages=3, n_enums=2, n_attrs=2, n_simples=1
        )

        # Build a fake publish_complete_schema_async that honours the callback
        async def fake_publish(max_concurrent=10, progress_callback=None):
            results = {
                "pages": 3, "enums": 2, "attributes": 2, "simple_types": 1,
                "errors": [], "total": grand_total,
            }
            if progress_callback:
                # Signal total
                progress_callback(0, grand_total, "Starting…")
                # Simulate per-item advances
                for i in range(grand_total):
                    await asyncio.sleep(0)   # yield to event loop
                    progress_callback(1, None, f"item {i}")
            return results

        async with CLIApp().run_test(size=(120, 40)) as pilot:
            app: CLIApp = pilot.app

            # Replace the singleton inside the TUI
            import ocxwiki.wiki_cli as wiki_cli_module
            original_instance = wiki_cli_module._wiki_manager_instance
            wiki_cli_module._wiki_manager_instance = manager

            try:
                # Build callbacks exactly as the app does
                progress_cb = app._make_progress_callback()
                summary_cb = app._make_summary_callback()

                # Call fake_publish on a background thread (mirrors production)
                def _run_publish():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(
                            fake_publish(progress_callback=progress_cb)
                        )
                    finally:
                        loop.close()

                results = await asyncio.to_thread(_run_publish)

                # Give Textual a moment to process call_from_thread updates
                await pilot.pause(0.2)

                # --- Assertions: progress sink ---
                sink = app.progress_sink
                assert sink._total == grand_total, (
                    f"Expected total={grand_total}, got {sink._total}"
                )
                assert sink._current == grand_total, (
                    f"Expected current={grand_total}, got {sink._current}"
                )

            finally:
                wiki_cli_module._wiki_manager_instance = original_instance

    @pytest.mark.asyncio
    async def test_summary_written_to_output_log(self):
        """
        Verify that calling the summary_callback writes text to the
        #output-log RichLog widget.
        """
        from ocxwiki.app import CLIApp

        async with CLIApp().run_test(size=(120, 40)) as pilot:
            app: CLIApp = pilot.app

            summary_text = (
                "\n[green]✓[/green] Publishing complete!\n"
                "  Pages published:       3\n"
                "  Enums published:       2\n"
                "  Attributes published:  2\n"
                "  Simple types published:1\n"
                "  Total published:       8"
            )

            summary_cb = app._make_summary_callback()

            # Invoke from a thread (as in production)
            await asyncio.to_thread(summary_cb, summary_text)

            # Wait for call_from_thread to execute on the UI thread
            await pilot.pause(0.2)

            # Check that the progress sink is marked complete
            sink = app.progress_sink
            assert sink._current == sink._total, "Summary callback should complete the progress bar"

            # Check the output log contains the summary
            output_log = app.query_one("#output-log", RichLog)
            # RichLog stores lines as Strip objects; convert to plain text for assertion
            rendered = "\n".join(str(line) for line in output_log.lines)
            assert "Publishing complete" in rendered, (
                f"Expected 'Publishing complete' in output log, got:\n{rendered}"
            )

    @pytest.mark.asyncio
    async def test_progress_and_summary_full_pipeline(self):
        """
        Full end-to-end: patch publish_complete_schema_async on the manager,
        run 'wiki publish-all-async' through the TUI dispatch, and verify
        both the progress bar and summary in the output log.
        """
        import ocxwiki.wiki_cli as wiki_cli_module
        from ocxwiki.app import CLIApp
        from ocxwiki.commands.base import dispatch_typer_command

        manager, grand_total = _make_mock_wiki_manager(
            n_pages=2, n_enums=1, n_attrs=1, n_simples=1
        )

        # Intercept progress/summary callbacks captured during dispatch
        captured_progress_calls = []
        captured_summary_calls = []

        async def fake_publish(max_concurrent=10, progress_callback=None):
            results = {
                "pages": 2, "enums": 1, "attributes": 1, "simple_types": 1,
                "errors": [], "total": grand_total,
            }
            if progress_callback:
                progress_callback(0, grand_total, "Starting…")
                for i in range(grand_total):
                    await asyncio.sleep(0)
                    progress_callback(1, None, f"item {i}")
                    captured_progress_calls.append(i)
            return results

        original_instance = wiki_cli_module._wiki_manager_instance
        wiki_cli_module._wiki_manager_instance = manager

        # Patch confirm so it auto-confirms without blocking
        with patch("ocxwiki.wiki_cli.wiki_confirm", return_value=True):
            # Patch publish_complete_schema_async on the singleton
            with patch.object(manager, "publish_complete_schema_async", side_effect=fake_publish):

                async with CLIApp().run_test(size=(120, 40)) as pilot:
                    app: CLIApp = pilot.app

                    # Replace the singleton used by the TUI
                    wiki_cli_module._wiki_manager_instance = manager

                    def _original_make_summary(original_fn=app._make_summary_callback):
                        original_cb = original_fn()

                        def _wrapper(text):
                            captured_summary_calls.append(text)
                            original_cb(text)

                        return _wrapper

                    # Patch the summary factory to also capture calls
                    with patch.object(app, "_make_summary_callback", _original_make_summary):
                        # Dispatch the command (mirrors what the TUI does)
                        from cli import cli as typer_cli
                        result = await dispatch_typer_command(
                            typer_cli,
                            ["wiki", "publish-all-async", "--max-concurrent", "5"],
                            confirm_callback=lambda msg: True,
                            progress_callback=app._make_progress_callback(),
                            summary_callback=app._make_summary_callback(),
                        )

                    await pilot.pause(0.3)

                    # --- Progress bar assertions ---
                    sink = app.progress_sink
                    assert sink._total == grand_total, (
                        f"Progress total should be {grand_total}, got {sink._total}"
                    )
                    assert sink._current == grand_total, (
                        f"Progress current should be {grand_total}, got {sink._current}"
                    )

                    # --- Progress calls assertions ---
                    assert len(captured_progress_calls) == grand_total, (
                        f"Expected {grand_total} item advances, got {len(captured_progress_calls)}"
                    )

                    # --- Summary in output log ---
                    output_log = app.query_one("#output-log", RichLog)
                    rendered = "\n".join(str(line) for line in output_log.lines)
                    assert "Publishing complete" in rendered, (
                        f"Output log should contain publish summary:\n{rendered}"
                    )

        wiki_cli_module._wiki_manager_instance = original_instance


# ---------------------------------------------------------------------------
# Unit test: TextualProgressSink in isolation (no TUI needed)
# ---------------------------------------------------------------------------

class TestTextualProgressSink:
    """Pure unit tests for TextualProgressSink."""

    def test_set_total_updates_widget(self):
        """set_total should delegate to the underlying ProgressBar."""
        from ocxwiki.ui.logging import TextualProgressSink

        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)
        sink.set_total(42.0)

        assert sink._total == 42.0
        mock_pb.update.assert_called_with(total=42.0)

    def test_reset_zeroes_current(self):
        from ocxwiki.ui.logging import TextualProgressSink

        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)
        sink._current = 10.0
        sink.reset()

        assert sink._current == 0.0
        mock_pb.update.assert_called_with(progress=0.0)

    def test_update_advances_current(self):
        from ocxwiki.ui.logging import TextualProgressSink

        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)
        sink.set_total(5.0)

        sink.update(advance=1.0)
        assert sink._current == 1.0

        sink.update(advance=2.5)
        assert sink._current == 3.5

    def test_update_clamps_at_total(self):
        from ocxwiki.ui.logging import TextualProgressSink

        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)
        sink.set_total(3.0)
        sink.update(advance=10.0)

        assert sink._current == 3.0

    def test_complete_sets_current_to_total(self):
        from ocxwiki.ui.logging import TextualProgressSink

        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)
        sink.set_total(7.0)
        sink.complete()

        assert sink._current == 7.0
        mock_pb.update.assert_called_with(progress=7.0)

    def test_set_progress_absolute(self):
        from ocxwiki.ui.logging import TextualProgressSink

        mock_pb = Mock(spec=ProgressBar)
        sink = TextualProgressSink(mock_pb)
        sink.set_total(10.0)
        sink.set_progress(4.5)

        assert sink._current == 4.5
        mock_pb.update.assert_called_with(progress=4.5)


# ---------------------------------------------------------------------------
# Progress callback threading safety
# ---------------------------------------------------------------------------

class TestProgressCallbackThreadSafety:
    """Verify the progress callback is safe to call from a worker thread."""

    @pytest.mark.asyncio
    async def test_callback_called_from_thread(self):
        """
        The production progress_callback uses call_from_thread.
        Verify the sink is updated correctly when called from a thread.
        """
        from ocxwiki.app import CLIApp

        async with CLIApp().run_test(size=(80, 24)) as pilot:
            app: CLIApp = pilot.app

            grand_total = 5
            progress_cb = app._make_progress_callback()

            def _thread_body():
                # Initialise total
                progress_cb(0, grand_total, "Starting…")
                for i in range(grand_total):
                    progress_cb(1, None, f"item {i}")

            await asyncio.to_thread(_thread_body)
            # Let Textual process the queued call_from_thread calls
            await pilot.pause(0.2)

            sink = app.progress_sink
            assert sink._total == grand_total
            assert sink._current == grand_total

    @pytest.mark.asyncio
    async def test_summary_callback_called_from_thread(self):
        """summary_callback must safely update the UI from a worker thread."""
        from ocxwiki.app import CLIApp

        async with CLIApp().run_test(size=(80, 24)) as pilot:
            app: CLIApp = pilot.app
            summary_cb = app._make_summary_callback()

            await asyncio.to_thread(summary_cb, "[green]Done![/green] Summary text here")
            await pilot.pause(0.2)

            # Progress bar should be complete
            sink = app.progress_sink
            assert sink._current == sink._total

            # Output log should contain the summary
            output_log = app.query_one("#output-log", RichLog)
            rendered = "\n".join(str(line) for line in output_log.lines)
            assert "Done" in rendered or "Summary" in rendered


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

