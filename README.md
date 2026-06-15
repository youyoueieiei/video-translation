# MP4 Subtitle Translator

MP4 Subtitle Translator is a local desktop and command-line tool for creating translated subtitles from MP4 videos.

It can transcribe speech, translate subtitles, preserve timestamps, apply custom glossary corrections, and optionally burn translated subtitles into a new MP4 video.

## Features

- Transcribe MP4 audio with `faster-whisper`.
- Translate subtitles between languages such as Japanese, Chinese, English, and Korean.
- Export translated `.srt` subtitle files.
- Optional GUI with English and Chinese interface support.
- Optional glossary CSV for names, brands, group names, and protected English words.
- Optional context-aware translation mode for better sentence flow.
- Optional song/music mode for lyrics and music videos.
- Optional MP4 output with translated subtitles burned into the video.
- Optional short-subtitle merge helper for subtitle cleanup.

## How It Works

```text
input.mp4
  -> extract audio with ffmpeg
  -> transcribe source language with faster-whisper
  -> save source .srt
  -> translate subtitle text
  -> save translated .srt
  -> optionally burn subtitles into a new MP4
```

## Requirements

- Windows, macOS, or Linux
- Python 3.10 or newer
- `ffmpeg`
- Internet access for Google Translate mobile web requests

## Setup

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install `ffmpeg` and make sure it is available on PATH:

```powershell
ffmpeg -version
```

On Windows, you can install `ffmpeg` with Winget:

```powershell
winget install Gyan.FFmpeg
```

Restart your terminal after installing `ffmpeg`.

## Quick Start

### GUI

Double-click:

```text
run_subtitle_translator.bat
```

Or start the GUI from PowerShell:

```powershell
python subtitle_translator_app.py
```

In the app:

1. Use `UI Language` to switch between English and Chinese.
2. Select an input `.mp4` video.
3. Choose an output folder.
4. Optionally select a glossary CSV.
5. (Optional) Set `Translate start` time to skip initial audio (format HH:MM:SS). Lines that end before this time will be copied unchanged into the translated SRT.
5. Select the source language and output language.
6. Select translation quality.
7. Choose whether to export only `.srt` or also create a subtitled `.mp4`.
8. For music videos or lyrics, enable song/music mode.
9. Click `Start`.

### Command Line

Basic usage:

```powershell
python translate_video.py "path/to/video.mp4" --source-language ja --target-language zh-CN
```

Japanese to Simplified Chinese with better context-aware translation:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --translation-mode context
```

Export translated SRT and a subtitled MP4:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --burn
```

For music videos, songs, or lyrics:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --song-mode --force-transcribe --force-translate
```

Use a GPU if CUDA is available:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --device cuda --compute-type float16
```

## GUI Options

### UI Language

Switches the app interface between English and Chinese. This does not change the subtitle translation language.

### Files

- `Input MP4`: source video file.
- `Output Folder`: where generated subtitle/video files are saved.
- `Glossary CSV`: optional custom dictionary for names and protected words.

### Languages And Quality

- `Source Language`: spoken language in the video.
- `Output Language`: subtitle translation language.
- `Whisper Model`: transcription model size. Larger models are usually more accurate but slower.
- `Translation Quality`: choose fast line-by-line translation or better context-aware grouped translation.

### Export Options

- `Also add translated subtitles to a new MP4 video`: creates a subtitled MP4 in addition to SRT files.
- `Song/music mode for lyrics`: disables voice activity filtering, useful for music videos.
- `Force transcribe again`: regenerates the source SRT even if it already exists.
- `Force translate again`: regenerates the translated SRT even if it already exists.

## Translation Quality

The app has two translation modes:

- `Fast Google (line by line)`: translates each subtitle cue separately. Faster, but short cues can sound unnatural.
- `Better Context Google (grouped subtitles)`: translates nearby subtitle cues together, then splits them back into SRT cues. This usually improves sentence flow, pronouns, jokes, names, and lyrics.

Command-line example:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --translation-mode context --context-size 6
```

Use `--force-translate` if you already generated subtitles and want to regenerate them with another translation mode.

## Glossary

Use `glossary_template.csv` as a starting template.

CSV format:

```csv
source,target,mode,notes
Kis-My-Ft2,Kis-My-Ft2,protect,Keep group name unchanged
YouTube,YouTube,protect,Keep English brand unchanged
キスマイ,Kis-My-Ft2,replace,Force Japanese nickname to preferred group name
藤ヶ谷,Fujigaya,replace,Person name example
```

Glossary modes:

- `protect`: keep the source word unchanged. Use this for English words, brands, product names, and names that should not be translated.
- `replace`: force the source word to become your preferred target word. Use this for names, nicknames, show names, group names, and recurring phrases.

Tips:

- Edit the CSV in Excel or a text editor.
- Keep the header row exactly as `source,target,mode,notes`.
- Save as UTF-8 CSV if your glossary contains Japanese or Chinese.
- If you change the glossary after generating subtitles, run again with `--force-translate`.

## Output Files

By default, files are written to an `output` folder next to the video:

```text
<video folder>/output/
```

Example outputs:

```text
video.ja.srt
video.ja.zh-CN.srt
video.zh-CN_subtitled.mp4
```

The translated subtitle file is the main output:

```text
video.<source-language>.<target-language>.srt
```

The MP4 output is only created when `--burn` is enabled.

## Merge Short Subtitle Lines

Use this helper if your translated SRT has many very short subtitle cues:

```powershell
python merge_short_subtitles.py "output/video.ja.zh-CN.srt" --min-chars 3 --max-gap-ms 1200 --max-duration-ms 7000
```

This creates a separate merged SRT and keeps the original file unchanged.

## Common Language Codes

- `ja`: Japanese
- `zh-CN`: Simplified Chinese
- `zh-TW`: Traditional Chinese
- `en`: English
- `ko`: Korean
- `fr`: French
- `de`: German
- `es`: Spanish

## Troubleshooting

### `ffmpeg` Not Found

Install `ffmpeg`, restart the terminal, and confirm:

```powershell
ffmpeg -version
```

### Empty SRT For Music Videos

Enable song/music mode and regenerate:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --song-mode --force-transcribe --force-translate
```

### Glossary Changes Do Not Appear

Regenerate translation:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --glossary glossary_template.csv --force-translate
```

### First Run Is Slow

The first run downloads the Whisper model. Larger models like `medium` and `large-v3` are slower, especially on CPU.

## Notes

- Translation uses Google Translate mobile web requests, so it needs internet access.
- For best transcription quality, use a larger Whisper model if your computer can handle it.
- For best translation quality, use context-aware translation plus a glossary.
