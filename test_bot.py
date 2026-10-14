"""Offline checks: python -m unittest -v test_bot.py"""
import asyncio
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import wave

import bot


class Voice:
    def __init__(self):
        self.after = None
        self.played = 0

    def is_connected(self):
        return True

    def play(self, source, after):
        self.after = after
        self.played += 1

    def stop(self):
        if self.after:
            callback, self.after = self.after, None
            callback(None)

    async def disconnect(self, force=False):
        pass


class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.voice = Voice()
        self.player = bot.Player(SimpleNamespace(voice_client=self.voice))

    async def asyncTearDown(self):
        await self.player.stop()
        self.temp.cleanup()

    def track(self, name):
        path = Path(self.temp.name) / name
        path.write_bytes(b"test")
        track = bot.Track(path, name, SimpleNamespace(send=AsyncMock()))
        self.player.queue.put_nowait(track)
        return track

    async def wait_until(self, predicate):
        async with asyncio.timeout(2):
            while not predicate():
                await asyncio.sleep(0.001)

    async def test_completion_advances_and_stop_deletes_all_files(self):
        first, second, third = [self.track(f"{i}.mp3") for i in range(3)]
        with patch.object(bot.discord, "FFmpegOpusAudio"):
            self.player.task = asyncio.create_task(self.player.run())
            await self.wait_until(lambda: self.voice.played == 1)
            self.voice.stop()
            await self.wait_until(lambda: self.voice.played == 2)
            self.assertFalse(first.path.exists())
            await self.player.stop()
        self.assertFalse(second.path.exists())
        self.assertFalse(third.path.exists())
        self.assertTrue(self.player.queue.empty())

    async def test_stop_before_worker_starts_deletes_queued_files(self):
        track = self.track("queued.mp3")
        self.player.task = asyncio.create_task(self.player.run())
        await self.player.stop()
        self.assertFalse(track.path.exists())
        self.assertTrue(self.player.queue.empty())

    async def test_failed_playback_cleans_file_and_reports_error(self):
        track = self.track("broken.mp3")
        with patch.object(bot.discord, "FFmpegOpusAudio", side_effect=RuntimeError("test failure")):
            with self.assertLogs("upload-player", level="ERROR"):
                self.player.task = asyncio.create_task(self.player.run())
                await asyncio.wait_for(self.player.queue.join(), 2)
        self.assertFalse(track.path.exists())
        track.channel.send.assert_awaited_once()


class ConfigurationTests(unittest.TestCase):
    def test_registered_commands_and_intents(self):
        self.assertEqual({c.name for c in bot.bot.tree.get_commands()},
                         {"play", "Play attachment", "queue", "pause", "resume", "skip", "stop", "tag"})
        self.assertFalse(bot.bot.intents.message_content)
        self.assertTrue(bot.bot.intents.voice_states)

    def test_real_ffmpeg_produces_opus_packet(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(48000)
                wav.writeframes(b"\0" * 19200)
            source = bot.discord.FFmpegOpusAudio(
                str(path), before_options="-nostdin -protocol_whitelist file,pipe",
                options="-vn -t 14400")
            try:
                self.assertTrue(source.is_opus())
                self.assertTrue(source.read())
            finally:
                source.cleanup()


class OnlineQueueTests(QueueTests):
    async def test_skip_during_lookup_continues_to_upload(self):
        started = asyncio.Event()
        cancelled = asyncio.Event()

        async def slow_lookup(query):
            started.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()

        self.player.queue.put_nowait(bot.Track(None, "search", SimpleNamespace(send=AsyncMock()), "song"))
        upload = self.track("next.mp3")
        with patch.object(bot.media, "resolve", side_effect=slow_lookup), patch.object(bot.discord, "FFmpegOpusAudio"):
            self.player.task = asyncio.create_task(self.player.run())
            await asyncio.wait_for(started.wait(), 2)
            self.player.skip()
            await self.wait_until(lambda: self.voice.played == 1)
            self.assertTrue(cancelled.is_set())
            self.assertEqual(self.player.current, upload)

    async def test_stop_cancels_lookup_and_clears_upload(self):
        started = asyncio.Event()

        async def slow_lookup(query):
            started.set()
            await asyncio.Future()

        self.player.queue.put_nowait(bot.Track(None, "search", SimpleNamespace(send=AsyncMock()), "song"))
        upload = self.track("waiting.mp3")
        with patch.object(bot.media, "resolve", side_effect=slow_lookup):
            self.player.task = asyncio.create_task(self.player.run())
            await asyncio.wait_for(started.wait(), 2)
            await asyncio.wait_for(self.player.stop(), 2)
        self.assertFalse(upload.path.exists())
        self.assertTrue(self.player.queue.empty())

    async def test_remote_stream_resolved_when_played(self):
        track = bot.Track(None, "query", SimpleNamespace(send=AsyncMock()), "song")
        self.player.queue.put_nowait(track)
        info = {"url": "https://example.com/song.mp3", "title": "Resolved song"}
        with patch.object(bot.media, "resolve", new=AsyncMock(return_value=info)) as resolve:
            with patch.object(bot.discord, "FFmpegOpusAudio") as source:
                self.player.task = asyncio.create_task(self.player.run())
                await self.wait_until(lambda: self.voice.played == 1)
                resolve.assert_awaited_once_with("song")
                self.assertEqual(track.name, "Resolved song")
                self.assertEqual(source.call_args.args[0], info["url"])


class MediaTests(unittest.IsolatedAsyncioTestCase):
    def test_search_and_url_normalization(self):
        self.assertEqual(bot.media.normalize_query(" artist song "), "ytsearch1:artist song")
        self.assertEqual(bot.media.normalize_query("<https://example.com/audio.mp3>"), "https://example.com/audio.mp3")
        for value in ["", "file:///etc/passwd", "ytsearch100:music", "https://open.spotify.com/track/123"]:
            with self.assertRaises(ValueError):
                bot.media.normalize_query(value)

    def test_missing_results_and_live_streams(self):
        for info in [{"entries": []}, {"url": "https://example.com", "is_live": True}]:
            with self.assertRaises(ValueError):
                bot.media.select_stream(info)
        info = {"url": "https://example.com/song.mp3", "title": "one"}
        self.assertEqual(bot.media.select_stream({"entries": [info]}), info)

    async def test_private_addresses_rejected(self):
        for value in ["http://127.0.0.1/music.mp3", "http://[::1]/music.mp3"]:
            with self.assertRaises(ValueError):
                await bot.media.validate_url(value)

    async def test_resolver_cancel_kills_process(self):
        process = SimpleNamespace(returncode=None, pid=None, kill=unittest.mock.Mock())
        started = asyncio.Event()

        async def communicate():
            if process.kill.called:
                process.returncode = -9
                return b"", b""
            started.set()
            await asyncio.Future()

        process.communicate = communicate
        with patch.object(bot.media.asyncio, "create_subprocess_exec", new=AsyncMock(return_value=process)):
            task = asyncio.create_task(bot.media.resolve("some song"))
            await asyncio.wait_for(started.wait(), 2)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        process.kill.assert_called_once()


if __name__ == "__main__":
    unittest.main()
