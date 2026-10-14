"""Resolve online audio without blocking Discord's event loop."""
import asyncio
import ipaddress
import json
import os
import shlex
import signal
import socket
import sys
from urllib.parse import urlsplit

LOOKUP_TIMEOUT = 90
CLEANUP_TIMEOUT = 5


class MediaError(ValueError):
    pass


def normalize_query(query):
    query = query.strip().strip("<>").strip()
    if not query or len(query) > 1000:
        raise MediaError("Enter a song/artist or a link (up to 1,000 characters).")
    parsed = urlsplit(query)
    if parsed.scheme:
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise MediaError("Use an http(s) music link, or type a song and artist.")
        if parsed.username or parsed.password:
            raise MediaError("Links containing login credentials aren't supported.")
        host = parsed.hostname.lower()
        if host == "spotify.com" or host.endswith(".spotify.com") or host == "music.apple.com":
            raise MediaError("Spotify and Apple Music links aren't supported. Type the song and artist instead.")
        return query
    if query.startswith(("/", "\\", ".", "~")):
        raise MediaError("For a local file, use the file option or Play attachment.")
    # Never interpret user input as yt-dlp pseudo-URLs or command-line options.
    return "ytsearch1:" + query


async def validate_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise MediaError("The source did not provide a playable web stream.")
    if parsed.username or parsed.password:
        raise MediaError("Links containing login credentials aren't supported.")
    try:
        addresses = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(parsed.hostname, parsed.port or 443,
                                                  type=socket.SOCK_STREAM), 10)
    except (OSError, ValueError, asyncio.TimeoutError) as error:
        raise MediaError("Couldn't reach that music host. Check the link and try again.") from error
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise MediaError("Use a public music link; local/private network addresses aren't supported.")


def select_stream(info):
    if "entries" in info:
        info = next((item for item in (info.get("entries") or []) if item), None)
    if not info or not info.get("url"):
        raise MediaError("No playable result was found. Try a more specific song and artist or another link.")
    if info.get("is_live") or info.get("live_status") == "is_live":
        raise MediaError("Live streams aren't supported; choose a recorded track.")
    if (info.get("duration") or 0) > 14400:
        raise MediaError("Choose a track shorter than four hours.")
    return info


async def resolve(query):
    target = normalize_query(query)
    if not target.startswith("ytsearch1:"):
        await validate_url(target)
    # A separate process lets /skip and /stop cancel slow extractors immediately.
    env = {key: value for key, value in os.environ.items() if key != "DISCORD_TOKEN"}
    process = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-cache-dir",
        "--no-playlist", "--playlist-items", "1", "--dump-single-json", "--skip-download",
        "--no-warnings", "--socket-timeout", "15", "--retries", "1",
        "--extractor-retries", "1", "--format", "bestaudio/best", "--", target,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
        start_new_session=(os.name == "posix"),
    )
    completed = False
    try:
        output, errors = await asyncio.wait_for(process.communicate(), LOOKUP_TIMEOUT)
        completed = True
    except asyncio.TimeoutError as error:
        raise MediaError("Music lookup timed out. Try another link or search.") from error
    finally:
        if not completed:
            try:
                if os.name == "posix" and process.pid:
                    # Kill extractor children too, so they cannot hold the pipes open.
                    os.killpg(process.pid, signal.SIGKILL)
                elif process.returncode is None:
                    process.kill()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(process.communicate(), CLEANUP_TIMEOUT)
            except asyncio.TimeoutError:
                # /skip and /stop must not wait indefinitely for extractor pipes.
                pass
    if process.returncode:
        if b"No module named yt_dlp" in errors:
            raise MediaError("Online playback needs its new dependencies. Run: python -m pip install -U -r requirements.txt")
        raise MediaError("Couldn't load that track. It may be unavailable, restricted, or blocked by the site. Try another link or upload the audio.")
    try:
        info = select_stream(json.loads(output))
    except (json.JSONDecodeError, TypeError) as error:
        raise MediaError("The music source returned an invalid response. Try another track.") from error
    await validate_url(info["url"])
    return info


def stream_options(info):
    # Only network protocols are permitted for an online source.
    options = "-nostdin -protocol_whitelist http,https,tcp,tls,crypto -rw_timeout 15000000 -reconnect 1 -reconnect_delay_max 5"
    headers = info.get("http_headers") or {}
    safe = {key: str(value) for key, value in headers.items()
            if key.lower() in {"user-agent", "referer", "origin"}
            and "\r" not in str(value) and "\n" not in str(value)}
    if safe:
        options += " -headers " + shlex.quote("".join(f"{key}: {value}\r\n" for key, value in safe.items()))
    return options
