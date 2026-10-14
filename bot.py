"""Play uploaded audio, music links, and searches in Discord voice channels."""
import asyncio
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
import io
import os
from pathlib import Path
from queue import SimpleQueue
import shutil
import tempfile
from dataclasses import dataclass

import certifi

# Configure trust before aiohttp builds its SSL contexts during import.
# Framework Python on macOS may not have a default certificate bundle installed.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import discord
from discord import app_commands
from dotenv import load_dotenv

import media
import fish_tts

log = logging.getLogger("upload-player")
EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".opus", ".m4a", ".aac", ".webm"}
MAX_BYTES = 100 * 1024 * 1024
MAX_QUEUE = 20


def configure_logging():
    # Terminal writes can stall; keep all log I/O off Discord's event loop.
    directory = Path(__file__).with_name("logs")
    directory.mkdir(exist_ok=True)
    handler = RotatingFileHandler(directory / "mookie.log", maxBytes=2_000_000,
                                 backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    messages = SimpleQueue()
    logging.basicConfig(level=logging.INFO, handlers=[QueueHandler(messages)], force=True)
    listener = QueueListener(messages, handler)
    listener.start()
    return listener


@dataclass
class Track:
    path: Path | None
    name: str
    channel: object
    query: str | None = None

    def cleanup(self):
        if self.path:
            self.path.unlink(missing_ok=True)


class Player:
    def __init__(self, guild):
        self.guild = guild
        self.lock = asyncio.Lock()
        self.queue = asyncio.Queue()
        self.task = None
        self.current = None
        self.playback = None

    async def play_track(self, track):
        source = None
        played = False
        try:
            if track.query:
                info = await media.resolve(track.query)
                track.name = info.get("title") or track.name
                location = info["url"]
                before = media.stream_options(info)
            else:
                location = str(track.path)
                before = "-nostdin -protocol_whitelist file,pipe"
            voice = self.guild.voice_client
            if not voice or not voice.is_connected():
                raise ValueError("Voice connection was lost; use /stop and try again.")
            source = discord.FFmpegOpusAudio(
                location, before_options=before, options="-vn -t 14400", stderr=None)
            loop = asyncio.get_running_loop()
            finished = loop.create_future()

            def complete(error):
                if not finished.done():
                    finished.set_result(error)

            voice.play(source, after=lambda error: loop.call_soon_threadsafe(complete, error))
            played = True
            error = await finished
            if error:
                raise error
        finally:
            if source:
                if played:
                    # Discord's audio thread owns cleanup after a successful play.
                    voice.stop()
                else:
                    # A rejected source is still ours; FFmpeg cleanup can block.
                    await asyncio.to_thread(source.cleanup)

    def skip(self):
        if self.playback and not self.playback.done():
            self.playback.cancel()

    async def run(self):
        try:
            while True:
                track = await self.queue.get()
                self.current = track
                try:
                    self.playback = asyncio.create_task(self.play_track(track))
                    await self.playback
                except asyncio.CancelledError:
                    if asyncio.current_task().cancelling():
                        raise
                    # Cancelling just the child means /skip; keep the queue running.
                except Exception as error:
                    log.exception("Playback failed")
                    try:
                        await track.channel.send(
                            (str(error) if isinstance(error, ValueError) else
                             "Couldn't play that track. Try another link or a valid audio upload."),
                            allowed_mentions=discord.AllowedMentions.none(),
                        )
                    except discord.HTTPException:
                        pass
                finally:
                    self.playback = None
                    track.cleanup()
                    self.current = None
                    self.queue.task_done()
        finally:
            while not self.queue.empty():
                track = self.queue.get_nowait()
                track.cleanup()
                self.queue.task_done()

    async def stop(self):
        voice = self.guild.voice_client
        if voice:
            voice.stop()
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
            self.task = None
        # Also handle a task cancelled before its coroutine ever starts.
        while not self.queue.empty():
            track = self.queue.get_nowait()
            track.cleanup()
            self.queue.task_done()
        if voice:
            await voice.disconnect(force=True)


class UploadBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.voice_states = True
        super().__init__(intents=intents, allowed_mentions=discord.AllowedMentions.none())
        self.tree = app_commands.CommandTree(self)
        self.players = {}
        self.files = tempfile.TemporaryDirectory(prefix="discord-upload-player-")

    async def setup_hook(self):
        # Global commands work in every server that installs the bot.
        await self.tree.sync()
        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)

    async def on_ready(self):
        log.info("Logged in as %s. Commands are ready.", self.user)

    async def close(self):
        try:
            for player in self.players.values():
                await player.stop()
        finally:
            await super().close()
            self.files.cleanup()


