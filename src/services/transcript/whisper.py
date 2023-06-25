import io
import json

from pytube import YouTube

from src.schemas import TranscriptEntry
from .transcript_provider_abc import TranscriptProvider


class WhisperTranscriptProvider(TranscriptProvider):
    """Получает расшифровку используя модель Whisper"""

    async def get_transcript(self) -> list[TranscriptEntry]:
        buffer = self._get_audio_buffer()
        whisper_response = await self._whisper_request(buffer.read())
        return [TranscriptEntry(
            segment['text'],
            segment['start'],
            segment['end'] - segment['start'],
        ) for segment in whisper_response['segments']]

    def _get_audio_buffer(self) -> io.BytesIO:
        buffer = io.BytesIO()
        if stream := YouTube(self.url).streams.filter(
            only_audio=True
        ).filter(file_extension="mp4").first():
            stream.stream_to_buffer(buffer)
            buffer.seek(0)
            return buffer

        raise ValueError(f'Video {self.url} has no audio stream')

    async def _whisper_request(self, buffer: bytes):
        async with self.session.post(
            'http://whisper:9000/asr?encode=true&output=json',
            data={'audio_file': buffer},
        ) as response:
            resp = await response.text()
        return json.loads(resp)
