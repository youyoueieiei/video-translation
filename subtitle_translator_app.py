from __future__ import annotations

import argparse
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


APP_DIR = Path(__file__).resolve().parent

LANGUAGES = [
    "Japanese (ja)",
    "Chinese Simplified (zh-CN)",
    "Chinese Traditional (zh-TW)",
    "English (en)",
    "Korean (ko)",
    "French (fr)",
    "German (de)",
    "Spanish (es)",
]

MODELS = ["tiny", "base", "small", "medium", "large-v3"]
UI_LANGUAGES = ["中文", "English"]
OUTPUT_FORMATS = ["mp4", "mkv"]
CRF_PRESETS = ["18 (更高画质)", "20", "22", "24 (推荐)", "26", "28 (更小体积)"]

QUALITY_MODE_LABELS = {
    "English": [
        "Fast (line by line)",
        "Better context (grouped subtitles)",
    ],
    "中文": [
        "快速翻译（逐行）",
        "更好上下文（分组字幕）",
    ],
}

QUALITY_MODE_VALUES = {
    "Fast (line by line)": "fast",
    "Better context (grouped subtitles)": "context",
    "快速翻译（逐行）": "fast",
    "更好上下文（分组字幕）": "context",
}

TRANSLATOR_LABELS = {
    "English": ["Local (Japanese -> Mandarin)", "Automatic (local/online)", "LLM API"],
    "中文": ["本地（日文→普通话）", "自动（本地/在线）", "大模型 API"],
}

TRANSLATOR_VALUES = {
    "Local (Japanese -> Mandarin)": "local",
    "Automatic (local/online)": "auto",
    "LLM API": "llm",
    "本地（日文→普通话）": "local",
    "自动（本地/在线）": "auto",
    "大模型 API": "llm",
}

