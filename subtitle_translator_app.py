from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


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

QUALITY_MODES = [
    "Fast Google (line by line)",
    "Better Context Google (grouped subtitles)",
]

UI_LANGUAGES = ["English", "中文"]

QUALITY_MODE_LABELS = {
    "English": [
        "Fast Google (line by line)",
        "Better Context Google (grouped subtitles)",
    ],
    "中文": [
        "快速 Google（逐行翻译）",
        "更好上下文 Google（分组字幕）",
    ],
}

QUALITY_MODE_VALUES = {
    "Fast Google (line by line)": "fast",
    "Better Context Google (grouped subtitles)": "context",
    "快速 Google（逐行翻译）": "fast",
    "更好上下文 Google（分组字幕）": "context",
}

TEXT = {
    "English": {
        "app_title": "MP4 Subtitle Translator",
        "ui_language": "UI Language",
        "description": "Select an MP4, choose source and target languages, then export translated subtitles.",
        "files_section": "Files",
        "translation_section": "Languages and Quality",
        "input_mp4": "Input MP4",
        "output_folder": "Output Folder",
        "glossary_csv": "Glossary CSV (optional)",
        "source_language": "Source Language",
        "output_language": "Output Language",
        "whisper_model": "Whisper Model",
        "translation_quality": "Translation Quality",
        "browse": "Browse...",
        "export_options": "Export Options",
        "burn_video": "Also add translated subtitles to a new MP4 video",
        "song_mode": "Song/music mode for lyrics",
        "force_transcribe": "Force transcribe again, even if source SRT already exists",
        "force_translate": "Force translate again, even if translated SRT already exists",
        "start": "Start",
        "stop": "Stop",
        "log": "Log",
        "select_video_title": "Select MP4 video",
        "select_output_title": "Select output folder",
        "select_glossary_title": "Select glossary CSV",
        "mp4_files": "MP4 videos",
        "csv_files": "CSV files",
        "all_files": "All files",
        "missing_video_title": "Missing video",
        "missing_video_message": "Please select an MP4 video.",
        "video_not_found_title": "Video not found",
        "video_not_found_message": "Video not found:",
        "starting": "Starting subtitle translation...",
        "command": "Command:",
        "done": "Done. Translated SRT exported successfully.",
        "failed": "Failed with exit code",
        "error": "Error",
        "stopping": "Stopping...",
    },
    "中文": {
        "app_title": "MP4 字幕翻译工具",
        "ui_language": "界面语言",
        "description": "选择 MP4 视频，设置源语言和目标语言，然后导出翻译字幕。",
        "files_section": "文件",
        "translation_section": "语言与质量",
        "input_mp4": "输入 MP4",
        "output_folder": "输出文件夹",
        "glossary_csv": "术语表 CSV（可选）",
        "source_language": "源语言",
        "output_language": "输出语言",
        "whisper_model": "Whisper 模型",
        "translation_quality": "翻译质量",
        "browse": "浏览...",
        "export_options": "导出选项",
        "burn_video": "同时生成带翻译字幕的新 MP4 视频",
        "song_mode": "歌曲/歌词模式",
        "force_transcribe": "重新转录，即使源字幕已存在",
        "force_translate": "重新翻译，即使翻译字幕已存在",
        "start": "开始",
        "stop": "停止",
        "log": "日志",
        "select_video_title": "选择 MP4 视频",
        "select_output_title": "选择输出文件夹",
        "select_glossary_title": "选择术语表 CSV",
        "mp4_files": "MP4 视频",
        "csv_files": "CSV 文件",
        "all_files": "所有文件",
        "missing_video_title": "缺少视频",
        "missing_video_message": "请选择一个 MP4 视频。",
        "video_not_found_title": "找不到视频",
        "video_not_found_message": "找不到视频：",
        "starting": "开始字幕翻译...",
        "command": "命令：",
        "done": "完成。已成功导出翻译 SRT。",
        "failed": "失败，退出代码",
        "error": "错误",
        "stopping": "正在停止...",
    },
}


def language_code(value: str) -> str:
    value = value.strip()
    if "(" in value and ")" in value:
        return value.rsplit("(", 1)[1].split(")", 1)[0].strip()
    return value


def translation_mode(value: str) -> str:
    return QUALITY_MODE_VALUES.get(value, "fast")


def display_path(path: Path | str) -> str:
    return str(path).replace("\\", "/")


class SubtitleTranslatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MP4 Subtitle Translator")
        self.geometry("980x760")
        self.minsize(900, 680)

        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.glossary_path = tk.StringVar()
        self.ui_language = tk.StringVar(value="English")
        self.translate_start = tk.StringVar(value="")
        self.source_language = tk.StringVar(value="Japanese (ja)")
        self.target_language = tk.StringVar(value="Chinese Simplified (zh-CN)")
        self.model_size = tk.StringVar(value="small")
        self.quality_mode = tk.StringVar(value="Better Context Google (grouped subtitles)")
        self.burn_video = tk.BooleanVar(value=False)
        self.song_mode = tk.BooleanVar(value=False)
        self.force_transcribe = tk.BooleanVar(value=False)
        self.force_translate = tk.BooleanVar(value=False)

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.widgets: dict[str, tk.Widget] = {}
        self.run_text = TEXT["English"].copy()

        self._build_ui()
        self._apply_ui_language()
        self.after(100, self._drain_output_queue)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=18)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(6, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky=tk.EW)
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="MP4 Subtitle Translator", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, sticky=tk.W)
        self.widgets["title"] = title

        self.widgets["ui_language_label"] = ttk.Label(header, text="UI Language")
        self.widgets["ui_language_label"].grid(row=0, column=1, sticky=tk.E, padx=(12, 6))
        ui_language_combo = ttk.Combobox(
            header,
            textvariable=self.ui_language,
            values=UI_LANGUAGES,
            state="readonly",
            width=10,
        )
        ui_language_combo.grid(row=0, column=2, sticky=tk.E)
        ui_language_combo.bind("<<ComboboxSelected>>", lambda _event: self._apply_ui_language())

        description = ttk.Label(
            root,
            text="Select an MP4, choose source and target languages, then export translated subtitles.",
            wraplength=760,
        )
        description.grid(row=1, column=0, sticky=tk.W, pady=(6, 16))
        self.widgets["description"] = description

        files_frame = ttk.LabelFrame(root, text="Files", padding=14)
        files_frame.grid(row=2, column=0, sticky=tk.EW, pady=(0, 12))
        files_frame.columnconfigure(1, weight=1)
        self.widgets["files_frame"] = files_frame

        self.widgets["input_mp4_label"] = ttk.Label(files_frame, text="Input MP4")
        self.widgets["input_mp4_label"].grid(row=0, column=0, sticky=tk.W, padx=(0, 12), pady=6)
        ttk.Entry(files_frame, textvariable=self.video_path).grid(row=0, column=1, sticky=tk.EW, padx=(0, 8), pady=6)
        self.widgets["browse_video_button"] = ttk.Button(files_frame, text="Browse...", command=self._select_video)
        self.widgets["browse_video_button"].grid(row=0, column=2, sticky=tk.E, pady=6)

        self.widgets["output_folder_label"] = ttk.Label(files_frame, text="Output Folder")
        self.widgets["output_folder_label"].grid(row=1, column=0, sticky=tk.W, padx=(0, 12), pady=6)
        ttk.Entry(files_frame, textvariable=self.output_dir).grid(row=1, column=1, sticky=tk.EW, padx=(0, 8), pady=6)
        self.widgets["browse_output_button"] = ttk.Button(files_frame, text="Browse...", command=self._select_output_dir)
        self.widgets["browse_output_button"].grid(row=1, column=2, sticky=tk.E, pady=6)

        self.widgets["glossary_label"] = ttk.Label(files_frame, text="Glossary CSV (optional)")
        self.widgets["glossary_label"].grid(row=2, column=0, sticky=tk.W, padx=(0, 12), pady=6)
        ttk.Entry(files_frame, textvariable=self.glossary_path).grid(row=2, column=1, sticky=tk.EW, padx=(0, 8), pady=6)
        self.widgets["browse_glossary_button"] = ttk.Button(files_frame, text="Browse...", command=self._select_glossary)
        self.widgets["browse_glossary_button"].grid(row=2, column=2, sticky=tk.E, pady=6)

        # Translate start time (optional)
        self.widgets["translate_start_label"] = ttk.Label(files_frame, text="Translate start (HH:MM:SS, optional)")
        self.widgets["translate_start_label"].grid(row=3, column=0, sticky=tk.W, padx=(0, 12), pady=6)
        ttk.Entry(files_frame, textvariable=self.translate_start, width=18).grid(row=3, column=1, sticky=tk.W, padx=(0, 8), pady=6)
        ttk.Label(files_frame, text="(leave blank = 0s)").grid(row=3, column=2, sticky=tk.W, pady=6)

        translation_frame = ttk.LabelFrame(root, text="Languages and Quality", padding=14)
        translation_frame.grid(row=3, column=0, sticky=tk.EW, pady=(0, 12))
        translation_frame.columnconfigure(1, weight=1)
        translation_frame.columnconfigure(3, weight=1)
        self.widgets["translation_frame"] = translation_frame

        self.widgets["source_language_label"] = ttk.Label(translation_frame, text="Source Language")
        self.widgets["source_language_label"].grid(row=0, column=0, sticky=tk.W, padx=(0, 12), pady=6)
        ttk.Combobox(translation_frame, textvariable=self.source_language, values=LANGUAGES, state="readonly").grid(
            row=0, column=1, sticky=tk.EW, padx=(0, 18), pady=6
        )

        self.widgets["output_language_label"] = ttk.Label(translation_frame, text="Output Language")
        self.widgets["output_language_label"].grid(row=0, column=2, sticky=tk.W, padx=(0, 12), pady=6)
        ttk.Combobox(translation_frame, textvariable=self.target_language, values=LANGUAGES, state="readonly").grid(
            row=0, column=3, sticky=tk.EW, pady=6
        )

        self.widgets["whisper_model_label"] = ttk.Label(translation_frame, text="Whisper Model")
        self.widgets["whisper_model_label"].grid(row=1, column=0, sticky=tk.W, padx=(0, 12), pady=6)
        ttk.Combobox(translation_frame, textvariable=self.model_size, values=MODELS, state="readonly", width=18).grid(
            row=1, column=1, sticky=tk.W, padx=(0, 18), pady=6
        )

        self.widgets["translation_quality_label"] = ttk.Label(translation_frame, text="Translation Quality")
        self.widgets["translation_quality_label"].grid(row=1, column=2, sticky=tk.W, padx=(0, 12), pady=6)
        quality_combo = ttk.Combobox(
            translation_frame,
            textvariable=self.quality_mode,
            values=QUALITY_MODES,
            state="readonly",
        )
        quality_combo.grid(row=1, column=3, sticky=tk.EW, pady=6
        )
        self.widgets["quality_combo"] = quality_combo

        options = ttk.LabelFrame(root, text="Export Options", padding=12)
        options.grid(row=4, column=0, sticky=tk.EW, pady=(0, 12))
        options.columnconfigure(0, weight=1)
        options.columnconfigure(1, weight=1)
        self.widgets["options_frame"] = options
        self.widgets["burn_video_check"] = ttk.Checkbutton(
            options,
            text="Also add translated subtitles to a new MP4 video",
            variable=self.burn_video,
        )
        self.widgets["burn_video_check"].grid(row=0, column=0, sticky=tk.W, padx=(0, 16), pady=4)
        self.widgets["song_mode_check"] = ttk.Checkbutton(
            options,
            text="Song/music mode for lyrics",
            variable=self.song_mode,
        )
        self.widgets["song_mode_check"].grid(row=0, column=1, sticky=tk.W, pady=4)
        self.widgets["force_transcribe_check"] = ttk.Checkbutton(
            options,
            text="Force transcribe again, even if source SRT already exists",
            variable=self.force_transcribe,
        )
        self.widgets["force_transcribe_check"].grid(row=1, column=0, sticky=tk.W, padx=(0, 16), pady=4)
        self.widgets["force_translate_check"] = ttk.Checkbutton(
            options,
            text="Force translate again, even if translated SRT already exists",
            variable=self.force_translate,
        )
        self.widgets["force_translate_check"].grid(row=1, column=1, sticky=tk.W, pady=4)

        actions = ttk.Frame(root)
        actions.grid(row=5, column=0, sticky=tk.EW, pady=(0, 12))
        actions.columnconfigure(0, weight=1)
        self.start_button = ttk.Button(actions, text="Start", command=self._start)
        self.start_button.grid(row=0, column=1, sticky=tk.E, padx=(0, 8))
        self.stop_button = ttk.Button(actions, text="Stop", command=self._stop, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=2, sticky=tk.E)

        log_frame = ttk.LabelFrame(root, text="Log", padding=10)
        log_frame.grid(row=6, column=0, sticky=tk.NSEW)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.widgets["log_frame"] = log_frame

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=12)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

    def _text(self, key: str) -> str:
        return TEXT[self.ui_language.get()].get(key, TEXT["English"][key])

    def _apply_ui_language(self) -> None:
        labels = QUALITY_MODE_LABELS[self.ui_language.get()]
        current_mode = translation_mode(self.quality_mode.get())
        self.quality_mode.set(labels[1] if current_mode == "context" else labels[0])

        quality_combo = self.widgets.get("quality_combo")
        if isinstance(quality_combo, ttk.Combobox):
            quality_combo.configure(values=labels)

        self.title(self._text("app_title"))
        self.widgets["title"].configure(text=self._text("app_title"))
        self.widgets["ui_language_label"].configure(text=self._text("ui_language"))
        self.widgets["description"].configure(text=self._text("description"))
        self.widgets["files_frame"].configure(text=self._text("files_section"))
        self.widgets["translation_frame"].configure(text=self._text("translation_section"))
        self.widgets["input_mp4_label"].configure(text=self._text("input_mp4"))
        self.widgets["output_folder_label"].configure(text=self._text("output_folder"))
        self.widgets["glossary_label"].configure(text=self._text("glossary_csv"))
        self.widgets["source_language_label"].configure(text=self._text("source_language"))
        self.widgets["output_language_label"].configure(text=self._text("output_language"))
        self.widgets["whisper_model_label"].configure(text=self._text("whisper_model"))
        self.widgets["translation_quality_label"].configure(text=self._text("translation_quality"))
        self.widgets["browse_video_button"].configure(text=self._text("browse"))
        self.widgets["browse_output_button"].configure(text=self._text("browse"))
        self.widgets["browse_glossary_button"].configure(text=self._text("browse"))
        self.widgets["options_frame"].configure(text=self._text("export_options"))
        self.widgets["burn_video_check"].configure(text=self._text("burn_video"))
        self.widgets["song_mode_check"].configure(text=self._text("song_mode"))
        self.widgets["force_transcribe_check"].configure(text=self._text("force_transcribe"))
        self.widgets["force_translate_check"].configure(text=self._text("force_translate"))
        self.start_button.configure(text=self._text("start"))
        self.stop_button.configure(text=self._text("stop"))
        self.widgets["log_frame"].configure(text=self._text("log"))

    def _select_video(self) -> None:
        selected = filedialog.askopenfilename(
            title=self._text("select_video_title"),
            filetypes=[(self._text("mp4_files"), "*.mp4"), (self._text("all_files"), "*.*")],
        )
        if selected:
            self.video_path.set(display_path(selected))
            if not self.output_dir.get():
                self.output_dir.set(display_path(Path(selected).parent / "output"))

    def _select_output_dir(self) -> None:
        selected = filedialog.askdirectory(title=self._text("select_output_title"))
        if selected:
            self.output_dir.set(display_path(selected))

    def _select_glossary(self) -> None:
        selected = filedialog.askopenfilename(
            title=self._text("select_glossary_title"),
            filetypes=[(self._text("csv_files"), "*.csv"), (self._text("all_files"), "*.*")],
        )
        if selected:
            self.glossary_path.set(display_path(selected))

    def _start(self) -> None:
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

        script_path = Path(__file__).with_name("translate_video.py")
        command = [
            sys.executable,
            "-u",
            str(script_path),
            video,
            "--source-language",
            language_code(self.source_language.get()),
            "--target-language",
            language_code(self.target_language.get()),
            "--model-size",
            self.model_size.get(),
            "--translation-mode",
            translation_mode(self.quality_mode.get()),
        ]

        if self.output_dir.get().strip():
            command.extend(["--output-dir", self.output_dir.get().strip()])
        if self.glossary_path.get().strip():
            command.extend(["--glossary", self.glossary_path.get().strip()])
        if self.translate_start.get().strip():
            command.extend(["--translate-start", self.translate_start.get().strip()])
        if self.burn_video.get():
            command.append("--burn")
        if self.song_mode.get():
            command.append("--song-mode")
        if self.force_transcribe.get():
            command.append("--force-transcribe")
        if self.force_translate.get():
            command.append("--force-translate")

        self._set_running(True)
        self._clear_log()
        self.run_text = TEXT[self.ui_language.get()].copy()
        self._log(f"{self._text('starting')}\n")
        self._log(f"{self._text('command')}\n" + " ".join(f'"{part}"' if " " in part else part for part in command) + "\n\n")

        thread = threading.Thread(target=self._run_command, args=(command,), daemon=True)
        thread.start()

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
            )
            assert self.process.stdout is not None
            for line in self.process.stdout:
                self.output_queue.put(line)
            exit_code = self.process.wait()
            if exit_code == 0:
                self.output_queue.put(f"\n{self.run_text['done']}\n")
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
        self.start_button.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_button.configure(state=tk.NORMAL if running else tk.DISABLED)

    def _clear_log(self) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)

    def _log(self, text: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)


if __name__ == "__main__":
    app = SubtitleTranslatorApp()
    app.mainloop()
