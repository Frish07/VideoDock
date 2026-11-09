from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

from .core import (DownloadRequest, available_heights, find_ffmpeg, find_node,
                   format_selector, friendly_error, normalize_url, unique_destination)
from .media import ensure_compatible_mp4


class EventWriter:
    def __init__(self, path: Path):
        self.file = path.open("a", encoding="utf-8", buffering=1)

    def emit(self, event: str, **data):
        self.file.write(json.dumps({"event": event, **data}, ensure_ascii=False) + "\n")
        self.file.flush()

    def debug(self, message):
        if not message.startswith("[debug]"):
            self.emit("log", message=message)

    info = debug

    def warning(self, message):
        self.emit("warning", message=message)

    def error(self, message):
        self.emit("log", message=message)


def base_options(events: EventWriter) -> dict:
    from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
    ffmpeg = str(find_ffmpeg())
    # yt-dlp's FFmpegFD.available() creates a processor without a downloader.
    # Set the same process-local context as yt-dlp's CLI, so it also sees our
    # bundled binary instead of accidentally searching the machine's PATH.
    FFmpegPostProcessor._ffmpeg_location.set(ffmpeg)
    node = find_node()
    return {
        "logger": events, "quiet": True, "no_warnings": False,
        "noplaylist": True, "socket_timeout": 25, "retries": 3,
        "fragment_retries": 3, "cachedir": False, "windowsfilenames": True,
        "js_runtimes": {"node": {"path": node}} if node else {},
        "ffmpeg_location": ffmpeg,
        "remote_components": set(),
    }


def check_video(info: dict):
    if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming", "post_live"}:
        raise ValueError("Этот эфир ещё идёт или обрабатывается. Дождитесь публикации записи.")
    if info.get("_type") in {"playlist", "multi_video"}:
        raise ValueError("Вставьте ссылку на один ролик.")


def diagnose_tools(events: EventWriter):
    """Offline support diagnostics for the packaged external tools."""
    import subprocess
    from yt_dlp import YoutubeDL
    from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor
    from yt_dlp.utils._utils import _get_exe_version_output
    executable = str(find_ffmpeg())
    try:
        result = subprocess.run([executable, "-bsfs"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=15)
        direct = {"returncode": result.returncode, "output": result.stdout[:1800]}
    except Exception as exc:
        direct = {"error": repr(exc)}
    output = _get_exe_version_output(executable, ["-bsfs"])
    with YoutubeDL(base_options(events)) as ydl:
        pp = FFmpegPostProcessor(ydl)
        events.emit("diagnostics", ffmpeg=executable, direct=direct, helper_output=str(output)[:1800],
                    paths=pp._paths, available=pp.available, versions=pp.get_versions(ydl))


def inspect_video(url: str, events: EventWriter, workdir: Path):
    from yt_dlp import YoutubeDL
    events.emit("status", message="Получаем информацию о видео…")
    with YoutubeDL(base_options(events)) as ydl:
        info = ydl.extract_info(normalize_url(url), download=False)
    check_video(info)
    thumbnail = ""
    thumb_url = info.get("thumbnail", "")
    if thumb_url.startswith("https://"):
        try:
            import certifi
            import ssl
            request = Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=8, context=ssl.create_default_context(cafile=certifi.where())) as response:
                content = response.read(4 * 1024 * 1024 + 1)
                if len(content) <= 4 * 1024 * 1024:
                    path = workdir / "thumbnail.jpg"
                    path.write_bytes(content)
                    thumbnail = str(path)
        except Exception:
            pass  # Preview must never prevent a download.
    result = {
        "url": normalize_url(url), "id": info["id"], "title": info.get("title", "Видео"),
        "channel": info.get("channel") or info.get("uploader") or "YouTube",
        "duration": info.get("duration"), "heights": available_heights(info.get("formats", [])),
        "thumbnail": thumbnail,
    }
    events.emit("metadata", **result)