TEXT = {
    "English": {
        "app_title": "MP4 Subtitle Translator",
        "ui_language": "UI Language",
        "tab_translate": "Translate",
        "tab_burn": "Burn / Compress",
        "description": "Select an MP4, choose languages, then export translated subtitles (optional burn-in). Chinese output is Mandarin, not Cantonese.",
        "burn_description": "Select a video + SRT/ASS, set font size and compression, then export a subtitled video.",
        "files_section": "Files",
        "translation_section": "Languages and Quality",
        "input_mp4": "Input MP4",
        "output_folder": "Output Folder",
        "glossary_csv": "Glossary CSV (optional)",
        "translate_start": "Translate start (HH:MM:SS)",
        "translate_start_hint": "blank = from beginning",
        "source_language": "Source Language",
        "output_language": "Output Language",
        "whisper_model": "Whisper Model",
        "translation_quality": "Translation Quality",
        "translation_backend": "Translation engine",
        "browse": "Browse...",
        "export_options": "Export Options",
        "burn_video": "Also burn subtitles into a new MP4",
        "disable_vad": "Disable speech filter for performances/noisy audio (may repeat lines)",
        "force_transcribe": "Force re-transcribe even if source SRT exists",
        "force_translate": "Force re-translate even if translated SRT exists",
        "burn_files": "Input / Output",
        "burn_video_label": "Input video",
        "burn_srt_label": "Subtitle (SRT/ASS)",
        "burn_output_label": "Output file",
        "burn_style": "Subtitle style",
        "burn_font_size": "Font size",
        "burn_margin_v": "Bottom margin",
        "burn_one_line": "Force one line (no line breaks)",
        "burn_compress": "Compression (same resolution)",
        "burn_format": "Output format",
        "burn_crf": "Quality (CRF)",
        "burn_start": "Start burn",
        "start": "Start",
        "transcribe_only": "Extract source subtitles only",
        "translate_only": "Translate existing subtitles only",
        "stop": "Stop",
        "open_output": "Open Output Folder",
        "log": "Log",
        "status_idle": "Ready",
        "status_running": "Running…",
        "select_video_title": "Select video",
        "select_output_title": "Select output folder",
        "select_glossary_title": "Select glossary CSV",
        "select_srt_title": "Select subtitle file",
        "select_output_file_title": "Select output video path",
        "mp4_files": "MP4 videos",
        "video_files": "Video files",
        "srt_files": "Subtitle files",
        "csv_files": "CSV files",
        "all_files": "All files",
        "missing_video_title": "Missing video",
        "missing_video_message": "Please select a video file.",
        "missing_srt_title": "Missing subtitle",
        "missing_srt_message": "Please select an SRT/ASS file.",
        "video_not_found_title": "Video not found",
        "video_not_found_message": "Video not found:",
        "output_missing_title": "No output folder",
        "output_missing_message": "Set or create an output folder first.",
        "starting": "Starting subtitle translation...",
        "starting_transcribe_only": "Extracting source subtitles only...",
        "starting_translate_only": "Translating existing source subtitles...",
        "starting_burn": "Starting burn / compress...",
        "command": "Command:",
        "done": "Done. Translated SRT exported successfully.",
        "done_transcribe_only": "Done. Review the source-language SRT before translating.",
        "done_translate_only": "Done. Translated SRT exported successfully.",
        "done_burn": "Done. Subtitled video exported successfully.",
        "failed": "Failed with exit code",
        "error": "Error",
        "stopping": "Stopping...",
    },
    "中文": {
        "app_title": "MP4 字幕翻译工具",
        "ui_language": "界面语言",
        "tab_translate": "翻译",
        "tab_burn": "压制 / 烧录",
        "description": "选择 MP4，设置源语言与目标语言，导出翻译字幕；可选烧录到新视频。中文输出为普通话，不保留粤语。",
        "burn_description": "选择视频 + SRT/ASS，设置字号与压缩参数，输出带字幕视频（分辨率不变）。",
        "files_section": "文件",
        "translation_section": "语言与质量",
        "input_mp4": "输入 MP4",
        "output_folder": "输出文件夹",
        "glossary_csv": "术语表 CSV（可选）",
        "translate_start": "开始翻译时间 (HH:MM:SS)",
        "translate_start_hint": "留空 = 从头开始",
        "source_language": "源语言",
        "output_language": "输出语言",
        "whisper_model": "Whisper 模型",
        "translation_quality": "翻译质量",
        "translation_backend": "翻译引擎",
        "browse": "浏览...",
        "export_options": "导出选项",
        "burn_video": "同时生成带字幕的新 MP4",
        "disable_vad": "演出/嘈杂音频关闭语音过滤（可能重复转写）",
        "force_transcribe": "强制重新转录（即使源字幕已存在）",
        "force_translate": "强制重新翻译（即使译文已存在）",
        "burn_files": "输入 / 输出",
        "burn_video_label": "输入视频",
        "burn_srt_label": "字幕 (SRT/ASS)",
        "burn_output_label": "输出文件",
        "burn_style": "字幕样式",
        "burn_font_size": "字号",
        "burn_margin_v": "距底部边距",
        "burn_one_line": "强制单行（不换行）",
        "burn_compress": "压缩（保持分辨率）",
        "burn_format": "输出格式",
        "burn_crf": "画质 (CRF)",
        "burn_start": "开始压制",
        "start": "开始",
        "transcribe_only": "仅提取源语言字幕",
        "translate_only": "仅翻译现有字幕",
        "stop": "停止",
        "open_output": "打开输出目录",
        "log": "日志",
        "status_idle": "就绪",
        "status_running": "运行中…",
        "select_video_title": "选择视频",
        "select_output_title": "选择输出文件夹",
        "select_glossary_title": "选择术语表 CSV",
        "select_srt_title": "选择字幕文件",
        "select_output_file_title": "选择输出视频路径",
        "mp4_files": "MP4 视频",
        "video_files": "视频文件",
        "srt_files": "字幕文件",
        "csv_files": "CSV 文件",
        "all_files": "所有文件",
        "missing_video_title": "缺少视频",
        "missing_video_message": "请选择一个视频文件。",
        "missing_srt_title": "缺少字幕",
        "missing_srt_message": "请选择一个 SRT/ASS 字幕文件。",
        "video_not_found_title": "找不到视频",
        "video_not_found_message": "找不到视频：",
        "output_missing_title": "没有输出目录",
        "output_missing_message": "请先设置输出文件夹。",
        "starting": "开始字幕翻译…",
        "starting_transcribe_only": "仅提取源语言字幕…",
        "starting_translate_only": "翻译现有源语言字幕…",
        "starting_burn": "开始压制 / 烧录…",
        "command": "命令：",
        "done": "完成。已成功导出翻译 SRT。",
        "done_transcribe_only": "完成。请先检查源语言 SRT，再执行翻译。",
        "done_translate_only": "完成。已成功导出翻译 SRT。",
        "done_burn": "完成。已成功导出带字幕视频。",
        "failed": "失败，退出代码",
        "error": "错误",
        "stopping": "正在停止…",
    },
}


def language_code(value: str) -> str:
    value = value.strip()
    if "(" in value and ")" in value:
        return value.rsplit("(", 1)[1].split(")", 1)[0].strip()
    return value


def translation_mode(value: str) -> str:
    return QUALITY_MODE_VALUES.get(value, "fast")


