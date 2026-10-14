# Discord Upload Player

Play uploaded audio, music URLs, and song searches in a server voice channel.

1. Join a voice channel.
2. Right-click a message containing your uploaded song → **Apps → Play attachment** (on mobile, long-press the message).
3. The bot joins you and plays it. More selections join the queue.

You can also use `/play` with either **query** or **file**:

- `/play query: Daft Punk One More Time` — plays the first YouTube search result.
- `/play query: https://www.youtube.com/watch?v=...` — plays the linked track.
- `/play query: https://soundcloud.com/artist/track` — plays a supported public SoundCloud track.
- `/play file:` — upload your own audio.

Choose one input per command. Uploaded files and online tracks use the same queue and controls.

## Updating your existing bot

On this Mac, `.venv` points to the local runtime at
`/Users/theozarrinkelk/Library/Application Support/Mookie/runtime`.
This keeps music libraries outside iCloud-managed Documents, where offloaded files
were causing song lookups to hang. The previous environment is preserved as
`.venv-icloud-backup-20261003`. Your usual startup command still works:

```sh
caffeinate -i .venv/bin/python bot.py
```

The code in this folder has already been updated. Your `.env` stays the same. Stop the running process with **Control+C**, then, with the virtual environment active:

```sh
python -m pip install --upgrade -r requirements.txt
brew install deno
python bot.py
```

Deno is needed for current YouTube support. Skip its installation if already installed. On this Mac, Deno was found during setup. The bot registers the new `/play` options at startup; if Discord shows the old command, reopen Discord after restarting the bot.


## First-time setup on your Mac

### 1. Create and invite the bot

- Open https://discord.com/developers/applications and choose **New Application**. Name it **Upload Player**.
- On the **Bot** page, generate/reset the bot token. Save it privately for step 3. Never paste it into chat or commit it to Git.
- Leave privileged intents off. This bot uses slash commands and explicitly selected messages.
- Under **OAuth2 → URL Generator**, select scopes **bot** and **applications.commands**.
- Select permissions **View Channels**, **Send Messages**, **Read Message History**, **Connect**, and **Speak**. Administrator permission is unnecessary.
- Open the generated URL and install it in a server you manage. Channel permission overrides must also allow the bot to connect and speak.
- Optional: in Discord enable **User Settings → Advanced → Developer Mode**, right-click your server, and **Copy Server ID**. Putting this ID in `.env` registers commands immediately in that server; commands are also registered globally for any other server that installs the bot.

### 2. Install requirements

Use Python 3.11 or newer, FFmpeg, and Deno 2.3 or newer. With Homebrew installed:

```sh
brew install python ffmpeg deno
```

Open Terminal in this downloaded project folder, then run:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

On Windows, activate with `.venv\Scripts\activate` and install FFmpeg on your PATH. On Debian/Ubuntu, install `python3-venv` and `ffmpeg` using your package manager.

### 3. Add your token locally

Open `.env` in a text editor:

```dotenv
DISCORD_TOKEN=your_actual_bot_token
DISCORD_GUILD_ID=your_server_id
```

The server ID is optional. Commands register globally for all servers that install the bot and may take time to appear. If set, the ID also gives that server an immediately updated copy of the commands.

### 4. Start

```sh
python bot.py
```

Keep Terminal running and your computer awake. Press Ctrl+C to stop the bot. For continuous availability, run this folder on an always-on computer or server with Python, FFmpeg, and outbound Discord voice connectivity.

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

Live server playback requires your own token and server. Local checks cannot verify Discord permissions or hear the resulting voice stream.

## Local verification

Runtime logs are written to `logs/mookie.log` and rotated automatically. Logging runs
on a background thread so a slow terminal cannot block Discord's heartbeat or slash commands.
To see connection and playback details, run `tail -f logs/mookie.log` in another terminal.

With the virtual environment activated, run:

```sh
python -m unittest -v test_bot.py test_fish_tts.py test_runtime.py
```

Offline tests cover command registration, FFmpeg Opus output, queue advancement, cleanup, mixed online/upload playback, cancellation during lookup, input validation, and subprocess cancellation. Local audio conversion and live HTTP audio/YouTube-search decoding passed during development. Delivery through an actual Discord voice session still needs testing after restart.

## Fish Audio voice tags
Set `FISH_API_KEY` and `FISH_VOICE_ID` in `.env`, then restart the bot.
Use `/tag text: Thizz Clinton. Turn the bass up.` to receive a private downloadable MP3.
No voice-channel connection is required. Limit: 500 characters, one request per user per server every 30 seconds.
The default model is `s2.1-pro-free`; optionally set `FISH_TTS_MODEL` to another supported Fish model. Paid models can incur usage charges.
This does not implement Spotify support. Credentials alone do not enable it.