def download(request: DownloadRequest, events: EventWriter, staging: Path):
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import download_range_func

    request.validate()
    output = Path(request.directory).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not output.is_dir():
        raise ValueError("Выбранный путь не является папкой.")
    if staging.parent.resolve() != output or not staging.name.startswith(".videodock-"):
        raise ValueError("Временная папка должна находиться в папке сохранения.")
    staging.mkdir(parents=True, exist_ok=True)
    last_progress = 0.0

    def progress(data):
        nonlocal last_progress
        if data["status"] == "downloading":
            now = time.monotonic()
            if now - last_progress < 0.25:
                return
            last_progress = now
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            downloaded = data.get("downloaded_bytes", 0)
            events.emit("progress", percent=min(100, downloaded / total * 100) if total else None,
                        downloaded=downloaded, total=total, speed=data.get("speed"), eta=data.get("eta"),
                        stream=Path(data.get("filename", "")).suffix)
        elif data["status"] == "finished":
            events.emit("status", message="Поток получен. Обрабатываем файл…")

    def postprocess(data):
        if data["status"] in {"started", "processing"}:
            events.emit("status", message="Обрабатываем аудио…" if request.audio else "Объединяем видео и звук…")

    options = base_options(events)
    options.update({
        "format": format_selector(request.height, request.container, request.audio),
        "outtmpl": str(staging / "%(title).110B [%(id)s].%(ext)s"),
        "progress_hooks": [progress], "postprocessor_hooks": [postprocess],
        "concurrent_fragment_downloads": 4,
        "overwrites": False,
        "final_ext": request.container,
    })
    if request.audio:
        options["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": request.container,
                                      "preferredquality": "192"}]
    else:
        options["merge_output_format"] = request.container
        options["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": request.container}]
        if request.container == "mp4":
            options["format_sort"] = ["res", "hdr:SDR", "fps", "vcodec:h264", "lang", "channels:2", "acodec:aac"]
    events.emit("status", message="Подключаемся к YouTube…")
    finished = []
    with YoutubeDL(options) as ydl:
        # yt-dlp reports the final path after merging, conversion and moves.
        ydl.add_post_hook(finished.append)
        info = ydl.extract_info(normalize_url(request.url), download=False)
        check_video(info)
        first, last = request.validate(info.get("duration"))
        if request.trim:
            ydl.params["download_ranges"] = download_range_func(None, [(first, last if last is not None else float("inf"))])
            ydl.params["force_keyframes_at_cuts"] = True
            events.emit("status", message="Скачиваем выбранный фрагмент. Точная обрезка может занять время…")
        else:
            events.emit("status", message="Скачиваем видео…" if not request.audio else "Скачиваем аудио…")
        # Reuse the extracted formats and URLs instead of making a second network extraction.
        ydl.process_ie_result(info, download=True)
    if len(finished) != 1:
        raise RuntimeError("Загрузка завершилась без готового файла. Попробуйте другой формат.")
    final = Path(finished[0]).resolve()
    if final.parent != staging.resolve() or final.suffix.lower() != f".{request.container}" or not final.is_file():
        raise RuntimeError("Загрузка завершилась без готового файла. Попробуйте другой формат.")
    if not final.stat().st_size:
        raise RuntimeError("Получен пустой файл. Повторите загрузку.")
    if not request.audio and request.container == "mp4":
        events.emit("status", message="Подготавливаем совместимый MP4…")
        ensure_compatible_mp4(final, Path(options["ffmpeg_location"]))
    # Publish atomically without leaving an empty/partial destination on cancellation.
    destination = unique_destination(output, final.name)
    while True:
        try:
            if os.name == "nt":
                final.rename(destination)  # Windows rename never overwrites an existing file.
            else:
                os.link(final, destination)
                final.unlink()
            break
        except FileExistsError:
            destination = unique_destination(output, final.name)
    events.emit("complete", path=str(destination), title=info.get("title", final.stem),
                size=destination.stat().st_size, container=request.container, audio=request.audio,
                start=first if request.trim else None, end=last if request.trim else None)


def run_worker(jobfile: str) -> int:
    jobpath = Path(jobfile)
    job = json.loads(jobpath.read_text(encoding="utf-8-sig"))
    workdir = jobpath.parent
    events = EventWriter(workdir / "events.jsonl")
    # Windowed PyInstaller applications have no sys.stdout/sys.stderr.
    with (workdir / "debug.log").open("w", encoding="utf-8") as log:
        sys.stdout = log
        sys.stderr = log
        try:
            if job["action"] == "inspect":
                inspect_video(job["url"], events, workdir)
            elif job["action"] == "download":
                download(DownloadRequest(**job["request"]), events, Path(job["staging"]))
            elif job["action"] == "diagnostics":
                diagnose_tools(events)
            else:
                raise ValueError("Неизвестная операция.")
            return 0
        except Exception as exc:
            import traceback
            traceback.print_exc(file=log)
            events.emit("error", message=friendly_error(str(exc)))
            return 1
        finally:
            events.file.close()