bot = UploadBot()


def member_channel(interaction):
    member = interaction.user
    if not interaction.guild or not isinstance(member, discord.Member):
        raise ValueError("Use this in a server.")
    channel = member.voice.channel if member.voice else None
    if not isinstance(channel, discord.VoiceChannel):
        raise ValueError("Join a regular voice channel first.")
    voice = interaction.guild.voice_client
    if voice and voice.channel.id != channel.id:
        raise ValueError("Join the bot's voice channel to control its music.")
    return channel


async def enqueue(interaction, attachment):
    await interaction.response.defer(ephemeral=True, thinking=True)
    guild = interaction.guild
    member_channel(interaction)
    suffix = Path(attachment.filename).suffix.lower()
    if suffix not in EXTENSIONS:
        raise ValueError("Choose an MP3, WAV, FLAC, OGG, Opus, M4A, AAC, or WebM audio file.")
    if attachment.size > MAX_BYTES:
        raise ValueError("This bot accepts files up to 100 MiB each.")
    player = bot.players.setdefault(guild.id, Player(guild))
    async with player.lock:
        channel = member_channel(interaction)
        if player.queue.qsize() >= MAX_QUEUE:
            raise ValueError("The queue is full (20 waiting tracks). Try again later.")
        fd, filename = tempfile.mkstemp(suffix=suffix, dir=bot.files.name)
        os.close(fd)
        path = Path(filename)
        try:
            # Download now: Discord attachment links expire, but queued local files don't.
            await asyncio.wait_for(attachment.save(path), timeout=60)
            if path.stat().st_size > MAX_BYTES:
                raise ValueError("This file exceeds the 100 MiB limit.")
            channel = member_channel(interaction)
            if not guild.voice_client:
                permissions = channel.permissions_for(guild.me)
                if not permissions.connect or not permissions.speak:
                    raise ValueError("I need Connect and Speak permissions in your voice channel.")
                await channel.connect(timeout=30, self_deaf=True)
            elif not guild.voice_client.is_connected():
                raise ValueError("The voice connection was lost. Use /stop, then try again.")
            player.queue.put_nowait(Track(path, attachment.filename, interaction.channel))
            if not player.task or player.task.done():
                player.task = asyncio.create_task(player.run())
        except BaseException:
            path.unlink(missing_ok=True)
            raise
    await interaction.followup.send("Added your audio to the queue.", ephemeral=True)


async def enqueue_query(interaction, query):
    await interaction.response.defer(ephemeral=True, thinking=True)
    media.normalize_query(query)  # Validate before connecting.
    guild = interaction.guild
    member_channel(interaction)
    player = bot.players.setdefault(guild.id, Player(guild))
    async with player.lock:
        channel = member_channel(interaction)
        if player.queue.qsize() >= MAX_QUEUE:
            raise ValueError("The queue is full (20 waiting tracks). Try again later.")
        if not guild.voice_client:
            permissions = channel.permissions_for(guild.me)
            if not permissions.connect or not permissions.speak:
                raise ValueError("I need Connect and Speak permissions in your voice channel.")
            await channel.connect(timeout=30, self_deaf=True)
        elif not guild.voice_client.is_connected():
            raise ValueError("The voice connection was lost. Use /stop, then try again.")
        player.queue.put_nowait(Track(None, query.strip()[:200], interaction.channel, query=query))
        if not player.task or player.task.done():
            player.task = asyncio.create_task(player.run())
    await interaction.followup.send("Added to the queue. I'll load it when its turn comes.", ephemeral=True)


@bot.tree.command(name="play", description="Play an uploaded file, music link, or song search")
@app_commands.guild_only()
@app_commands.describe(query="Paste a music link or type a song and artist", file="Upload an audio file instead")
async def play(interaction: discord.Interaction, query: str | None = None, file: discord.Attachment | None = None):
    if (query is None) == (file is None):
        raise ValueError("Choose either query (a link or song search) or file, not both.")
    if file is not None:
        await enqueue(interaction, file)
    else:
        await enqueue_query(interaction, query)


