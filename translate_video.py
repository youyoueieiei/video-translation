from __future__ import annotations

import argparse
import csv
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Iterable

import requests
import srt
from bs4 import BeautifulSoup
from faster_whisper import WhisperModel


@dataclass(frozen=True)
class SubtitleLine:
    index: int
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class GlossaryEntry:
    source: str
    target: str
    mode: str


def run_command(command: list[str], cwd: Path | None = None) -> None:
    try:
        subprocess.run(command, check=True, cwd=str(cwd) if cwd else None)
    except FileNotFoundError as exc:
        executable = command[0]
        raise RuntimeError(
            f"Could not find `{executable}`. Please install it and make sure it is on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Command failed with exit code {exc.returncode}: {' '.join(command)}") from exc


def extract_audio(video_path: Path, audio_path: Path) -> None:
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(audio_path),
        ]
    )


def transcribe_audio(
    audio_path: Path,
    source_language: str,
    model_size: str,
    device: str,
    compute_type: str,
    vad_filter: bool,
) -> list[SubtitleLine]:
    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    segments, _ = model.transcribe(
        str(audio_path),
        language=source_language,
        vad_filter=vad_filter,
        beam_size=5,
    )

    lines: list[SubtitleLine] = []
    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        if text:
            lines.append(SubtitleLine(index=index, start=segment.start, end=segment.end, text=text))
    return lines


def to_srt(lines: Iterable[SubtitleLine]) -> str:
    subtitles = [
        srt.Subtitle(
            index=line.index,
            start=timedelta(seconds=line.start),
            end=timedelta(seconds=line.end),
            content=line.text,
        )
        for line in lines
    ]
    return srt.compose(subtitles)


def from_srt(content: str) -> list[SubtitleLine]:
    lines: list[SubtitleLine] = []
    for subtitle in srt.parse(content):
        lines.append(
            SubtitleLine(
                index=subtitle.index,
                start=subtitle.start.total_seconds(),
                end=subtitle.end.total_seconds(),
                text=subtitle.content.strip(),
            )
        )
    return lines


