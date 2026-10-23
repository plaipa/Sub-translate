import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subtitles
from translators import _parse_array, translate_all

SRT = "1\n00:00:01,000 --> 00:00:02,000\nHello\nworld\n\n2\n00:00:03,000 --> 00:00:04,000\n{\\an8}<i>Bye</i>\n"
VTT = "WEBVTT\n\nNOTE hi\n\n00:01.000 --> 00:02.000\nHello\n"


class Fake:
    async def translate_batch(self, texts, target):
        return [t.upper() for t in texts]


def run(content):
    blocks = subtitles.parse(content)
    out = asyncio.run(translate_all(Fake(), subtitles.cue_texts(blocks), "fa", batch_size=1))
    return subtitles.render(blocks, out)


def test_srt_roundtrip_keeps_timing_and_tags():
    out = run(SRT)
    assert "00:00:01,000 --> 00:00:02,000\nHELLO\nWORLD" in out
    assert "{\\an8}<I>BYE</I>" in out


def test_vtt_header_preserved():
    out = run(VTT)
    assert out.startswith("WEBVTT\n\nNOTE hi\n\n00:01.000 --> 00:02.000\nHELLO")


def test_decode_cp1256():
    assert subtitles.decode("سلام".encode("cp1256")) == "سلام"


def test_parse_array_tolerates_wrapping():
    assert _parse_array('Here:\n```json\n["a","b"]\n```') == ["a", "b"]
