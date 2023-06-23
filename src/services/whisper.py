import io
import json

from pytube import YouTube
from aiohttp import ClientSession

from src.schemas import TranscriptEntry


async def whisper_transcript(session: ClientSession, url: str) -> list[TranscriptEntry]:
    buffer = _get_audio_buffer(url)
    whisper_response = await _whisper_request(session, buffer.read())
    return [TranscriptEntry(
        segment['text'],
        segment['start'],
        segment['end'] - segment['start'],
    ) for segment in whisper_response['segments']]


def _get_audio_buffer(url: str) -> io.BytesIO:
    buffer = io.BytesIO()
    if stream := YouTube(url).streams.filter(only_audio=True).filter(file_extension="mp4").first():
        stream.stream_to_buffer(buffer)
        buffer.seek(0)
        return buffer

    raise ValueError(f'Video {url} has no audio stream')


async def _whisper_request(session: ClientSession, buffer: bytes):
    async with session.post(
        'http://whisper:9000/asr?task=translate&encode=true&output=json',
        data={'audio_file': buffer},
    ) as response:
        resp = await response.text()
    return json.loads(resp)
