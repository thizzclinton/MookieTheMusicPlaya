# Mookie The Music Playa

Mookie plays music in a Discord voice channel. You can upload a song, paste a music link, or search for a song by name.

**You do not need to know how to code.** You will need to install a few tools, create your own Discord bot, and copy some commands. Follow one step at a time.

This runs your own copy of Mookie on your computer. Your computer needs to stay on, connected to the internet, and awake while Mookie is playing.

## Before you start

You need a Mac or Windows computer, a Discord account, and a Discord server where you can add bots. You also need a GitHub account with access to this repository. Since it is private, ask the owner to invite you and accept that invitation first.

**Just want to listen?** If someone already runs Mookie in your server, you do not need to install anything. Join a voice channel and use `/play` in a text channel.

## Step 1: Download the files

1. Sign into GitHub and open [Mookie's repository](https://github.com/thizzclinton/MookieTheMusicPlaya).
2. Click the green **Code** button above the file list.
3. Click **Download ZIP**.
4. Open your Downloads folder.
5. On Mac, double-click the ZIP. On Windows, right-click it, choose **Extract All**, and click **Extract**.
6. Open the extracted folder. You should see `bot.py`, `README.md`, and `requirements.txt`. If you only see another folder, open that folder too.
7. Rename the folder containing those files to **Mookie**.
8. Move that folder into your personal home folder. On Mac, open Finder and press **Shift + Command + H** to get there. On Windows, press **Windows + R**, type `%USERPROFILE%`, and press Enter to open it.

Use a local folder rather than iCloud or OneDrive. The rest of this guide assumes the folder is named `Mookie` and is directly inside your home folder.

## Step 2: Open the command window

This is where you paste the commands below. A command is just an instruction for your computer.

**Mac:** Press **Command + Space**, type `Terminal`, and press Enter.

**Windows:** Open Start, type `PowerShell`, and open **Windows PowerShell**.

For each command: copy it, paste it into that window, and press Enter. Do not copy the surrounding box or any text outside it. Wait until your normal typing prompt returns before entering the next command. Some commands show lots of text; that is normal. If you see an error, stop at that step and check the help section below.

## Step 3: Install the tools Mookie needs

### If you use a Mac

First check whether Homebrew is installed. Homebrew downloads the tools for you.

```sh
brew --version
```

If you see a version number, continue below. If you see `command not found`, open [brew.sh](https://brew.sh), copy the command under **Install Homebrew**, and paste it into Terminal. Follow its prompts. If asked for your Mac password, type it and press Enter; no dots or letters will appear while you type. At the end, follow the installer's **Next steps** instructions, then run `brew --version` again.

Now install the tools:

```sh
brew install python ffmpeg deno
```

Wait for the normal prompt to return. This can take several minutes. Then run these checks, one at a time:

```sh
python3 --version
```

```sh
ffmpeg -version
```

```sh
deno --version
```

Each should print version information. Python needs to be 3.11 or newer and Deno needs to be 2.3 or newer. FFmpeg handles audio; Deno helps Mookie play YouTube tracks. These requirements follow the [yt-dlp setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS).

### If you use Windows

1. Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/windows/). If the installer offers **Add Python to PATH**, check it.
2. Install FFmpeg using the Windows builds linked from [FFmpeg's download page](https://ffmpeg.org/download.html). Extract the downloaded archive. Open its `bin` folder; this is the folder containing `ffmpeg.exe`.
3. Copy that folder's full address from File Explorer's address bar. Open Start, search **Edit environment variables for your account**, and open it. Under your user variables, select **Path → Edit → New**. Paste the folder address and click **OK** on each window. This lets Mookie find FFmpeg.
4. Install Deno by following the **Windows** instructions on [Deno's installation page](https://docs.deno.com/runtime/getting_started/installation/).
5. Close PowerShell and open it again so it sees the installed tools.
6. Run these checks one at a time:

```powershell
py -3 --version
```

```powershell
ffmpeg -version
```

```powershell
deno --version
```

Each should print version information. If one is not recognized, finish installing that tool before continuing. Python must be 3.11 or newer; Deno must be 2.3 or newer.

## Step 4: Set up Mookie's folder

Choose the commands for your computer. Paste **one line at a time** and wait for it to finish.

### Mac

```sh
cd ~/Mookie
```

Check the folder:

```sh
ls
```

You should see `bot.py` and `requirements.txt`. If you do, continue:

```sh
python3 -m venv .venv
```

```sh
.venv/bin/python -m pip install --upgrade pip
```

```sh
.venv/bin/python -m pip install -r requirements.txt
```

```sh
cp .env.example .env
```

### Windows

```powershell
cd "$env:USERPROFILE\Mookie"
```

Check the folder:

```powershell
dir
```

You should see `bot.py` and `requirements.txt`. If you do, continue:

```powershell
py -3 -m venv .venv
```

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
```

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```powershell
Copy-Item .env.example .env
```

This creates Mookie's own Python tools and a settings file. You only do this step once. **Do not repeat the last copy command after adding your token**; it would replace your settings.

## Step 5: Create your bot in Discord

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and sign in with Discord.
2. Click **New Application**, name it `Mookie`, and complete the creation prompts.
3. Click **Bot** in the left menu.
4. Find the token section and click **Reset Token** or the available token-generation button. Complete Discord's verification if asked.
5. Copy the token. It is a secret password for your bot. You will paste it into your local settings file in the next step. Do not send it to anyone or include it in screenshots.
6. Leave the **Privileged Gateway Intents** switches off.

Now invite the bot:

1. Click **OAuth2**, then find **URL Generator**.
2. Under **Scopes**, check **bot** and **applications.commands**.
3. Under **Bot Permissions**, check **View Channels**, **Send Messages**, **Read Message History**, **Connect**, and **Speak**.
4. Copy the generated link and open it in your browser.
5. Choose your server and finish the authorization prompts.

Mookie should appear in the server's member list. It can be offline for now; you haven't started it yet. If your server isn't listed, ask someone with permission to manage that server to install the bot.

If Discord moves a button, its [official bot guide](https://docs.discord.com/developers/quick-start/getting-started) has more setup help.

## Step 6: Add the bot's secret token

Go back to your command window. Open the settings file with the command for your computer.

Mac:

```sh
open -e .env
```

Windows:

```powershell
notepad .env
```

Find this line:

```dotenv
DISCORD_TOKEN=paste_your_bot_token_here
```

Replace **only** `paste_your_bot_token_here` with the token you copied from Discord. Keep `DISCORD_TOKEN=` at the beginning. Do not add quotation marks or spaces.

Save with **Command + S** on Mac or **Ctrl + S** on Windows, then close the editor. Leave the other settings alone for now. Fish Audio settings are optional and aren't needed for music.

If you accidentally share your token, reset it in Discord and replace it here.

## Step 7: Turn Mookie on

Mac:

```sh
caffeinate -i .venv/bin/python bot.py
```

Windows:

```powershell
.\.venv\Scripts\python.exe bot.py
```

Wait for a message like:

```text
Logged in as Mookie... Commands are ready.
```

Mookie should now appear online in Discord. **Leave this window open.** It will not return to the typing prompt while the bot is running; that is expected. On Mac, `caffeinate` prevents idle sleep while this command runs. On Windows, make sure your computer's sleep settings allow it to stay awake while you use Mookie.

## Step 8: Play your first song

1. Open Discord and join a normal voice channel, such as General.
2. Open a text channel in the same server.
3. Type `/play` and choose Mookie's command from Discord's suggestions.
4. Choose the **file** option and upload a small MP3, then send the command.
5. Mookie should join your voice channel and play it.

To search instead, choose the **query** option and type a song and artist, or paste a YouTube link. Choose either **file** or **query** for each request.

Try these controls in a text channel:

| Type this | What it does |
| --- | --- |
| `/queue` | Shows the current song and waiting songs |
| `/pause` | Pauses the song |
| `/resume` | Continues playing |
| `/skip` | Moves to the next song |
| `/stop` | Clears the music queue and leaves the voice channel |

You can also right-click a message with an uploaded song and choose **Apps → Play attachment**. Anyone in Mookie's voice channel can use the playback controls.

## Turning it off and starting it next time

To shut the bot down, click its command window and press **Ctrl + C**. `/stop` only disconnects it from voice; Ctrl+C shuts the program down.

Next time, open Terminal or PowerShell and run these two commands:

Mac:

```sh
cd ~/Mookie
caffeinate -i .venv/bin/python bot.py
```

Windows:

```powershell
cd "$env:USERPROFILE\Mookie"
.\.venv\Scripts\python.exe bot.py
```

You do not need to install everything again. Run only one copy of the bot at a time.

## Stuck? Start here

| What you see | What to do |
| --- | --- |
| GitHub says 404 or you can't see the files | Sign into the invited GitHub account and accept the owner's repository invitation. |
| `No such file or directory` or `can't open file` | Your command window is in the wrong folder. Repeat the `cd` command in Step 4 and check that `bot.py` appears with `ls` or `dir`. |
| `command not found` or `not recognized` | A tool isn't installed or your command window can't find it. Return to Step 3 and repeat the version check for that tool. |
| `No module named ...` | Repeat the requirements installation command in Step 4, then use the exact start command in Step 7. |
| Message asks for a token | Check that `.env` was saved inside Mookie's folder and that you replaced the placeholder. |
| Token/login error | Reset the bot token in Discord, update `.env`, save, and restart. |
| Bot is online but `/play` doesn't appear | Reopen Discord and wait for global commands to appear. Check that you invited it with both scopes in Step 5. |
| Bot can't join or you hear nothing | Check its Connect and Speak permissions for that specific voice channel, make sure it isn't muted, and test a small MP3. |
| An online song fails | Test an uploaded MP3 first. A music website may block access even when Mookie is installed correctly. |

For quicker command registration: in Discord, open **User Settings → Advanced**, enable **Developer Mode**, right-click your server icon, and choose **Copy Server ID**. Stop Mookie, open `.env`, paste that number after `DISCORD_GUILD_ID=`, save, and restart.

If you're still stuck, tell the owner **which step you reached** and send the error text. Do not send your `.env` file, bot token, or API keys.

## A few things to know

- Mookie is a Discord bot, not a separate music-player window on your computer.
- Closing its command window or shutting down the computer takes it offline.
- Spotify and Apple Music subscription streaming aren't supported.
- Searches play the first YouTube match. Paste a specific link when you want a particular version.
- Song queues disappear when the bot restarts.
- This guide has not been verified on a fresh installation of every operating system.

For optional voice tags, Linux setup, developer tests, and more details, see [the extra guide](docs/TECHNICAL.md).
