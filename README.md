# Mookie The Music Playa

A self-hosted Discord music bot. Play uploaded audio, supported music links, or song searches in your server's voice channels. Optional Fish Audio integration generates downloadable voice tags.

Installing this project runs your own copy of Mookie using your own Discord bot account. It does not give you access to the owner's bot token. Your computer must stay on and the bot process must remain running.

## Before you start

- Access to this private GitHub repository: the owner must invite you as a collaborator and you must accept.
- A Discord account and a server where you can install apps.
- Python 3.11 or newer, Git, FFmpeg, and Deno 2.3 or newer.
- Your own Discord bot token, created below.

FFmpeg decodes audio; Deno supports YouTube's JavaScript challenges. See the [yt-dlp runtime guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

## 1. Download Mookie

Open Terminal (Mac/Linux) or PowerShell (Windows). Navigate to a local folder where you keep projects, then run:

```sh
git clone https://github.com/thizzclinton/MookieTheMusicPlaya.git
cd MookieTheMusicPlaya
```

For this private repository, use authenticated Git. If you have GitHub CLI installed, run `gh auth login` and `gh auth setup-git` first. Alternatively, use GitHub Desktop to clone it. A GitHub account password will not authenticate an HTTPS Git clone.

Keep the project in a local, non-cloud-synced folder to avoid dependencies being offloaded.

## 2. Install system requirements

### macOS

Install [Homebrew](https://brew.sh/) if you do not have it, then run:

```sh
brew install python ffmpeg deno git
python3 --version
ffmpeg -version
deno --version
```

### Windows

Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/windows/) (enable its PATH option), [Git](https://git-scm.com/downloads), [FFmpeg](https://ffmpeg.org/download.html), and [Deno](https://docs.deno.com/runtime/getting_started/installation/). Ensure FFmpeg and Deno are on your PATH. Reopen PowerShell and check:

```powershell
py -3 --version
git --version
ffmpeg -version
deno --version
```

### Linux (Debian/Ubuntu)

```sh
sudo apt update
sudo apt install python3 python3-venv python3-pip ffmpeg git
```

Install Deno using its [official installation instructions](https://docs.deno.com/runtime/getting_started/installation/). Check `python3 --version` is at least 3.11, and check `ffmpeg -version` and `deno --version`.

## 3. Install Python dependencies

Run these commands from inside `MookieTheMusicPlaya`.

**Mac/Linux:**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

**Windows PowerShell:**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

These commands use the virtual environment directly; no activation or PowerShell execution-policy changes are necessary. Copy the environment example only during first-time setup so you don't overwrite existing credentials.

## 4. Create and invite your Discord bot

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create a new application named Mookie (or any name you prefer).
3. Open **Bot**, generate/reset its token, and save it privately. Leave privileged intents off; this bot uses slash commands and explicitly selected messages.
4. Under **OAuth2 → URL Generator**, select **bot** and **applications.commands**.
5. Select **View Channels**, **Send Messages**, **Read Message History**, **Connect**, and **Speak**. Administrator permission is unnecessary.
6. Open the generated installation URL and choose your server. Make sure channel overrides also allow Connect and Speak.
7. Optionally enable **Developer Mode** in Discord's advanced settings, right-click your server, and copy its ID for quicker command registration in that server.

Discord's [bot setup guide](https://docs.discord.com/developers/quick-start/getting-started) provides additional portal guidance.

## 5. Configure your local token

Open the `.env` file in a text editor. On Mac you can use `open -e .env`; on Windows use `notepad .env`.

```dotenv
DISCORD_TOKEN=your_own_bot_token
DISCORD_GUILD_ID=
```

Put the optional server ID after `DISCORD_GUILD_ID=`. Save the file. Never share your token or commit `.env` to Git; it is ignored by this repository. If a token is exposed, reset it in the Developer Portal and update your local file.

## 6. Start and verify

**Mac/Linux:**

```sh
.venv/bin/python bot.py
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python.exe bot.py
```

Wait for the `Logged in as ... Commands are ready.` message. Keep this terminal open. On Mac, you can prevent idle sleep while running with:

```sh
caffeinate -i .venv/bin/python bot.py
```

Then check real playback:

1. Join a regular Discord voice channel.
2. Use `/play file:` and upload a small MP3.
3. Confirm Mookie joins and you can hear it.
4. Try `/pause`, `/resume`, and `/stop`.
5. Try `/play query:` with a song title or a specific YouTube URL.

You can also right-click an uploaded audio message and choose **Apps → Play attachment** (long-press on mobile).

Press Ctrl+C in the terminal to stop. To start next time, enter the project folder and run the same start command. Don't run two copies with the same token. For continuous availability, use an always-on computer or server; this repository does not set up hosting automatically.

## Updating

Stop Mookie with Ctrl+C, then run these commands inside the project folder:

```sh
git pull --ff-only
```

Mac/Linux:

```sh
.venv/bin/python -m pip install --upgrade -r requirements.txt
.venv/bin/python bot.py
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
.\.venv\Scripts\python.exe bot.py
```

Your `.env` remains local. If you made code changes, save or commit them before pulling updates.

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
