# MP4 Subtitle Translator

Local tool to **transcribe**, **translate**, and **burn** subtitles for videos.

- **GUI** (Chinese / English): translate tab + burn/compress tab  
- **CLI**: `translate_video.py`, `burn_video.py`, `merge_short_subtitles.py`  
- Works offline for JA→ZH when online translators rate-limit (MarianMT fallback)

---

## Features

| Area | What it does |
|------|----------------|
| Transcribe | `faster-whisper` speech-to-text → source `.srt` |
| Translate | Google / MyMemory online, or local MarianMT (JA→ZH) |
| Glossary | CSV protect/replace for names, titles, brands |
| Context mode | Group nearby cues for better sentence flow |
| Song mode | Better for music / lyrics (weaker VAD filtering) |
| Burn / compress | Video + SRT/ASS → subtitled MP4/MKV, same resolution, CRF compression |
| GUI | Double-click launcher, no console window |

---

## Requirements

- Windows / macOS / Linux  
- Python **3.10+**  
- [`ffmpeg`](https://ffmpeg.org/) on `PATH`  
- Internet for online translation (optional if you use `--translation-backend local` for JA→ZH)

### Setup

```powershell
cd video-translation
python -m pip install -r requirements.txt
ffmpeg -version
```

Windows ffmpeg install:

```powershell
winget install Gyan.FFmpeg
```

Restart the terminal after installing ffmpeg.

`requirements.txt` includes `torch` / `transformers` for the **offline JA→ZH** fallback. First local run may download a model (~hundreds of MB).

---

## Quick start (GUI)

Double-click:

```text
run_subtitle_translator.bat
```

or the silent launcher:

```text
run_subtitle_translator.vbs
```

Optional desktop shortcut:

```powershell
powershell -ExecutionPolicy Bypass -File .\create_desktop_shortcut.ps1
```

Or:

```powershell
python subtitle_translator_app.py
python subtitle_translator_app.py "path\to\video.mp4"
```

### Translate tab

1. Choose input video and output folder  
2. Optional glossary CSV  
3. Source / target language, Whisper model, translation quality  
4. Click **Extract source subtitles only** to create and review the Japanese SRT  
5. After checking it, click **Translate existing subtitles only** to create the Chinese SRT  
6. Use **Start** for the complete workflow; optional: burn into MP4 or force a full re-run

### Burn / Compress tab

1. Input video (mp4 / mkv / mov / avi / webm / …)  
2. Input subtitle (`.srt` or `.ass`)  
3. Output path + format (`mp4` or `mkv`)  
4. Font size, bottom margin, one-line toggle, CRF quality  
5. Click **Start burn** — resolution stays the same; CRF controls file size

---

## Command line

### Translate

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN
```

Extract Japanese subtitles only (creates/replaces the `.ja.srt` file):

```powershell
python translate_video.py "video.mp4" --source-language ja --transcribe-only
```

After reviewing or editing that SRT, translate it only (creates/replaces the `.ja.zh-CN.srt` file):

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --translate-only
```

Context-aware + glossary:

```powershell
python translate_video.py "video.mp4" `
  --source-language ja --target-language zh-CN `
  --translation-mode context `
  --glossary glossary_template.csv
```

### LLM translation API

The GUI offers an optional **LLM API** translation engine. It uses an OpenAI-compatible
Chat Completions endpoint; the existing automatic backend remains the default. Configure
these as Windows user environment variables before launching the app:

- `OPENAI_API_KEY` — API key from your provider
- `OPENAI_MODEL` — model name (defaults to `gpt-4o-mini`)
- `OPENAI_BASE_URL` — API base URL (defaults to `https://api.openai.com/v1`)

The API provider may charge for usage. The key is read from the environment and is not
stored in the project. In the GUI, choose **LLM API** and **Better context (grouped
subtitles)**. For the CLI:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN `
  --translator llm --translation-mode context --glossary glossary_template.csv
```

Also burn while translating:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN --burn
```

Song / lyrics:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN `
  --song-mode --force-transcribe --force-translate
```

Voice-activity filtering is enabled by default. For performances or noisy audio, disable
it with `--no-vad-filter` (the older `--song-mode` flag remains supported). This may
preserve quiet dialogue, but can also repeat lines; the GUI offers the same option.

Force offline JA→ZH:

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN `
  --translation-backend local
```

GPU transcription (if CUDA is available):

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN `
  --device cuda --compute-type float16
```

Skip translating cues before a timestamp (copy them as-is):

```powershell
python translate_video.py "video.mp4" --source-language ja --target-language zh-CN `
  --translate-start 00:01:30
```

### Burn / compress only

```powershell
python burn_video.py "video.mp4" "subs.zh-CN.srt" `
  -o "video.burned.mp4" --font-size 46 --crf 24 --format mp4
```

Useful flags:

| Flag | Meaning |
|------|---------|
| `--font-size` | ASS font size (default 46) |
| `--margin-v` | Distance from bottom edge |
| `--crf` | x264 quality: lower = bigger/better (18–28 typical; 24 recommended) |
| `--format` | `mp4` or `mkv` |
| `--keep-line-breaks` | Keep multi-line cues (default flattens to one line) |

### Merge very short cues

```powershell
python merge_short_subtitles.py "output/video.ja.zh-CN.srt" `
  --min-chars 3 --max-gap-ms 1200 --max-duration-ms 7000
```

Creates a new merged SRT; original file is unchanged.

---

## Glossary

Start from `glossary_template.csv`.

```csv
source,target,mode,notes
Kis-My-Ft2,Kis-My-Ft2,protect,Keep group name unchanged
キスマイ,Kis-My-Ft2,replace,Nickname → official name
```

- **`protect`**: leave the source text unchanged  
- **`replace`**: force a preferred translation  

Save as UTF-8. After editing, re-run with `--force-translate`.

---

## Output layout

Default folder (next to the video unless you pass `--output-dir`):

```text
<video folder>/output/
  video.ja.srt
  video.ja.zh-CN.srt
  video.zh-CN_subtitled.mp4   # only with --burn
```

Burn-only default name:

```text
video.burned.mp4
```

---

## Project files

| File | Role |
|------|------|
| `subtitle_translator_app.py` | GUI |
| `translate_video.py` | Transcribe + translate CLI |
| `burn_video.py` | Burn/compress CLI |
| `merge_short_subtitles.py` | Merge short SRT cues |
| `glossary_template.csv` | Glossary starter |
| `run_subtitle_translator.bat` / `.vbs` | GUI launchers |
| `create_desktop_shortcut.ps1` | Desktop shortcut helper |

Media outputs (`*.mp4`, `*.srt`, `*.mkv`, …) are **gitignored** and should not be committed.

---

## Language codes

`ja` `zh-CN` `zh-TW` `en` `ko` `fr` `de` `es`

---

## Troubleshooting

**ffmpeg not found** — install, restart terminal, run `ffmpeg -version`.

**Empty SRT on music videos** — use `--song-mode --force-transcribe --force-translate`.

**Online translation rate-limited** — the tool falls back to local MarianMT for JA→ZH, or pass `--translation-backend local`.

**Glossary not applied** — run again with `--force-translate`.

**First run slow** — Whisper (and optional MarianMT) models download once; larger Whisper sizes are slower on CPU.

**GUI opens a black console** — use `run_subtitle_translator.vbs` or recreate the desktop shortcut with `create_desktop_shortcut.ps1`.

---

## License

See [LICENSE](LICENSE).
