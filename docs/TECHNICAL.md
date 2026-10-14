# Extra setup and developer information

Start with [the main installation guide](../README.md). These sections are optional.

## Linux (Debian/Ubuntu)

Install Python 3.11 or newer and FFmpeg:

```sh
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg
```

Install Deno 2.3 or newer using its [official instructions](https://docs.deno.com/runtime/getting_started/installation/). Download and extract the repository ZIP as described in the main guide, then open a terminal in the folder containing `bot.py`.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Add your own Discord token to `.env` using a text editor. Create and invite the bot as described in the main guide, then run:

```sh
.venv/bin/python bot.py
```

## Updating a ZIP download

Stop Mookie. Download the new ZIP and extract it into a separate folder. Copy your local `.env` into the new folder, then repeat the environment creation and dependency installation there. Keep the old folder until the new version passes a playback check. Never upload `.env` to GitHub.

## Commands

| Command | Action |
| --- | --- |
| Message → Apps → Play attachment | Queue the first supported audio attachment in an existing message |
| `/play file:` | Upload and queue an audio file |
| `/play query:` | Queue a music URL or the first YouTube search match |
| `/queue` | Show current filename and waiting track count |
| `/pause` / `/resume` | Control current playback |
| `/skip` | Skip current track, including a pending online lookup |
| `/stop` | Clear queued files and disconnect |

Anyone in the bot's voice channel can control it. Each server has an independent queue. The bot stays connected when the queue ends; use `/stop` to disconnect. It supports regular voice channels, not Stage channels.

## Limits and troubleshooting

- Online playback uses yt-dlp and streams through FFmpeg. Tested with a public MP3 link and a YouTube song search. Other supported sites, including SoundCloud, may depend on regional availability or site restrictions.
- Spotify/Apple Music subscription streaming, login-required content, live streams, and full-playlist queuing are not supported. A playlist URL selects at most its first item; a video URL containing a playlist plays that video.
- Search plays the first YouTube match automatically. Use a specific track URL if you want a particular version.
- Tracks are resolved when their turn comes, so queued stream links do not expire while waiting. Lookup has a 90-second timeout and can be cancelled with `/skip` or `/stop`. Errors appear in the text channel where the track was requested; the queue then continues.
- If a music site stops working, update with `python -m pip install --upgrade "yt-dlp[default]"`, restart, and retry. Some site blocks cannot be fixed by updating.
- Accepted extensions: MP3, WAV, FLAC, OGG, Opus, M4A, AAC, WebM. Files must actually contain decodable audio.
- Maximum 100 MiB per uploaded file, 20 waiting tracks per server, and four hours of playback per track. Discord's own upload limit still applies.
- Files are downloaded to a temporary folder at queue time and removed after playback, skip, stop, or graceful shutdown. Forced termination can leave temporary files in the OS temp directory. Queues do not persist across restarts.
- Missing commands: check installation scopes, server ID, bot startup logs, and restart Discord. Global commands may take time to propagate.
- Bot joins but is silent: confirm Speak permission, that it isn't server-muted, and that FFmpeg is installed. Test with a normal MP3. Invalid audio can end immediately; inspect Terminal for FFmpeg errors.
- Voice connection lost: use `/stop` and queue the file again.
- Voice dependency errors: recreate the virtual environment and reinstall requirements. The pinned discord.py version includes support for Discord's DAVE voice encryption through the voice extras.

## Implementation references

- Online media resolver: https://github.com/yt-dlp/yt-dlp
- YouTube JS runtime setup: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- discord.py: https://github.com/Rapptz/discord.py
- DAVE support: https://github.com/Rapptz/discord.py/blob/master/docs/whats_new.rst
- Selected-message content exception: https://github.com/discord/discord-api-docs/blob/main/developers/events/gateway.mdx
- Expiring attachment URLs: https://github.com/discord/discord-api-docs/blob/main/developers/reference.mdx

Live server playback requires your own bot token and server. Local tests cannot verify Discord permissions or hear the resulting voice stream.

## Local verification

Runtime logs are written to `logs/mookie.log` and rotated automatically. Logging runs
on a background thread so a slow terminal cannot block Discord's heartbeat or slash commands.
To see connection and playback details, run `tail -f logs/mookie.log` in another terminal.

Mac/Linux:

```sh
.venv/bin/python -m unittest -v test_bot.py test_fish_tts.py test_runtime.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_bot.py test_fish_tts.py test_runtime.py
```

Offline tests cover command registration, FFmpeg Opus output, queue advancement, cleanup, mixed online/upload playback, cancellation during lookup, input validation, and subprocess cancellation. A new installation still needs the live playback check described above. These tests do not prove playback on every operating system or network.

## Fish Audio voice tags
Set `FISH_API_KEY` and `FISH_VOICE_ID` in `.env`, then restart the bot.
Use `/tag text: Thizz Clinton. Turn the bass up.` to receive a private downloadable MP3.
No voice-channel connection is required. Limit: 500 characters, one request per user per server every 30 seconds.
The default model is `s2.1-pro-free`; optionally set `FISH_TTS_MODEL` to another supported Fish model. Provider access and pricing can change; check your Fish Audio account before using this feature.
This does not implement Spotify support. Credentials alone do not enable it.
