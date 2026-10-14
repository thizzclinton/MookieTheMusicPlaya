import os
import unittest
from unittest.mock import patch, MagicMock
import fish_tts

class FishTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_and_oversize_rejected(self):
        for text in [' ', 'x' * 501]:
            with self.assertRaises(ValueError):
                await fish_tts.synthesize(text)

    async def test_missing_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'FISH_API_KEY'):
                await fish_tts.synthesize('hello')

    async def test_response_and_auth_errors(self):
        for status in [200, 401, 402, 429]:
            response = MagicMock()
            response.status = status
            async def chunks(size):
                yield b'ID3test'
            response.content.iter_chunked = chunks
            session = MagicMock()
            session.post.return_value.__aenter__.return_value = response
            with patch.dict(os.environ, {'FISH_API_KEY': 'secret', 'FISH_VOICE_ID': 'voice'}, clear=True), patch.object(fish_tts.aiohttp, 'ClientSession') as factory:
                factory.return_value.__aenter__.return_value = session
                if status == 200:
                    self.assertEqual(await fish_tts.synthesize('hello'), b'ID3test')
                    self.assertEqual(session.post.call_args.kwargs['json']['reference_id'], 'voice')
                else:
                    with self.assertRaises(ValueError) as error:
                        await fish_tts.synthesize('hello')
                    self.assertNotIn('secret', str(error.exception))

class TagDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_tag_sends_file_and_closes_it(self):
        import bot
        from types import SimpleNamespace
        from unittest.mock import AsyncMock
        for fails in (False, True):
            sent = []
            async def send(*args, **kwargs):
                clip = kwargs['file']
                sent.append(clip)
                self.assertEqual(clip.fp.read(), b'ID3test')
                self.assertEqual(clip.filename, 'mookie-tag.mp3')
                self.assertTrue(kwargs['ephemeral'])
                if fails:
                    raise RuntimeError('delivery failed')
            interaction = SimpleNamespace(response=SimpleNamespace(defer=AsyncMock()),
                followup=SimpleNamespace(send=send))
            with patch.object(bot.fish_tts, 'synthesize', new=AsyncMock(return_value=b'ID3test')):
                if fails:
                    with self.assertRaises(RuntimeError):
                        await bot.tag.callback(interaction, 'test')
                else:
                    await bot.tag.callback(interaction, 'test')
            self.assertTrue(sent[0].fp.closed)
