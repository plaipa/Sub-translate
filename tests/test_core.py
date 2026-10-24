import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import subtitles
from translators import LLMTranslator, _parse_object, translate_all

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


def test_parse_object_tolerates_wrapping():
    assert _parse_object('Here:\n```json\n{"0": "a", "1": "b"}\n```') == {"0": "a", "1": "b"}


class Flaky(LLMTranslator):
    """Drops id "1" on the first call; a retry must only ask for the missing ids."""
    def __init__(self):
        self.calls = []

    async def _complete(self, system, user):
        import json
        items = json.loads(user)
        self.calls.append(sorted(items))
        out = {k: v.upper() for k, v in items.items()}
        if len(self.calls) == 1:
            out.pop("1")
        return json.dumps(out)


def test_llm_retries_only_missing_lines_and_keeps_alignment():
    tr = Flaky()
    assert asyncio.run(tr.translate_batch(["a", "b", "c"], "fa")) == ["A", "B", "C"]
    assert tr.calls == [["0", "1", "2"], ["1"]]


class Broken(LLMTranslator):
    async def _complete(self, system, user):
        return "sorry, I cannot do that"


def test_llm_gives_up_gracefully_with_original_text():
    assert asyncio.run(Broken().translate_batch(["a", "b"], "fa")) == ["a", "b"]


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


def test_daily_limit_resets_each_day(monkeypatch):
    import bot
    monkeypatch.setattr(bot, "DAILY_LIMIT", 2)
    ud = {}
    assert not bot.over_limit(ud)
    bot.quota(ud)["used"] = 2
    assert bot.over_limit(ud)
    ud["quota"]["day"] = "2000-01-01"  # yesterday's usage must not carry over
    assert not bot.over_limit(ud) and ud["quota"]["used"] == 0
    monkeypatch.setattr(bot, "DAILY_LIMIT", 0)  # 0 = unlimited
    ud["quota"]["used"] = 999
    assert not bot.over_limit(ud)


def test_gemini_falls_back_to_next_model_on_overload():
    import httpx
    from translators import GeminiTranslator

    def handler(request):
        if "bad-model" in str(request.url):
            return httpx.Response(503, json={"error": {"status": "UNAVAILABLE"}})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"0": "ok"}'}]}}]})

    async def go():
        tr = GeminiTranslator("k", ["bad-model", "good-model"])
        tr.http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        async def no_sleep(_): pass
        import translators; translators.asyncio.sleep = no_sleep
        out = await tr.translate_batch(["x"], "fa")
        assert "bad-model" in tr._cool  # overloaded model is skipped for a while
        return out
    assert asyncio.run(go()) == ["ok"]


def _credit(content, text="Translated by @bot"):
    blocks = subtitles.parse(content)
    tr = subtitles.cue_texts(blocks)
    b, t = subtitles.add_credit(blocks, tr, text)
    return subtitles.render(b, t)


def test_credit_goes_after_last_line_and_srt_stays_numbered():
    out = _credit(SRT)  # first line starts at 1s: no room for a credit at the start
    assert out.startswith("1\n00:00:01,000")
    assert out.rstrip().endswith("3\n00:00:04,500 --> 00:00:08,500\nTranslated by @bot")


def test_credit_also_at_start_when_there_is_room_and_numbers_are_rewritten():
    srt = "1\n00:00:10,000 --> 00:00:12,000\nHi\n\n2\n00:00:13,000 --> 00:00:14,000\nBye\n"
    out = _credit(srt)
    assert out.startswith("1\n00:00:00,500 --> 00:00:02,800\nTranslated by @bot\n\n2\n00:00:10,000")
    assert "\n\n3\n00:00:13,000" in out and "\n\n4\n00:00:14,500 --> 00:00:18,500\nTranslated" in out


def test_credit_vtt_keeps_header_and_time_style():
    vtt = "WEBVTT\n\n00:05.000 --> 00:06.000\nHello\n"
    out = _credit(vtt)
    assert out.startswith("WEBVTT\n\n00:00.500 --> 00:02.800\nTranslated by @bot")
    assert out.rstrip().endswith("00:06.500 --> 00:10.500\nTranslated by @bot")


def test_translated_filename():
    f = subtitles.translated_filename
    assert f("Movie.2020.1080p.srt", "fa", "my_bot") == "Movie.2020.1080p.fa.@my_bot.srt"
    assert f("Movie.2020.en.srt", "fa", "my_bot") == "Movie.2020.fa.@my_bot.srt"  # old tag dropped
    assert f("Inception.vtt", "zh-CN", "my_bot") == "Inception.zh-CN.@my_bot.vtt"