def load_glossary(glossary_path: Path | None) -> list[GlossaryEntry]:
    if not glossary_path:
        return []
    if not glossary_path.exists():
        raise RuntimeError(f"Glossary file not found: {glossary_path}")

    entries: list[GlossaryEntry] = []
    with glossary_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required_columns = {"source", "target", "mode"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise RuntimeError(
                f"Glossary is missing required columns: {', '.join(sorted(missing_columns))}"
            )

        for row_number, row in enumerate(reader, start=2):
            source = (row.get("source") or "").strip()
            target = (row.get("target") or "").strip()
            mode = (row.get("mode") or "").strip().lower()

            if not source:
                continue
            if mode not in {"protect", "replace"}:
                raise RuntimeError(
                    f"Glossary row {row_number} has invalid mode `{mode}`. Use `protect` or `replace`."
                )

            entries.append(
                GlossaryEntry(
                    source=source,
                    target=target or source,
                    mode=mode,
                )
            )

    return sorted(entries, key=lambda entry: len(entry.source), reverse=True)


def apply_glossary_placeholders(
    text: str,
    glossary_entries: list[GlossaryEntry],
) -> tuple[str, dict[str, str]]:
    protected_text = text
    replacements: dict[str, str] = {}

    for index, entry in enumerate(glossary_entries):
        if entry.source not in protected_text:
            continue

        placeholder = f"ZXQGLOSSARY{index}QXZ"
        protected_text = protected_text.replace(entry.source, placeholder)
        replacements[placeholder] = entry.target if entry.mode == "replace" else entry.source

    return protected_text, replacements


def restore_glossary_placeholders(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for placeholder, replacement in replacements.items():
        restored = restored.replace(placeholder, replacement)
        restored = restored.replace(placeholder.lower(), replacement)
        restored = restored.replace(placeholder.title(), replacement)
    return restored


def translate_text(text: str, source_language: str, target_language: str, timeout: int, retries: int) -> str:
    if not text.strip():
        return text

    last_error: Exception | None = None
    for _ in range(retries + 1):
        try:
            response = requests.get(
                "https://translate.google.com/m",
                params={"sl": source_language, "tl": target_language, "q": text},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=timeout,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            element = soup.find("div", class_="result-container")
            if element:
                return element.get_text(strip=True)
            raise RuntimeError("translation response did not include result text")
        except Exception as exc:
            last_error = exc

    raise RuntimeError(str(last_error) if last_error else "translation failed")


def parse_numbered_translation_block(translated_block: str, expected_count: int) -> list[str] | None:
    parsed: list[str] = []

    for raw_line in translated_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = re.match(r"^\s*(\d+)\s*[\.\):：、-]?\s*(.*)$", line)
        if not match:
            continue

        index = int(match.group(1))
        if index != len(parsed) + 1:
            return None

        parsed.append(match.group(2).strip())

    if len(parsed) != expected_count:
        return None
    if any(not item for item in parsed):
        return None

    return parsed


def build_context_block(lines: list[str]) -> str:
    return "\n".join(f"{index}. {text}" for index, text in enumerate(lines, start=1))


def translate_context_batch(
    lines: list[str],
    source_language: str,
    target_language: str,
    timeout: int,
    retries: int,
) -> list[str] | None:
    translated_block = translate_text(
        build_context_block(lines),
        source_language=source_language,
        target_language=target_language,
        timeout=timeout,
        retries=retries,
    )
    return parse_numbered_translation_block(translated_block, expected_count=len(lines))


def translate_subtitles(
    lines: list[SubtitleLine],
    source_language: str,
    target_language: str,
    timeout: int,
    retries: int,
    glossary_entries: list[GlossaryEntry],
    translation_mode: str,
    context_size: int,
) -> list[SubtitleLine]:
    if translation_mode == "context":
        return translate_subtitles_with_context(
            lines=lines,
            source_language=source_language,
            target_language=target_language,
            timeout=timeout,
            retries=retries,
            glossary_entries=glossary_entries,
            context_size=context_size,
        )

    translated: list[SubtitleLine] = []

    for position, line in enumerate(lines, start=1):
        text_to_translate, glossary_replacements = apply_glossary_placeholders(
            line.text,
            glossary_entries,
        )
        try:
            translated_text = translate_text(
                text_to_translate,
                source_language=source_language,
                target_language=target_language,
                timeout=timeout,
                retries=retries,
            )
        except Exception as exc:
            print(
                f"Warning: translation failed for subtitle {line.index}; keeping original text. ({exc})",
                file=sys.stderr,
                flush=True,
            )
            translated_text = line.text

        translated_text = restore_glossary_placeholders(translated_text, glossary_replacements)

        if position == 1 or position % 10 == 0 or position == len(lines):
            print(f"Translated {position}/{len(lines)} subtitle lines...", flush=True)

        translated.append(
            SubtitleLine(
                index=line.index,
                start=line.start,
                end=line.end,
                text=translated_text.strip() if translated_text else line.text,
            )
        )

    return translated


def translate_subtitles_with_context(
    lines: list[SubtitleLine],
    source_language: str,
    target_language: str,
    timeout: int,
    retries: int,
    glossary_entries: list[GlossaryEntry],
    context_size: int,
) -> list[SubtitleLine]:
    translated: list[SubtitleLine] = []
    safe_context_size = max(2, context_size)

    for batch_start in range(0, len(lines), safe_context_size):
        batch = lines[batch_start : batch_start + safe_context_size]
        protected_lines: list[str] = []
        batch_replacements: list[dict[str, str]] = []

        for line in batch:
            protected_text, glossary_replacements = apply_glossary_placeholders(
                line.text,
                glossary_entries,
            )
            protected_lines.append(protected_text)
            batch_replacements.append(glossary_replacements)

        translated_texts: list[str] | None = None
        try:
            translated_texts = translate_context_batch(
                protected_lines,
                source_language=source_language,
                target_language=target_language,
                timeout=timeout,
                retries=retries,
            )
        except Exception as exc:
            print(
                f"Warning: context translation failed for lines {batch[0].index}-{batch[-1].index}; "
                f"falling back to line-by-line. ({exc})",
                file=sys.stderr,
                flush=True,
            )

        if translated_texts is None:
            translated_texts = []
            for protected_text, source_line in zip(protected_lines, batch):
                try:
                    translated_texts.append(
                        translate_text(
                            protected_text,
                            source_language=source_language,
                            target_language=target_language,
                            timeout=timeout,
                            retries=retries,
                        )
                    )
                except Exception as exc:
                    print(
                        f"Warning: translation failed for subtitle {source_line.index}; "
                        f"keeping original text. ({exc})",
                        file=sys.stderr,
                        flush=True,
                    )
                    translated_texts.append(source_line.text)

        for source_line, translated_text, replacements in zip(batch, translated_texts, batch_replacements):
            translated_text = restore_glossary_placeholders(translated_text, replacements)
            translated.append(
                SubtitleLine(
                    index=source_line.index,
                    start=source_line.start,
                    end=source_line.end,
                    text=translated_text.strip() if translated_text else source_line.text,
                )
            )

        print(f"Translated {len(translated)}/{len(lines)} subtitle lines...", flush=True)

    return translated


def burn_subtitles(video_path: Path, subtitle_path: Path, output_video_path: Path) -> None:
    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_working_dir = Path(__file__).resolve().parent
    ffmpeg_subtitle_path = ffmpeg_working_dir / "_subtitle_for_burn.srt"
    ffmpeg_subtitle_path.write_text(subtitle_path.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        run_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"subtitles=filename={ffmpeg_subtitle_path.name}",
                "-c:a",
                "copy",
                str(output_video_path),
            ],
            cwd=ffmpeg_working_dir,
        )
    finally:
        try:
            os.remove(ffmpeg_subtitle_path)
        except FileNotFoundError:
            pass


def safe_language_code(language_code: str) -> str:
    return "".join(character if character.isalnum() or character in ("-", "_") else "_" for character in language_code)


def build_output_paths(
    video_path: Path,
    output_dir: Path,
    source_language: str,
    target_language: str,
) -> tuple[Path, Path, Path, Path]:
    stem = video_path.stem
    source_code = safe_language_code(source_language)
    target_code = safe_language_code(target_language)
    audio_path = output_dir / f"{stem}.wav"
    source_srt_path = output_dir / f"{stem}.{source_code}.srt"
    translated_srt_path = output_dir / f"{stem}.{source_code}.{target_code}.srt"
    subtitled_video_path = output_dir / f"{stem}.{target_code}_subtitled.mp4"
    return audio_path, source_srt_path, translated_srt_path, subtitled_video_path


def parse_time_to_seconds(s: str | None) -> float:
    if not s:
        return 0.0
    s = str(s).strip()
    if s.isdigit():
        return float(s)
    parts = s.split(":")
    try:
        parts = [float(p) for p in parts]
    except Exception:
        raise RuntimeError(f"Invalid --translate-start time format: {s}")
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise RuntimeError(f"Invalid --translate-start time format: {s}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe MP4 audio and export translated subtitles as an SRT file."
    )
    parser.add_argument(
        "video",
        help="Path to the MP4 video.",
    )
    parser.add_argument(
        "--source-language",
        "--source",
        default="ja",
        help="Source spoken language code for Whisper and translation, e.g. ja, en, ko. Default: ja.",
    )
    parser.add_argument(
        "--target-language",
        "--target",
        default="zh-CN",
        help="Output translation language code, e.g. zh-CN, en, ja, ko. Default: zh-CN.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output folder. Defaults to an `output` folder next to the video.",
    )
    parser.add_argument(
        "--model-size",
        default="medium",
        help="Whisper model size: tiny, base, small, medium, large-v3. Default: medium.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Whisper device: cpu or cuda. Default: cpu.",
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="faster-whisper compute type. Use float16 for CUDA. Default: int8.",
    )
    parser.add_argument(
        "--burn",
        action="store_true",
        help="Also create a new MP4 with translated subtitles burned into the video.",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        help="Keep the extracted WAV file after processing.",
    )
    parser.add_argument(
        "--song-mode",
        action="store_true",
        help="Disable voice activity filtering. Useful for music videos, songs, and lyrics.",
    )
    parser.add_argument(
        "--force-transcribe",
        action="store_true",
        help="Regenerate source-language subtitles even if they already exist.",
    )
    parser.add_argument(
        "--force-translate",
        action="store_true",
        help="Regenerate translated subtitles even if they already exist.",
    )
    parser.add_argument(
        "--glossary",
        default=None,
        help="Optional CSV glossary with source,target,mode columns for protected names and terms.",
    )
    parser.add_argument(
        "--translation-mode",
        choices=["fast", "context"],
        default="fast",
        help="Translation mode. `fast` translates cue by cue; `context` translates small groups for better flow.",
    )
    parser.add_argument(
        "--context-size",
        type=int,
        default=6,
        help="Number of subtitle cues per context translation batch. Default: 6.",
    )
    parser.add_argument(
        "--translation-timeout",
        type=int,
        default=15,
        help="Seconds before one translation request times out. Default: 15.",
    )
    parser.add_argument(
        "--translation-retries",
        type=int,
        default=2,
        help="Retries per subtitle line after a translation failure. Default: 2.",
    )
    parser.add_argument(
        "--translate-start",
        default=None,
        help="Optional start time to begin translating (format: HH:MM:SS, MM:SS, or seconds). "
        "Lines that end before this time will be copied unchanged into the translated SRT.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video_path = Path(args.video).expanduser().resolve()
    if not video_path.exists():
        print(f"Video not found: {video_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else video_path.parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_language = args.source_language
    target_language = args.target_language
    glossary_path = Path(args.glossary).expanduser().resolve() if args.glossary else None
    audio_path, source_srt_path, translated_srt_path, subtitled_video_path = build_output_paths(
        video_path,
        output_dir,
        source_language=source_language,
        target_language=target_language,
    )

    try:
        glossary_entries = load_glossary(glossary_path)
        if glossary_entries:
            print(f"Loaded glossary entries: {len(glossary_entries)}")

        audio_was_extracted = False
        source_lines: list[SubtitleLine] = []
        if source_srt_path.exists() and not args.force_transcribe:
            print(f"1/4 Reusing source subtitles: {source_srt_path}")
            source_lines = from_srt(source_srt_path.read_text(encoding="utf-8"))

            if not source_lines:
                print("Existing source subtitle file is empty; regenerating transcription.")

        if not source_lines:
            print("1/4 Extracting audio...")
            extract_audio(video_path, audio_path)
            audio_was_extracted = True

            print(f"2/4 Transcribing source language ({source_language})...")
            source_lines = transcribe_audio(
                audio_path=audio_path,
                source_language=source_language,
                model_size=args.model_size,
                device=args.device,
                compute_type=args.compute_type,
                vad_filter=not args.song_mode,
            )
            if not source_lines:
                raise RuntimeError(
                    "No subtitle lines were detected. For music videos or songs, try enabling song mode."
                )
            source_srt_path.write_text(to_srt(source_lines), encoding="utf-8")
            print(f"Wrote source subtitles: {source_srt_path}")

        if translated_srt_path.exists() and not args.force_translate:
            print(f"3/4 Reusing translated subtitles: {translated_srt_path}")
        else:
            translate_start_seconds = parse_time_to_seconds(args.translate_start)
            print(f"3/4 Translating {source_language} to {target_language} (start at {translate_start_seconds}s)...")

            # Decide which lines to translate (those that end after translate_start_seconds)
            lines_to_translate = [l for l in source_lines if l.end > translate_start_seconds]

            if lines_to_translate:
                translated_subset = translate_subtitles(
                    lines_to_translate,
                    source_language=source_language,
                    target_language=target_language,
                    timeout=args.translation_timeout,
                    retries=args.translation_retries,
                    glossary_entries=glossary_entries,
                    translation_mode=args.translation_mode,
                    context_size=args.context_size,
                )
                # Map index -> translated text for replaced lines
                translated_map = {l.index: l.text for l in translated_subset}
            else:
                translated_map = {}

            # Build final translated list: if line ends <= start, keep source text unchanged
            translated_lines: list[SubtitleLine] = []
            for l in source_lines:
                text = translated_map.get(l.index, l.text)
                translated_lines.append(SubtitleLine(index=l.index, start=l.start, end=l.end, text=text))

            translated_srt_path.write_text(to_srt(translated_lines), encoding="utf-8")
            print(f"Wrote translated subtitles: {translated_srt_path}")

        if args.burn:
            if not translated_srt_path.exists() or not translated_srt_path.read_text(encoding="utf-8").strip():
                raise RuntimeError("Translated SRT is empty, so there are no subtitles to add to the video.")
            print("4/4 Burning translated subtitles into MP4...")
            burn_subtitles(video_path, translated_srt_path, subtitled_video_path)
            print(f"Wrote subtitled video: {subtitled_video_path}")
        else:
            print("4/4 Skipped MP4 subtitle burning. Use --burn to enable it.")

        if audio_was_extracted and not args.keep_audio:
            try:
                os.remove(audio_path)
            except FileNotFoundError:
                pass

    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