@bot.tree.command(name="tag", description="Generate a spoken voice tag as an MP3 with Fish Audio")
@app_commands.guild_only()
@app_commands.describe(text="What the voice should say (up to 500 characters)")
@app_commands.checks.cooldown(1, 30.0, key=lambda i: (i.guild_id, i.user.id))
async def tag(interaction: discord.Interaction, text: app_commands.Range[str, 1, 500]):
    await interaction.response.defer(ephemeral=True, thinking=True)
    async with tag_slots:
        audio = await fish_tts.synthesize(text)
    buffer = io.BytesIO(audio)
    clip = discord.File(buffer, filename="mookie-tag.mp3")
    try:
        await interaction.followup.send("Your voice tag is ready.", file=clip, ephemeral=True)
    finally:
        clip.close()
        buffer.close()


tag_slots = asyncio.Semaphore(2)


@bot.tree.context_menu(name="Play attachment")
@app_commands.guild_only()
async def play_attachment(interaction: discord.Interaction, message: discord.Message):
    audio = [a for a in message.attachments if Path(a.filename).suffix.lower() in EXTENSIONS]
    if not audio:
        raise ValueError("That message has no supported audio attachment.")
    await enqueue(interaction, audio[0])


@bot.tree.command(name="queue", description="Show the current track and number of waiting tracks")
@app_commands.guild_only()
async def show_queue(interaction: discord.Interaction):
    member_channel(interaction)
    player = bot.players.get(interaction.guild_id)
    current = player.current.name if player and player.current else "Nothing playing"
    current = discord.utils.escape_markdown(current)[:200]
    await interaction.response.send_message(
        f"Current: {current}\nWaiting: {player.queue.qsize() if player else 0}", ephemeral=True)


async def control(interaction, action):
    await interaction.response.defer(ephemeral=True)
    member_channel(interaction)
    player = bot.players.get(interaction.guild_id)
    if not player:
        raise ValueError("No music session is active.")
    async with player.lock:
        member_channel(interaction)
        voice = interaction.guild.voice_client
        if action == "stop":
            await player.stop()
        elif action == "skip" and player.current:
            player.skip()
        elif not voice or not (voice.is_playing() or voice.is_paused()):
            raise ValueError("Nothing is playing yet.")
        elif action == "pause":
            voice.pause()
        elif action == "resume":
            voice.resume()
    await interaction.followup.send({"stop": "Queue cleared and disconnected.", "skip": "Skipped.",
                                    "pause": "Paused.", "resume": "Resumed."}[action], ephemeral=True)


@bot.tree.command(description="Skip the current track")
@app_commands.guild_only()
async def skip(interaction: discord.Interaction):
    await control(interaction, "skip")


@bot.tree.command(description="Pause playback")
@app_commands.guild_only()
async def pause(interaction: discord.Interaction):
    await control(interaction, "pause")


@bot.tree.command(description="Resume playback")
@app_commands.guild_only()
async def resume(interaction: discord.Interaction):
    await control(interaction, "resume")


@bot.tree.command(description="Clear the queue and disconnect")
@app_commands.guild_only()
async def stop(interaction: discord.Interaction):
    await control(interaction, "stop")


@bot.tree.error
async def command_error(interaction, error):
    original = getattr(error, "original", error)
    if isinstance(original, discord.NotFound) and original.code in {10062, 10015}:
        log.warning("A command expired before Discord could accept its response; retry the command.")
        return
    if isinstance(original, app_commands.CommandOnCooldown):
        message = f"Try /tag again in {original.retry_after:.0f} seconds."
    elif isinstance(original, ValueError):
        message = str(original)
    elif isinstance(original, asyncio.TimeoutError):
        message = "Download or voice connection timed out. Please try again."
    else:
        log.error("Command failed", exc_info=(type(original), original, original.__traceback__))
        message = "That didn't work. Check my channel permissions and the bot terminal for details."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.NotFound:
        # An expired interaction cannot receive another error response.
        log.warning("The command response expired before its error message could be delivered.")


if __name__ == "__main__":
    load_dotenv(Path(__file__).with_name(".env"))
    if not shutil.which("ffmpeg"):
        raise SystemExit("Install FFmpeg first; see README.md.")
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "paste_your_bot_token_here":
        raise SystemExit("Add your bot token to .env; see README.md. Never share it in chat.")
    listener = configure_logging()
    print(f"Mookie is starting. Logs: {Path(__file__).with_name('logs') / 'mookie.log'}", flush=True)
    try:
        bot.run(token, log_handler=None)
    finally:
        listener.stop()
        for handler in listener.handlers:
            handler.close()
