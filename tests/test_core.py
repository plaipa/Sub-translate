import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subtitles
from translators import LLMTranslator, _parse_array, translate_all

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


class Bad(LLMTranslator):
    """Misaligned output for batches > 1 forces the split-and-retry path."""
    async def _complete(self, system, user):
        import json
        items = json.loads(user)
        return json.dumps(items if len(items) == 1 else items[:-1])


def test_llm_split_fallback_keeps_alignment():
    out = asyncio.run(Bad().translate_batch(["a", "b", "c"], "fa"))
    assert out == ["a", "b", "c"]


def test_i18n_all_languages_complete():
    from i18n import COMMANDS, S, UI_LANGUAGES, text
    assert set(S) == set(UI_LANGUAGES)
    en_keys = set(S["en"])
    for code, strings in S.items():
        assert set(strings) == en_keys, code
        assert all(f"cmd_{c}" in strings for c in COMMANDS)
        text(code, "progress", lang="x", done=1, total=2)  # placeholders format cleanly
    assert text("xx", "done") == S["en"]["done"]  # unknown language falls back to English


def test_profile_texts_fit_telegram_limits_and_mention_support():
    from i18n import DESCRIPTION, SHORT_DESCRIPTION, SUPPORT
    assert len(DESCRIPTION) <= 512 and len(SHORT_DESCRIPTION) <= 120
    assert SUPPORT in DESCRIPTION and SUPPORT in SHORT_DESCRIPTION
