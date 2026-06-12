# MP4 Subtitle Translator

This tool takes an MP4 video, transcribes the spoken language, translates the subtitle text, and exports a translated `.srt` file.

## Process Summary

1. Input an `.mp4` video.
2. Extract audio from the MP4 with `ffmpeg`.
3. Transcribe the audio with `faster-whisper`.
4. Save the source-language subtitles as `.srt`.
5. Translate each subtitle cue with timestamps preserved.
6. Export the translated `.srt` file.
7. Optionally merge very short subtitle cues.
8. Optionally burn translated subtitles into a new MP4.

## What It Does

- Input: MP4 video
- Select source language: `--source-language`
- Select output translation language: `--target-language`
- Export: translated `.srt` file

## Setup

Install Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Install `ffmpeg` and make sure it is available on PATH:

```powershell
ffmpeg -version
```

If `ffmpeg` is missing, install it with Winget:

```powershell
winget install Gyan.FFmpeg
```

Then restart the terminal.

## Run

### GUI Program

Double-click this file:

```text
run_subtitle_translator.bat
```

In the app:

1. Select an input `.mp4` video.
2. Optionally select a glossary CSV for names, brands, and protected words. Leave it blank if you do not need custom corrections.
3. Select the source language.
4. Select the output translation language.
5. Leave the checkbox off to export translated `.srt` only.
6. Check `Also add translated subtitles to a new MP4 video` to export `.srt` and a new subtitled `.mp4`.
7. For music videos or lyrics, check `Song/music mode for lyrics`.
8. Click `Start`.

You can also start the GUI from PowerShell:

```powershell
python subtitle_translator_app.py
```

### Command Line

Basic format:

```powershell
python translate_video.py "path\to\video.mp4" --source-language ja --target-language zh-CN
```

Japanese to Simplified Chinese:

```powershell
python translate_video.py "Process video\Kis-My-Ft2【ピンスポクエスト】キスマイYouTubeが地上波に初進出という事態が起こりました！.mp4" --source-language ja --target-language zh-CN --model-size small
```

Use a glossary for names, brands, and protected English words:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --glossary glossary_template.csv
```

English to Chinese:

```powershell
python translate_video.py "video.mp4" --source-language en --target-language zh-CN
```

Japanese to English:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language en
```

Use a faster, lower-quality transcription model:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --model-size small
```

For music videos, songs, or lyrics:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --song-mode --force-transcribe --force-translate
```

Use a GPU if CUDA is available:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --device cuda --compute-type float16
```

Regenerate subtitles even if output files already exist:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --force-transcribe --force-translate
```

Merge very short translated subtitle lines into nearby timestamps:

```powershell
python merge_short_subtitles.py "Process video\output\video.ja.zh-CN.srt" --min-chars 3 --max-gap-ms 1200 --max-duration-ms 7000
```

## Glossary

Use `glossary_template.csv` as the starting template.

The CSV columns are:

```csv
source,target,mode,notes
Kis-My-Ft2,Kis-My-Ft2,protect,Keep group name unchanged
YouTube,YouTube,protect,Keep English brand unchanged
キスマイ,Kis-My-Ft2,replace,Force Japanese nickname to preferred group name
藤ヶ谷,Fujigaya,replace,Person name example
```

Glossary modes:

- `protect`: keep the source word unchanged. Good for English words, brands, product names, and names that should not be translated.
- `replace`: force the source word to become your preferred target word. Good for Japanese names, nicknames, show names, and idol group names.

Tips:

- Edit the CSV in Excel or a text editor.
- Keep the header row exactly as `source,target,mode,notes`.
- Save as UTF-8 CSV if your glossary contains Japanese or Chinese.
- If you already generated the translated SRT and then changed the glossary, run again with `--force-translate`.

## Output

Files are written to an `output` folder next to the video by default:

```text
<video folder>\output\
```

Example output names:

```text
video.ja.srt
video.ja.zh-CN.srt
video.ja.zh-CN.merged.srt
```

The translated subtitle file is the main output:

```text
video.<source-language>.<target-language>.srt
```

The `.mp4` output is only created when using `--burn`.

## Notes

- The first run can take a long time because the Whisper model must download.
- `medium` gives better transcription quality but is slower on CPU.
- Translation uses Google Translate mobile web requests, so it needs internet access.
- Common language codes: `ja`, `zh-CN`, `zh-TW`, `en`, `ko`, `fr`, `de`, `es`.
