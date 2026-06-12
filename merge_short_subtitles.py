from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import srt


@dataclass
class MergeStats:
    original_count: int
    merged_count: int
    short_count: int


def readable_length(text: str) -> int:
    # Count meaningful visible text only; ignore punctuation and whitespace.
    return len(re.findall(r"[\w\u4e00-\u9fff\u3040-\u30ff]", text, flags=re.UNICODE))


def normalize_text(*parts: str) -> str:
    cleaned = [part.strip() for part in parts if part.strip()]
    return "\n".join(cleaned)


def can_merge(
    current: srt.Subtitle,
    next_subtitle: srt.Subtitle,
    min_chars: int,
    max_gap: timedelta,
    max_duration: timedelta,
) -> bool:
    gap = next_subtitle.start - current.end
    merged_duration = next_subtitle.end - current.start

    current_is_short = readable_length(current.content) <= min_chars
    next_is_short = readable_length(next_subtitle.content) <= min_chars

    return (
        (current_is_short or next_is_short)
        and timedelta(0) <= gap <= max_gap
        and merged_duration <= max_duration
    )


def merge_short_subtitles(
    subtitles: list[srt.Subtitle],
    min_chars: int,
    max_gap_ms: int,
    max_duration_ms: int,
) -> tuple[list[srt.Subtitle], MergeStats]:
    if not subtitles:
        return [], MergeStats(original_count=0, merged_count=0, short_count=0)

    max_gap = timedelta(milliseconds=max_gap_ms)
    max_duration = timedelta(milliseconds=max_duration_ms)
    short_count = sum(1 for subtitle in subtitles if readable_length(subtitle.content) <= min_chars)

    merged: list[srt.Subtitle] = []
    current = subtitles[0]

    for next_subtitle in subtitles[1:]:
        if can_merge(current, next_subtitle, min_chars, max_gap, max_duration):
            current = srt.Subtitle(
                index=current.index,
                start=current.start,
                end=next_subtitle.end,
                content=normalize_text(current.content, next_subtitle.content),
            )
        else:
            merged.append(current)
            current = next_subtitle

    merged.append(current)

    reindexed = [
        srt.Subtitle(index=index, start=subtitle.start, end=subtitle.end, content=subtitle.content)
        for index, subtitle in enumerate(merged, start=1)
    ]

    return reindexed, MergeStats(
        original_count=len(subtitles),
        merged_count=len(reindexed),
        short_count=short_count,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge very short adjacent subtitle cues.")
    parser.add_argument("input", help="Input .srt file.")
    parser.add_argument(
        "--output",
        default=None,
        help="Output .srt file. Defaults to `<input>.merged.srt`.",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=3,
        help="Merge cues with this many visible characters or fewer. Default: 3.",
    )
    parser.add_argument(
        "--max-gap-ms",
        type=int,
        default=1200,
        help="Only merge adjacent cues when the gap is at most this many ms. Default: 1200.",
    )
    parser.add_argument(
        "--max-duration-ms",
        type=int,
        default=7000,
        help="Do not create merged cues longer than this many ms. Default: 7000.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        print(f"Input file not found: {input_path}")
        return 1

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else input_path.with_name(f"{input_path.stem}.merged{input_path.suffix}")
    )

    subtitles = list(srt.parse(input_path.read_text(encoding="utf-8")))
    merged, stats = merge_short_subtitles(
        subtitles=subtitles,
        min_chars=args.min_chars,
        max_gap_ms=args.max_gap_ms,
        max_duration_ms=args.max_duration_ms,
    )

    output_path.write_text(srt.compose(merged), encoding="utf-8")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"Original cues: {stats.original_count}")
    print(f"Short cues found: {stats.short_count}")
    print(f"Merged cues: {stats.merged_count}")
    print(f"Removed cue breaks: {stats.original_count - stats.merged_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
