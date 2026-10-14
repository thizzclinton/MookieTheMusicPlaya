"""Bounded Fish Audio requests; never expose provider bodies or credentials."""
import asyncio
import os
import aiohttp

MAX_TEXT = 500
MAX_AUDIO = 8 * 1024 * 1024

async def synthesize(text):
    text = text.strip()
    if not text or len(text) > MAX_TEXT:
        raise ValueError('Enter between 1 and 500 characters.')
    key = os.getenv('FISH_API_KEY', '').strip()
    voice = os.getenv('FISH_VOICE_ID', '').strip()
    if not key or not voice:
        raise ValueError('Set FISH_API_KEY and FISH_VOICE_ID in the bot .env, then restart.')
    model = os.getenv('FISH_TTS_MODEL', 's2.1-pro-free').strip()
    if model not in {'s1', 's2-pro', 's2.1-pro', 's2.1-pro-free', 'drama-3-preview'}:
        raise ValueError('FISH_TTS_MODEL is not a supported model.')
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(
                'https://api.fish.audio/v1/tts',
                headers={'Authorization': f'Bearer {key}', 'model': model},
                json={'text': text, 'reference_id': voice, 'format': 'mp3'},
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    messages = {401: 'Fish Audio rejected the API key.',
                                402: 'Check your Fish Audio credit or plan.',
                                403: 'Fish Audio denied access to this voice or model.',
                                429: 'Fish Audio is rate limiting requests. Try again later.'}
                    raise ValueError(messages.get(response.status,
                        f'Fish Audio could not generate the clip (HTTP {response.status}). Check the voice ID and model.'))
                audio = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    audio.extend(chunk)
                    if len(audio) > MAX_AUDIO:
                        raise ValueError('The generated clip is too large. Try shorter text.')
                if not audio:
                    raise ValueError('Fish Audio returned an empty clip. Try again.')
                if not (audio.startswith(b'ID3') or (len(audio) > 1 and audio[0] == 255 and audio[1] & 224 == 224)):
                    raise ValueError('Fish Audio did not return a valid MP3 clip.')
                return bytes(audio)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        raise ValueError('Fish Audio could not be reached or timed out. Try again later.') from None