def translator_backend(value: str) -> str:
    return TRANSLATOR_VALUES.get(value, "auto")


def display_path(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def parse_crf(label: str) -> int:
    token = label.strip().split()[0]
    return int(token)


def default_glossary() -> str:
    candidate = APP_DIR / "glossary_template.csv"
    if candidate.exists():
        return display_path(candidate)
    return ""


class SubtitleTranslatorApp(tk.Tk):
    def __init__(self, initial_video: str | None = None) -> None:
        super().__init__()
        self.title("MP4 字幕翻译工具")
        self.geometry("1040x820")
        self.minsize(940, 720)

        try:
            style = ttk.Style(self)
            if "vista" in style.theme_names():
                style.theme_use("vista")
            elif "clam" in style.theme_names():
                style.theme_use("clam")
        except tk.TclError:
            pass

        # Translate tab vars
        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.glossary_path = tk.StringVar(value=default_glossary())
        self.ui_language = tk.StringVar(value="中文")
        self.translate_start = tk.StringVar(value="")
        self.source_language = tk.StringVar(value="Japanese (ja)")
        self.target_language = tk.StringVar(value="Chinese Simplified (zh-CN)")
        self.model_size = tk.StringVar(value="medium")
        self.quality_mode = tk.StringVar(value=QUALITY_MODE_LABELS["中文"][1])
        self.translator = tk.StringVar(value=TRANSLATOR_LABELS["中文"][0])
        self.burn_video = tk.BooleanVar(value=False)
        self.disable_vad = tk.BooleanVar(value=False)
        self.force_transcribe = tk.BooleanVar(value=False)
        self.force_translate = tk.BooleanVar(value=False)

        # Burn tab vars
        self.burn_input_video = tk.StringVar()
        self.burn_input_srt = tk.StringVar()
        self.burn_output_file = tk.StringVar()
        self.burn_font_size = tk.StringVar(value="46")
        self.burn_margin_v = tk.StringVar(value="18")
        self.burn_one_line = tk.BooleanVar(value=True)
        self.burn_format = tk.StringVar(value="mp4")
        self.burn_crf = tk.StringVar(value="24 (推荐)")

        self.status_text = tk.StringVar(value=TEXT["中文"]["status_idle"])
        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.widgets: dict[str, tk.Widget] = {}
        self.run_text = TEXT["中文"].copy()
        self._done_key = "done"

        self._build_ui()
        self._apply_ui_language()
        self.after(100, self._drain_output_queue)

        if initial_video:
            self._set_translate_video(initial_video)
            self.burn_input_video.set(display_path(initial_video))

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky=tk.EW)
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="MP4 字幕翻译工具", font=("Microsoft YaHei UI", 16, "bold"))
        title.grid(row=0, column=0, sticky=tk.W)
        self.widgets["title"] = title

        self.widgets["ui_language_label"] = ttk.Label(header, text="界面语言")
        self.widgets["ui_language_label"].grid(row=0, column=1, sticky=tk.E, padx=(12, 6))
        ui_language_combo = ttk.Combobox(
            header, textvariable=self.ui_language, values=UI_LANGUAGES, state="readonly", width=10
        )
        ui_language_combo.grid(row=0, column=2, sticky=tk.E)
        ui_language_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_ui_language())

        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=1, column=0, sticky=tk.NSEW, pady=(10, 8))
        root.rowconfigure(1, weight=3)

        self.translate_tab = ttk.Frame(self.notebook, padding=10)
        self.burn_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.translate_tab, text="翻译")
        self.notebook.add(self.burn_tab, text="压制 / 烧录")
        self.widgets["notebook"] = self.notebook

        self._build_translate_tab(self.translate_tab)
        self._build_burn_tab(self.burn_tab)

        bottom = ttk.Frame(root)
        bottom.grid(row=2, column=0, sticky=tk.NSEW)
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=1)

        actions = ttk.Frame(bottom)
        actions.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        actions.columnconfigure(0, weight=1)
        ttk.Label(actions, textvariable=self.status_text).grid(row=0, column=0, sticky=tk.W)
        self.open_output_button = ttk.Button(
            actions, text="打开输出目录", command=self._open_output_folder
        )
        self.open_output_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 8))
        self.stop_button = ttk.Button(actions, text="停止", command=self._stop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, sticky=tk.E)

        log_frame = ttk.LabelFrame(bottom, text="日志", padding=8)
        log_frame.grid(row=1, column=0, sticky=tk.NSEW)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.widgets["log_frame"] = log_frame
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

    def _build_translate_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        description = ttk.Label(parent, text="", wraplength=920)
        description.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.widgets["description"] = description

        files_frame = ttk.LabelFrame(parent, text="文件", padding=12)
        files_frame.grid(row=1, column=0, sticky=tk.EW, pady=(0, 10))
        files_frame.columnconfigure(1, weight=1)
        self.widgets["files_frame"] = files_frame

        self._add_path_row(
            files_frame, 0, "input_mp4_label", "browse_video_button", self.video_path, self._select_video
        )
        self._add_path_row(
            files_frame,
            1,
            "output_folder_label",
            "browse_output_button",
            self.output_dir,
            self._select_output_dir,
        )
        self._add_path_row(
            files_frame,
            2,
            "glossary_label",
            "browse_glossary_button",
            self.glossary_path,
            self._select_glossary,
        )

        self.widgets["translate_start_label"] = ttk.Label(files_frame, text="")
        self.widgets["translate_start_label"].grid(row=3, column=0, sticky=tk.W, padx=(0, 12), pady=5)
        ttk.Entry(files_frame, textvariable=self.translate_start, width=18).grid(
            row=3, column=1, sticky=tk.W, padx=(0, 8), pady=5
        )
        self.widgets["translate_start_hint"] = ttk.Label(files_frame, text="")
        self.widgets["translate_start_hint"].grid(row=3, column=2, sticky=tk.W, pady=5)

        translation_frame = ttk.LabelFrame(parent, text="语言与质量", padding=12)
        translation_frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 10))
        translation_frame.columnconfigure(1, weight=1)
        translation_frame.columnconfigure(3, weight=1)
        self.widgets["translation_frame"] = translation_frame

        self.widgets["source_language_label"] = ttk.Label(translation_frame, text="")
        self.widgets["source_language_label"].grid(row=0, column=0, sticky=tk.W, padx=(0, 12), pady=5)
        ttk.Combobox(
            translation_frame, textvariable=self.source_language, values=LANGUAGES, state="readonly"
        ).grid(row=0, column=1, sticky=tk.EW, padx=(0, 16), pady=5)

        self.widgets["output_language_label"] = ttk.Label(translation_frame, text="")
        self.widgets["output_language_label"].grid(row=0, column=2, sticky=tk.W, padx=(0, 12), pady=5)
        ttk.Combobox(
            translation_frame, textvariable=self.target_language, values=LANGUAGES, state="readonly"
        ).grid(row=0, column=3, sticky=tk.EW, pady=5)

        self.widgets["whisper_model_label"] = ttk.Label(translation_frame, text="")
        self.widgets["whisper_model_label"].grid(row=1, column=0, sticky=tk.W, padx=(0, 12), pady=5)
        ttk.Combobox(
            translation_frame, textvariable=self.model_size, values=MODELS, state="readonly", width=16
        ).grid(row=1, column=1, sticky=tk.W, padx=(0, 16), pady=5)

        self.widgets["translation_quality_label"] = ttk.Label(translation_frame, text="")
        self.widgets["translation_quality_label"].grid(
            row=1, column=2, sticky=tk.W, padx=(0, 12), pady=5
        )
        quality_combo = ttk.Combobox(
            translation_frame,
            textvariable=self.quality_mode,
            values=QUALITY_MODE_LABELS["中文"],
            state="readonly",
        )
        quality_combo.grid(row=1, column=3, sticky=tk.EW, pady=5)
        self.widgets["quality_combo"] = quality_combo

        self.widgets["translation_backend_label"] = ttk.Label(translation_frame, text="")
        self.widgets["translation_backend_label"].grid(
            row=2, column=0, sticky=tk.W, padx=(0, 12), pady=5
        )
        translator_combo = ttk.Combobox(
            translation_frame,
            textvariable=self.translator,
            values=TRANSLATOR_LABELS["中文"],
            state="readonly",
        )
        translator_combo.grid(row=2, column=1, columnspan=3, sticky=tk.EW, pady=5)
        self.widgets["translator_combo"] = translator_combo

        options = ttk.LabelFrame(parent, text="导出选项", padding=10)
        options.grid(row=3, column=0, sticky=tk.EW, pady=(0, 10))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        self.widgets["options_frame"] = options
        self.widgets["burn_video_check"] = ttk.Checkbutton(options, text="", variable=self.burn_video)
        self.widgets["burn_video_check"].grid(row=0, column=0, sticky=tk.W, pady=3)
        self.widgets["disable_vad_check"] = ttk.Checkbutton(options, text="", variable=self.disable_vad)
        self.widgets["disable_vad_check"].grid(row=0, column=1, sticky=tk.W, pady=3)
        self.widgets["force_transcribe_check"] = ttk.Checkbutton(
            options, text="", variable=self.force_transcribe
        )
        self.widgets["force_transcribe_check"].grid(row=1, column=0, sticky=tk.W, pady=3)
        self.widgets["force_translate_check"] = ttk.Checkbutton(
            options, text="", variable=self.force_translate
        )
        self.widgets["force_translate_check"].grid(row=1, column=1, sticky=tk.W, pady=3)

        actions = ttk.Frame(parent)
        actions.grid(row=4, column=0, sticky=tk.EW)
        actions.columnconfigure(0, weight=1)
        self.transcribe_only_button = ttk.Button(
            actions,
            text=self._text("transcribe_only"),
            command=lambda: self._start_translate(stage="transcribe"),
        )
        self.transcribe_only_button.grid(row=0, column=0, sticky=tk.W)
        self.translate_only_button = ttk.Button(
            actions,
            text=self._text("translate_only"),
            command=lambda: self._start_translate(stage="translate"),
        )
        self.translate_only_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 8))
        self.start_button = ttk.Button(
            actions, text=self._text("start"), command=self._start_translate
        )
        self.start_button.grid(row=0, column=2, sticky=tk.E)

    def _build_burn_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(0, weight=1)

        description = ttk.Label(parent, text="", wraplength=920)
        description.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.widgets["burn_description"] = description

        files = ttk.LabelFrame(parent, text="输入 / 输出", padding=12)
        files.grid(row=1, column=0, sticky=tk.EW, pady=(0, 10))
        files.columnconfigure(1, weight=1)
        self.widgets["burn_files"] = files

        self._add_path_row(
            files,
            0,
            "burn_video_label",
            "browse_burn_video_button",
            self.burn_input_video,
            self._select_burn_video,
        )
        self._add_path_row(
            files,
            1,
            "burn_srt_label",
            "browse_burn_srt_button",
            self.burn_input_srt,
            self._select_burn_srt,
        )
        self._add_path_row(
            files,
            2,
            "burn_output_label",
            "browse_burn_output_button",
            self.burn_output_file,
            self._select_burn_output,
        )

        style = ttk.LabelFrame(parent, text="字幕样式", padding=12)
        style.grid(row=2, column=0, sticky=tk.EW, pady=(0, 10))
        style.columnconfigure(1, weight=1)
        style.columnconfigure(3, weight=1)
        self.widgets["burn_style"] = style

        self.widgets["burn_font_size_label"] = ttk.Label(style, text="")
        self.widgets["burn_font_size_label"].grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        ttk.Spinbox(style, from_=18, to=96, textvariable=self.burn_font_size, width=8).grid(
            row=0, column=1, sticky=tk.W, pady=5
        )
        self.widgets["burn_margin_v_label"] = ttk.Label(style, text="")
        self.widgets["burn_margin_v_label"].grid(row=0, column=2, sticky=tk.W, padx=(16, 10), pady=5)
        ttk.Spinbox(style, from_=0, to=200, textvariable=self.burn_margin_v, width=8).grid(
            row=0, column=3, sticky=tk.W, pady=5
        )
        self.widgets["burn_one_line_check"] = ttk.Checkbutton(
            style, text="", variable=self.burn_one_line
        )
        self.widgets["burn_one_line_check"].grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=5)

        compress = ttk.LabelFrame(parent, text="压缩", padding=12)
        compress.grid(row=3, column=0, sticky=tk.EW, pady=(0, 10))
        compress.columnconfigure(1, weight=1)
        compress.columnconfigure(3, weight=1)
        self.widgets["burn_compress"] = compress

        self.widgets["burn_format_label"] = ttk.Label(compress, text="")
        self.widgets["burn_format_label"].grid(row=0, column=0, sticky=tk.W, padx=(0, 10), pady=5)
        ttk.Combobox(
            compress, textvariable=self.burn_format, values=OUTPUT_FORMATS, state="readonly", width=10
        ).grid(row=0, column=1, sticky=tk.W, pady=5)
        self.widgets["burn_crf_label"] = ttk.Label(compress, text="")
        self.widgets["burn_crf_label"].grid(row=0, column=2, sticky=tk.W, padx=(16, 10), pady=5)
        ttk.Combobox(
            compress, textvariable=self.burn_crf, values=CRF_PRESETS, state="readonly", width=16
        ).grid(row=0, column=3, sticky=tk.W, pady=5)

        self.burn_start_button = ttk.Button(parent, text="开始压制", command=self._start_burn)
        self.burn_start_button.grid(row=4, column=0, sticky=tk.E)

    def _add_path_row(
        self,
        parent: ttk.LabelFrame,
        row: int,
        label_key: str,
        button_key: str,
        variable: tk.StringVar,
        command,
    ) -> None:
        label = ttk.Label(parent, text="")
        label.grid(row=row, column=0, sticky=tk.W, padx=(0, 12), pady=5)
        self.widgets[label_key] = label
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky=tk.EW, padx=(0, 8), pady=5
        )
        button = ttk.Button(parent, text="浏览...", command=command)
        button.grid(row=row, column=2, sticky=tk.E, pady=5)
        self.widgets[button_key] = button

    def _text(self, key: str) -> str:
        return TEXT[self.ui_language.get()].get(key, TEXT["English"][key])

    def _apply_ui_language(self) -> None:
        labels = QUALITY_MODE_LABELS[self.ui_language.get()]
        current_mode = translation_mode(self.quality_mode.get())
        self.quality_mode.set(labels[1] if current_mode == "context" else labels[0])
        quality_combo = self.widgets.get("quality_combo")
        if isinstance(quality_combo, ttk.Combobox):
            quality_combo.configure(values=labels)

        translator_labels = TRANSLATOR_LABELS[self.ui_language.get()]
        current_translator = translator_backend(self.translator.get())
        self.translator.set(translator_labels[1] if current_translator == "llm" else translator_labels[0])
        translator_combo = self.widgets.get("translator_combo")
        if isinstance(translator_combo, ttk.Combobox):
            translator_combo.configure(values=translator_labels)

        self.title(self._text("app_title"))
        self.widgets["title"].configure(text=self._text("app_title"))
        self.widgets["ui_language_label"].configure(text=self._text("ui_language"))
        self.notebook.tab(0, text=self._text("tab_translate"))
        self.notebook.tab(1, text=self._text("tab_burn"))
        self.widgets["description"].configure(text=self._text("description"))
        self.widgets["burn_description"].configure(text=self._text("burn_description"))
        self.widgets["files_frame"].configure(text=self._text("files_section"))
        self.widgets["translation_frame"].configure(text=self._text("translation_section"))
        self.widgets["options_frame"].configure(text=self._text("export_options"))
        self.widgets["burn_files"].configure(text=self._text("burn_files"))
        self.widgets["burn_style"].configure(text=self._text("burn_style"))
        self.widgets["burn_compress"].configure(text=self._text("burn_compress"))
        self.widgets["log_frame"].configure(text=self._text("log"))

        for key in (
            "input_mp4_label",
            "output_folder_label",
            "glossary_label",
            "translate_start_label",
            "translate_start_hint",
            "source_language_label",
            "output_language_label",
            "whisper_model_label",
            "translation_quality_label",
            "translation_backend_label",
            "burn_video_label",
            "burn_srt_label",
            "burn_output_label",
            "burn_font_size_label",
            "burn_margin_v_label",
            "burn_format_label",
            "burn_crf_label",
        ):
            text_key = {
                "input_mp4_label": "input_mp4",
                "output_folder_label": "output_folder",
                "glossary_label": "glossary_csv",
                "translate_start_label": "translate_start",
                "translate_start_hint": "translate_start_hint",
                "source_language_label": "source_language",
                "output_language_label": "output_language",
                "whisper_model_label": "whisper_model",
                "translation_quality_label": "translation_quality",
                "translation_backend_label": "translation_backend",
                "burn_video_label": "burn_video_label",
                "burn_srt_label": "burn_srt_label",
                "burn_output_label": "burn_output_label",
                "burn_font_size_label": "burn_font_size",
                "burn_margin_v_label": "burn_margin_v",
                "burn_format_label": "burn_format",
                "burn_crf_label": "burn_crf",
            }[key]
            self.widgets[key].configure(text=self._text(text_key))

        for key in (
            "browse_video_button",
            "browse_output_button",
            "browse_glossary_button",
            "browse_burn_video_button",
            "browse_burn_srt_button",
            "browse_burn_output_button",
        ):
            self.widgets[key].configure(text=self._text("browse"))

        self.widgets["burn_video_check"].configure(text=self._text("burn_video"))
        self.widgets["disable_vad_check"].configure(text=self._text("disable_vad"))
        self.widgets["force_transcribe_check"].configure(text=self._text("force_transcribe"))
        self.widgets["force_translate_check"].configure(text=self._text("force_translate"))
        self.widgets["burn_one_line_check"].configure(text=self._text("burn_one_line"))
        self.transcribe_only_button.configure(text=self._text("transcribe_only"))
        self.translate_only_button.configure(text=self._text("translate_only"))
        self.start_button.configure(text=self._text("start"))
        self.burn_start_button.configure(text=self._text("burn_start"))
        self.open_output_button.configure(text=self._text("open_output"))
        self.stop_button.configure(text=self._text("stop"))
        if self.process is None:
            self.status_text.set(self._text("status_idle"))

    def _set_translate_video(self, path: str) -> None:
        video = Path(path)
        if not video.exists():
            return
        self.video_path.set(display_path(video))
        if not self.output_dir.get().strip():
            self.output_dir.set(display_path(video.parent / "Process video" / video.stem[:40]))

    def _select_video(self) -> None:
        selected = filedialog.askopenfilename(
            title=self._text("select_video_title"),
            filetypes=[
                (self._text("video_files"), "*.mp4 *.mkv *.mov *.avi *.webm *.m4v"),
                (self._text("all_files"), "*.*"),
            ],
            initialdir=str(APP_DIR.parent),
        )
        if selected:
            self._set_translate_video(selected)

    def _select_output_dir(self) -> None:
        selected = filedialog.askdirectory(title=self._text("select_output_title"))
        if selected:
            self.output_dir.set(display_path(selected))

    def _select_glossary(self) -> None:
        selected = filedialog.askopenfilename(
            title=self._text("select_glossary_title"),
            filetypes=[(self._text("csv_files"), "*.csv"), (self._text("all_files"), "*.*")],
            initialdir=str(APP_DIR),
        )
        if selected:
            self.glossary_path.set(display_path(selected))

    def _select_burn_video(self) -> None:
        selected = filedialog.askopenfilename(
            title=self._text("select_video_title"),
            filetypes=[
                (self._text("video_files"), "*.mp4 *.mkv *.mov *.avi *.webm *.m4v"),
                (self._text("all_files"), "*.*"),
            ],
            initialdir=str(APP_DIR.parent),
        )
        if selected:
            self.burn_input_video.set(display_path(selected))
            self._maybe_set_burn_output()

    def _select_burn_srt(self) -> None:
        selected = filedialog.askopenfilename(
            title=self._text("select_srt_title"),
            filetypes=[
                (self._text("srt_files"), "*.srt *.ass"),
                (self._text("all_files"), "*.*"),
            ],
            initialdir=str(APP_DIR.parent),
        )
        if selected:
            self.burn_input_srt.set(display_path(selected))
            self._maybe_set_burn_output()

    def _select_burn_output(self) -> None:
        fmt = self.burn_format.get().strip() or "mp4"
        selected = filedialog.asksaveasfilename(
            title=self._text("select_output_file_title"),
            defaultextension=f".{fmt}",
            filetypes=[(fmt.upper(), f"*.{fmt}"), (self._text("all_files"), "*.*")],
        )
        if selected:
            self.burn_output_file.set(display_path(selected))

    def _maybe_set_burn_output(self) -> None:
        if self.burn_output_file.get().strip():
            return
        video = self.burn_input_video.get().strip()
        if not video:
            return
        path = Path(video)
        fmt = self.burn_format.get().strip() or "mp4"
        self.burn_output_file.set(display_path(path.with_name(f"{path.stem}.burned.{fmt}")))

    def _open_output_folder(self) -> None:
        candidates = [
            self.burn_output_file.get().strip(),
            self.output_dir.get().strip(),
            self.video_path.get().strip(),
            self.burn_input_video.get().strip(),
        ]
        folder = None
        for item in candidates:
            if not item:
                continue
            path = Path(item)
            folder = path.parent if path.suffix else path
            break
        if folder is None:
            messagebox.showinfo(
                self._text("output_missing_title"), self._text("output_missing_message")
            )
            return
        folder.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(folder)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)

    def _start_translate(self, stage: str = "full") -> None:
        video = self.video_path.get().strip()
        if not video:
            messagebox.showerror(self._text("missing_video_title"), self._text("missing_video_message"))
            return
        if not Path(video).exists():
            messagebox.showerror(
                self._text("video_not_found_title"),
                f"{self._text('video_not_found_message')}\n{video}",
            )
            return

        command = [
            sys.executable,
            "-u",
            str(APP_DIR / "translate_video.py"),
            video,
            "--source-language",
            language_code(self.source_language.get()),
            "--target-language",
            language_code(self.target_language.get()),
            "--model-size",
            self.model_size.get(),
            "--translation-mode",
            translation_mode(self.quality_mode.get()),
            "--translator",
            translator_backend(self.translator.get()),
        ]
        if stage == "transcribe":
            command.append("--transcribe-only")
        elif stage == "translate":
            command.extend(["--translate-only", "--force-translate"])
        if self.output_dir.get().strip():
            command.extend(["--output-dir", self.output_dir.get().strip()])
        if self.glossary_path.get().strip():
            command.extend(["--glossary", self.glossary_path.get().strip()])
        if self.translate_start.get().strip():
            command.extend(["--translate-start", self.translate_start.get().strip()])
        if self.burn_video.get() and stage == "full":
            command.append("--burn")
        if self.disable_vad.get():
            command.append("--no-vad-filter")
        if self.force_transcribe.get() and stage == "full":
            command.append("--force-transcribe")
        if self.force_translate.get() and stage == "full":
            command.append("--force-translate")

        stage_keys = {
            "transcribe": ("starting_transcribe_only", "done_transcribe_only"),
            "translate": ("starting_translate_only", "done_translate_only"),
        }
        starting_key, done_key = stage_keys.get(stage, ("starting", "done"))
        self._launch_command(command, starting_key=starting_key, done_key=done_key)

    def _start_burn(self) -> None:
        video = self.burn_input_video.get().strip()
        srt_path = self.burn_input_srt.get().strip()
        if not video:
            messagebox.showerror(self._text("missing_video_title"), self._text("missing_video_message"))
            return
        if not srt_path:
            messagebox.showerror(self._text("missing_srt_title"), self._text("missing_srt_message"))
            return
        if not Path(video).exists():
            messagebox.showerror(
                self._text("video_not_found_title"),
                f"{self._text('video_not_found_message')}\n{video}",
            )
            return
        if not Path(srt_path).exists():
            messagebox.showerror(self._text("missing_srt_title"), f"{srt_path}")
            return

        self._maybe_set_burn_output()
        output = self.burn_output_file.get().strip()
        fmt = self.burn_format.get().strip() or "mp4"
        try:
            font_size = int(self.burn_font_size.get().strip())
            margin_v = int(self.burn_margin_v.get().strip())
            crf = parse_crf(self.burn_crf.get())
        except ValueError:
            messagebox.showerror(self._text("error"), "Font size / margin / CRF must be numbers.")
            return

        command = [
            sys.executable,
            "-u",
            str(APP_DIR / "burn_video.py"),
            video,
            srt_path,
            "-o",
            output,
            "--format",
            fmt,
            "--font-size",
            str(font_size),
            "--margin-v",
            str(margin_v),
            "--crf",
            str(crf),
        ]
        if not self.burn_one_line.get():
            command.append("--keep-line-breaks")

        self._launch_command(command, starting_key="starting_burn", done_key="done_burn")

    def _launch_command(self, command: list[str], starting_key: str, done_key: str) -> None:
        if self.process is not None:
            return
        self._done_key = done_key
        self._set_running(True)
        self._clear_log()
        self.run_text = TEXT[self.ui_language.get()].copy()
        self._log(f"{self._text(starting_key)}\n")
        self._log(
            f"{self._text('command')}\n"
            + " ".join(f'"{part}"' if " " in part else part for part in command)
            + "\n\n"
        )
        threading.Thread(target=self._run_command, args=(command,), daemon=True).start()

    def _run_command(self, command: list[str]) -> None:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=creationflags,
                cwd=str(APP_DIR),
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.output_queue.put(line)
            exit_code = self.process.wait()
            if exit_code == 0:
                self.output_queue.put(f"\n{self.run_text[self._done_key]}\n")
            else:
                self.output_queue.put(f"\n{self.run_text['failed']} {exit_code}.\n")
        except Exception as exc:
            self.output_queue.put(f"\n{self.run_text['error']}: {exc}\n")
        finally:
            self.process = None
            self.output_queue.put("__PROCESS_FINISHED__")

    def _stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self._log(f"\n{self._text('stopping')}\n")

    def _drain_output_queue(self) -> None:
        try:
            while True:
                line = self.output_queue.get_nowait()
                if line == "__PROCESS_FINISHED__":
                    self._set_running(False)
                else:
                    self._log(line)
        except queue.Empty:
            pass
        self.after(100, self._drain_output_queue)

    def _set_running(self, running: bool) -> None:
        state_start = tk.DISABLED if running else tk.NORMAL
        self.start_button.configure(state=state_start)
        self.transcribe_only_button.configure(state=state_start)
        self.translate_only_button.configure(state=state_start)
        self.burn_start_button.configure(state=state_start)
        self.stop_button.configure(state=tk.NORMAL if running else tk.DISABLED)
        self.status_text.set(self._text("status_running" if running else "status_idle"))

    def _clear_log(self) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _log(self, text: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MP4 Subtitle Translator GUI")
    parser.add_argument("video", nargs="?", default=None, help="Optional video path to pre-fill")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    app = SubtitleTranslatorApp(initial_video=args.video)
    app.mainloop()


if __name__ == "__main__":
    main()
