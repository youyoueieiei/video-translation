#!/usr/bin/env python3
"""Burn SRT subtitles into a video and optionally compress (same resolution)."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import srt


VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v", ".ts"}
OUTPUT_FORMATS = ("mp4", "mkv")


@dataclass(frozen=True)
class BurnOptions:
    font_name: str = "Microsoft YaHei"
    font_size: int = 46
    margin_v: int = 18
    margin_lr: int = 40
    outline: float = 2.0
    one_line: bool = True
    crf: int = 24
    preset: str = "fast"
    audio_copy: bool = True
    output_format: str = "mp4"


def probe_video_size(video_path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "json",
        str(video_path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding="utf-8")
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])


def flatten_one_line(text: str) -> str:
    return "".join(text.replace("\n", " ").split())


def prepare_srt(source_srt: Path, dest_srt: Path, one_line: bool) -> None:
    subs = list(srt.parse(source_srt.read_text(encoding="utf-8")))
    if one_line:
        for sub in subs:
            sub.content = flatten_one_line(sub.content)
    dest_srt.write_text(srt.compose(subs), encoding="utf-8")


def write_ass(
    srt_path: Path,
    ass_path: Path,
    width: int,
    height: int,
    options: BurnOptions,
) -> None:
    subs = list(srt.parse(srt_path.read_text(encoding="utf-8")))

    def ass_time(td: timedelta) -> str:
        total = td.total_seconds()
        hours = int(total // 3600)
        minutes = int((total % 3600) // 60)
        seconds = total % 60
        return f"{hours}:{minutes:02d}:{seconds:05.2f}"

    style = (
        f"Style: Default,{options.font_name},{options.font_size},"
        f"&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        f"0,0,0,0,100,100,0,0,1,{options.outline},0,2,"
        f"{options.margin_lr},{options.margin_lr},{options.margin_v},1"
    )
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {width}",
        f"PlayResY: {height}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
        "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        style,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for sub in subs:
        text = sub.content.replace("\n", r"\N").replace("{", "(").replace("}", ")")
        lines.append(
            f"Dialogue: 0,{ass_time(sub.start)},{ass_time(sub.end)},Default,,0,0,0,,{text}"
        )
    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")


def link_or_copy(src: Path, dest: Path) -> None:
    if dest.exists():
        dest.unlink()
    try:
        dest.hardlink_to(src)
    except OSError:
        shutil.copy2(src, dest)


def burn_video(
    video_path: Path,
    subtitle_path: Path,
    output_path: Path,
    options: BurnOptions | None = None,
) -> Path:
    options = options or BurnOptions()
    if video_path.suffix.lower() not in VIDEO_SUFFIXES:
        raise RuntimeError(f"Unsupported video type: {video_path.suffix}")
    if subtitle_path.suffix.lower() not in {".srt", ".ass"}:
        raise RuntimeError("Subtitle must be .srt or .ass")
    if options.output_format not in OUTPUT_FORMATS:
        raise RuntimeError(f"Unsupported output format: {options.output_format}")

    output_path = output_path.with_suffix(f".{options.output_format}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = probe_video_size(video_path)

    with tempfile.TemporaryDirectory(prefix="burn_work_") as tmp:
        work = Path(tmp)
        simple_video = work / f"input{video_path.suffix.lower()}"
        simple_srt = work / "subs.srt"
        simple_ass = work / "subs.ass"
        simple_out = work / f"output.{options.output_format}"

        link_or_copy(video_path, simple_video)

        if subtitle_path.suffix.lower() == ".ass" and not options.one_line:
            shutil.copy2(subtitle_path, simple_ass)
        else:
            src_for_ass = subtitle_path
            if subtitle_path.suffix.lower() == ".srt":
                prepare_srt(subtitle_path, simple_srt, one_line=options.one_line)
                src_for_ass = simple_srt
            else:
                # ASS + one_line: flatten via round-trip is awkward; copy ASS as-is
                shutil.copy2(subtitle_path, simple_ass)
                src_for_ass = None
            if src_for_ass is not None:
                write_ass(src_for_ass, simple_ass, width, height, options)

        ass_filter = simple_ass.as_posix().replace(":", r"\:")
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(simple_video),
            "-vf",
            f"ass='{ass_filter}'",
            "-c:v",
            "libx264",
            "-preset",
            options.preset,
            "-crf",
            str(options.crf),
            "-pix_fmt",
            "yuv420p",
        ]
        if options.audio_copy:
            cmd.extend(["-c:a", "copy"])
        else:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        if options.output_format == "mp4":
            cmd.extend(["-movflags", "+faststart"])
        cmd.append(str(simple_out))

        print("Running:", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True, cwd=str(work))
        shutil.copy2(simple_out, output_path)

    print(f"Wrote: {output_path}", flush=True)
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Burn SRT/ASS into a video (keep resolution, optional compression)."
    )
    parser.add_argument("video", type=Path, help="Input video (mp4/mkv/mov/...)")
    parser.add_argument("subtitle", type=Path, help="Input subtitle (.srt or .ass)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output video path. Default: <video>.burned.<format>",
    )
    parser.add_argument("--format", choices=OUTPUT_FORMATS, default="mp4")
    parser.add_argument("--font-size", type=int, default=46)
    parser.add_argument("--margin-v", type=int, default=18, help="Distance from bottom edge")
    parser.add_argument("--font-name", default="Microsoft YaHei")
    parser.add_argument("--crf", type=int, default=24, help="x264 quality (18=large, 28=small)")
    parser.add_argument("--preset", default="fast")
    parser.add_argument(
        "--keep-line-breaks",
        action="store_true",
        help="Keep multi-line cues (default flattens to one line)",
    )
    parser.add_argument("--reencode-audio", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    video = args.video.expanduser().resolve()
    subtitle = args.subtitle.expanduser().resolve()
    if not video.exists():
        raise SystemExit(f"Video not found: {video}")
    if not subtitle.exists():
        raise SystemExit(f"Subtitle not found: {subtitle}")

    output = args.output
    if output is None:
        output = video.with_name(f"{video.stem}.burned.{args.format}")
    else:
        output = output.expanduser().resolve()

    options = BurnOptions(
        font_name=args.font_name,
        font_size=args.font_size,
        margin_v=args.margin_v,
        one_line=not args.keep_line_breaks,
        crf=args.crf,
        preset=args.preset,
        audio_copy=not args.reencode_audio,
        output_format=args.format,
    )
    burn_video(video, subtitle, output, options)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"ffmpeg failed with exit code {exc.returncode}", file=sys.stderr)
        raise SystemExit(exc.returncode)
