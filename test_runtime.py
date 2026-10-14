"""Regression tests for cancelled media jobs and Discord runtime failures."""
import asyncio
import logging
from pathlib import Path
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import discord

import bot
import media


def missing_interaction(code=10062):
    response = SimpleNamespace(status=404, reason="Not Found")
    return discord.NotFound(response, {"code": code, "message": "Unknown interaction"})


def interaction(*, done=False):
    return SimpleNamespace(
        response=SimpleNamespace(
            is_done=Mock(return_value=done), send_message=AsyncMock()
        ),
        followup=SimpleNamespace(send=AsyncMock()),
    )


class InteractionErrors(unittest.IsolatedAsyncioTestCase):
    async def test_expired_interaction_is_not_answered_again(self):
        for code in (10062, 10015):
            with self.subTest(code=code):
                request = interaction()
                await bot.command_error(
                    request, SimpleNamespace(original=missing_interaction(code))
                )
                request.response.send_message.assert_not_awaited()
                request.followup.send.assert_not_awaited()

    async def test_error_response_disappearing_does_not_raise(self):
        for done in (False, True):
            with self.subTest(done=done):
                request = interaction(done=done)
                sender = request.followup.send if done else request.response.send_message
                sender.side_effect = missing_interaction()
                await bot.command_error(request, ValueError("Join a voice channel first."))
                sender.assert_awaited_once()

    async def test_validation_error_still_reaches_user(self):
        request = interaction(done=True)
        await bot.command_error(request, ValueError("Join a voice channel first."))
        request.followup.send.assert_awaited_once_with(
            "Join a voice channel first.", ephemeral=True
        )


class BackgroundLogging(unittest.IsolatedAsyncioTestCase):
    async def test_blocked_log_writer_does_not_block_discord_loop(self):
        started = threading.Event()
        release = threading.Event()
        emitted_on = []

        class BlockingHandler(logging.Handler):
            def emit(self, record):
                emitted_on.append(threading.get_ident())
                started.set()
                release.wait(2)

        handler = BlockingHandler()
        root = logging.getLogger()
        original_handlers = root.handlers[:]
        original_level = root.level
        listener = None
        loop_thread = threading.get_ident()
        heartbeat = asyncio.Event()

        async def tick():
            await asyncio.sleep(0)
            heartbeat.set()

        task = asyncio.create_task(tick())
        try:
            with patch.object(bot, "RotatingFileHandler", return_value=handler):
                listener = bot.configure_logging()
            before = time.monotonic()
            logging.getLogger("mookie-runtime-test").warning("writer is deliberately blocked")
            elapsed = time.monotonic() - before
            self.assertLess(elapsed, 0.25)
            self.assertTrue(await asyncio.to_thread(started.wait, 1))
            await asyncio.wait_for(heartbeat.wait(), 1)
            self.assertFalse(release.is_set())
            self.assertNotEqual(emitted_on, [loop_thread])
        finally:
            release.set()
            if listener is not None:
                listener.stop()
            for current in root.handlers[:]:
                root.removeHandler(current)
                if current not in original_handlers:
                    current.close()
            for original in original_handlers:
                root.addHandler(original)
            root.setLevel(original_level)
            handler.close()
            await task


class PlaybackCleanup(unittest.IsolatedAsyncioTestCase):
    def make_player(self):
        voice = Mock()
        voice.is_connected.return_value = True
        return bot.Player(SimpleNamespace(voice_client=voice)), voice

    async def test_started_audio_leaves_cleanup_to_discord_player(self):
        player, voice = self.make_player()
        source = Mock()

        def play(audio, *, after):
            self.assertIs(audio, source)
            after(None)

        voice.play.side_effect = play
        track = bot.Track(Path("/tmp/mookie-runtime-test.wav"), "track", Mock())
        with patch.object(bot.discord, "FFmpegOpusAudio", return_value=source):
            await player.play_track(track)
        source.cleanup.assert_not_called()
        voice.stop.assert_called_once()

    async def test_unused_source_is_cleaned_outside_event_loop(self):
        player, voice = self.make_player()
        voice.play.side_effect = RuntimeError("Voice playback refused")
        source = Mock()
        cleaned_on = []
        source.cleanup.side_effect = lambda: cleaned_on.append(threading.get_ident())
        loop_thread = threading.get_ident()
        track = bot.Track(Path("/tmp/mookie-runtime-test.wav"), "track", Mock())
        with patch.object(bot.discord, "FFmpegOpusAudio", return_value=source):
            with self.assertRaisesRegex(RuntimeError, "Voice playback refused"):
                await player.play_track(track)
        source.cleanup.assert_called_once()
        self.assertNotEqual(cleaned_on, [loop_thread])


class ExtractorCancellation(unittest.IsolatedAsyncioTestCase):
    def process(self):
        process = SimpleNamespace(returncode=None, pid=None, kill=Mock())
        process.kill.side_effect = lambda: setattr(process, "returncode", -9)
        return process

    async def test_lookup_timeout_kills_and_drains_child(self):
        process = self.process()
        calls = 0

        async def communicate():
            nonlocal calls
            calls += 1
            if calls == 1:
                await asyncio.Future()
            return b"", b""

        process.communicate = AsyncMock(side_effect=communicate)
        with patch.object(media.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)), \
             patch.object(media, "LOOKUP_TIMEOUT", 0.02), \
             patch.object(media, "CLEANUP_TIMEOUT", 0.02):
            with self.assertRaisesRegex(media.MediaError, "lookup timed out"):
                await asyncio.wait_for(media.resolve("test song"), 1)
        process.kill.assert_called_once()
        self.assertGreaterEqual(process.communicate.await_count, 2)

    async def test_cancelling_lookup_kills_child_and_preserves_cancellation(self):
        process = self.process()
        started = asyncio.Event()
        calls = 0

        async def communicate():
            nonlocal calls
            calls += 1
            if calls == 1:
                started.set()
                await asyncio.Future()
            return b"", b""

        process.communicate = AsyncMock(side_effect=communicate)
        with patch.object(media.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)), \
             patch.object(media, "CLEANUP_TIMEOUT", 0.02):
            task = asyncio.create_task(media.resolve("test song"))
            await asyncio.wait_for(started.wait(), 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await asyncio.wait_for(task, 1)
        process.kill.assert_called_once()
        self.assertGreaterEqual(process.communicate.await_count, 2)

    async def test_stalled_child_cleanup_is_bounded(self):
        process = self.process()

        async def communicate():
            await asyncio.Future()

        process.communicate = AsyncMock(side_effect=communicate)
        with patch.object(media.asyncio, "create_subprocess_exec", AsyncMock(return_value=process)), \
             patch.object(media, "LOOKUP_TIMEOUT", 0.02), \
             patch.object(media, "CLEANUP_TIMEOUT", 0.02):
            with self.assertRaisesRegex(media.MediaError, "lookup timed out"):
                await asyncio.wait_for(media.resolve("test song"), 1)
        process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
