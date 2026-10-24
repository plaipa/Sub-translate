"""Minimal SRT / WebVTT parser that keeps timing and structure intact."""
from __future__ import annotations

import re
from dataclasses import dataclass

ENCODINGS = ("utf-8-sig", "cp1256", "cp1252")
LEADING_TAGS = re.compile(r"^(?:\{[^}]*\})+")


@dataclass
class Block:
    """A subtitle block. `head` is everything before the text (id + timing line)."""
    head: list[str]
    text: list[str]
    is_cue: bool


def decode(data: bytes) -> str:
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    for enc in ENCODINGS:
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def parse(content: str) -> list[Block]:
    blocks: list[Block] = []
    for raw in re.split(r"\n{2,}", content.replace("\r\n", "\n").replace("\r", "\n").strip("\n")):
        lines = raw.split("\n")
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            blocks.append(Block(lines, [], False))  # WEBVTT header, NOTE, STYLE...
        else:
            blocks.append(Block(lines[: idx + 1], lines[idx + 1 :], True))
    return blocks


def cue_texts(blocks: list[Block]) -> list[str]:
    return ["\n".join(b.text) for b in blocks if b.is_cue]


def render(blocks: list[Block], translations: list[str]) -> str:
    it = iter(translations)
    out = []
    for b in blocks:
        text = next(it).split("\n") if b.is_cue else b.text
        out.append("\n".join(b.head + text))
    return "\n\n".join(out) + "\n"


def split_leading_tags(text: str) -> tuple[str, str]:
    """Separate ASS-style prefixes like {\\an8} so translators never see them."""
    m = LEADING_TAGS.match(text)
    return (m.group(0), text[m.end():]) if m else ("", text)


TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})([.,])(\d{3})")


def _ms(m: re.Match) -> int:
    h, mi, s, ms = int(m.group(1) or 0), int(m.group(2)), int(m.group(3)), int(m.group(5))
    return ((h * 60 + mi) * 60 + s) * 1000 + ms


def _fmt(ms: int, sep: str, hours: bool) -> str:
    h, rem = divmod(ms, 3_600_000)
    mi, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{mi:02d}:{s:02d}{sep}{ms:03d}" if hours or h else f"{mi:02d}:{s:02d}{sep}{ms:03d}"


def add_credit(blocks: list[Block], translations: list[str], text: str,
               lead_room: int = 3000, tail: int = 4000) -> tuple[list[Block], list[str]]:
    """Add a credit cue at the start (only if the first line begins late enough that it can't
    overlap) and one after the last line. SRT numbering is rewritten to stay consecutive."""
    cues = [b for b in blocks if b.is_cue]
    if not cues:
        return blocks, translations
    first = list(TIME.finditer(cues[0].head[-1]))
    last = list(TIME.finditer(cues[-1].head[-1]))
    if len(first) < 2 or len(last) < 2:
        return blocks, translations
    sep, hours = first[0].group(4), first[0].group(1) is not None
    srt = len(cues[0].head) == 2 and cues[0].head[0].strip().isdigit()

    def credit(start: int, end: int) -> Block:
        timing = f"{_fmt(start, sep, hours)} --> {_fmt(end, sep, hours)}"
        return Block([""] + [timing] if srt else [timing], [text], True)

    new_blocks, new_tr = list(blocks), list(translations)
    first_start = _ms(first[0])
    if first_start >= lead_room:
        at = next(i for i, b in enumerate(new_blocks) if b.is_cue)  # after WEBVTT header / NOTEs
        new_blocks.insert(at, credit(500, lead_room - 200))
        new_tr.insert(0, text)  # translations only cover cues, so the credit is first there
    new_blocks.append(credit(_ms(last[1]) + 500, _ms(last[1]) + 500 + tail))
    new_tr.append(text)
    if srt:
        for n, b in enumerate((b for b in new_blocks if b.is_cue), 1):
            b.head[0] = str(n)
    return new_blocks, new_tr


_LANG_TAGS = {"en", "eng", "english", "fa", "fas", "per", "persian", "ar", "tr", "ru", "de", "fr",
              "es", "it", "pt", "ja", "ko", "hi", "ur", "az", "zh", "chi", "chs", "cht"}


def translated_filename(original: str, target: str, bot_username: str) -> str:
    """Movie.2020.en.srt -> Movie.2020.fa.@bot_username.srt"""
    stem, dot, ext = original.rpartition(".")
    if not dot:
        stem, ext = original, "srt"
    head, _, tag = stem.rpartition(".")
    if head and tag.lower() in _LANG_TAGS:  # drop the old language tag
        stem = head
    return f"{stem}.{target}.@{bot_username}.{ext}"
