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


def language_code(value: str) -> str:
    value = value.strip()
    if "(" in value and ")" in value:
        return value.rsplit("(", 1)[1].split(")", 1)[0].strip()
    return value


class SubtitleTranslatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MP4 Subtitle Translator")
        self.geometry("860x660")
        self.minsize(800, 600)

        self.video_path = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.glossary_path = tk.StringVar()
        self.source_language = tk.StringVar(value="Japanese (ja)")
        self.target_language = tk.StringVar(value="Chinese Simplified (zh-CN)")
        self.model_size = tk.StringVar(value="small")
        self.burn_video = tk.BooleanVar(value=False)
        self.song_mode = tk.BooleanVar(value=False)
        self.force_transcribe = tk.BooleanVar(value=False)
        self.force_translate = tk.BooleanVar(value=False)

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self.after(100, self._drain_output_queue)

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=16)
        root.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(root, text="MP4 Subtitle Translator", font=("Segoe UI", 16, "bold"))
        title.pack(anchor=tk.W)

        description = ttk.Label(
            root,
            text="Select an MP4, choose source and target languages, then export translated subtitles.",
        )
        description.pack(anchor=tk.W, pady=(4, 16))

        form = ttk.Frame(root)
        form.pack(fill=tk.X)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Input MP4").grid(row=0, column=0, sticky=tk.W, pady=6)
        ttk.Entry(form, textvariable=self.video_path).grid(row=0, column=1, sticky=tk.EW, padx=8)
        ttk.Button(form, text="Browse...", command=self._select_video).grid(row=0, column=2, sticky=tk.E)

        ttk.Label(form, text="Output Folder").grid(row=1, column=0, sticky=tk.W, pady=6)
        ttk.Entry(form, textvariable=self.output_dir).grid(row=1, column=1, sticky=tk.EW, padx=8)
        ttk.Button(form, text="Browse...", command=self._select_output_dir).grid(row=1, column=2, sticky=tk.E)

        ttk.Label(form, text="Glossary CSV (optional)").grid(row=2, column=0, sticky=tk.W, pady=6)
        ttk.Entry(form, textvariable=self.glossary_path).grid(row=2, column=1, sticky=tk.EW, padx=8)
        ttk.Button(form, text="Browse...", command=self._select_glossary).grid(row=2, column=2, sticky=tk.E)

        ttk.Label(form, text="Source Language").grid(row=3, column=0, sticky=tk.W, pady=6)
        ttk.Combobox(form, textvariable=self.source_language, values=LANGUAGES).grid(
            row=3, column=1, sticky=tk.EW, padx=8
        )

        ttk.Label(form, text="Output Language").grid(row=4, column=0, sticky=tk.W, pady=6)
        ttk.Combobox(form, textvariable=self.target_language, values=LANGUAGES).grid(
            row=4, column=1, sticky=tk.EW, padx=8
        )

        ttk.Label(form, text="Whisper Model").grid(row=5, column=0, sticky=tk.W, pady=6)
        ttk.Combobox(form, textvariable=self.model_size, values=MODELS, state="readonly").grid(
            row=5, column=1, sticky=tk.W, padx=8
        )

        options = ttk.LabelFrame(root, text="Export Options", padding=12)
        options.pack(fill=tk.X, pady=16)
        ttk.Checkbutton(
            options,
            text="Also add translated subtitles to a new MP4 video",
            variable=self.burn_video,
        ).pack(anchor=tk.W)
        ttk.Checkbutton(
            options,
            text="Song/music mode for lyrics",
            variable=self.song_mode,
        ).pack(anchor=tk.W, pady=(6, 0))
        ttk.Checkbutton(
            options,
            text="Force transcribe again, even if source SRT already exists",
            variable=self.force_transcribe,
        ).pack(anchor=tk.W, pady=(6, 0))
        ttk.Checkbutton(
            options,
            text="Force translate again, even if translated SRT already exists",
            variable=self.force_translate,
        ).pack(anchor=tk.W, pady=(6, 0))

        actions = ttk.Frame(root)
        actions.pack(fill=tk.X)
        self.start_button = ttk.Button(actions, text="Start", command=self._start)
        self.start_button.pack(side=tk.LEFT)
        self.stop_button = ttk.Button(actions, text="Stop", command=self._stop, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=8)

        ttk.Label(root, text="Log").pack(anchor=tk.W, pady=(16, 4))
        log_frame = ttk.Frame(root)
        log_frame.pack(fill=tk.BOTH, expand=True)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=14)
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

    def _select_video(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select MP4 video",
            filetypes=[("MP4 videos", "*.mp4"), ("All files", "*.*")],
        )
        if selected:
            self.video_path.set(selected)
            if not self.output_dir.get():
                self.output_dir.set(str(Path(selected).parent / "output"))

    def _select_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Select output folder")
        if selected:
            self.output_dir.set(selected)

    def _select_glossary(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select glossary CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.glossary_path.set(selected)

    def _start(self) -> None:
        video = self.video_path.get().strip()
        if not video:
            messagebox.showerror("Missing video", "Please select an MP4 video.")
            return
        if not Path(video).exists():
            messagebox.showerror("Video not found", f"Video not found:\n{video}")
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
        ]

        if self.output_dir.get().strip():
            command.extend(["--output-dir", self.output_dir.get().strip()])
        if self.glossary_path.get().strip():
            command.extend(["--glossary", self.glossary_path.get().strip()])
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
        self._log("Starting subtitle translation...\n")
        self._log("Command:\n" + " ".join(f'"{part}"' if " " in part else part for part in command) + "\n\n")

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
                self.output_queue.put("\nDone. Translated SRT exported successfully.\n")
            else:
                self.output_queue.put(f"\nFailed with exit code {exit_code}.\n")
        except Exception as exc:
            self.output_queue.put(f"\nError: {exc}\n")
        finally:
            self.process = None
            self.output_queue.put("__PROCESS_FINISHED__")

    def _stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self._log("\nStopping...\n")

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
