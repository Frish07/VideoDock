from __future__ import annotations

import math
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse


PLATFORMS = "YouTube · TikTok · Instagram · Facebook"
VIDEO_LINK_ERROR = "Не удалось найти видео в ссылке. Скопируйте ссылку на конкретный ролик."


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def normalize_url(value: str) -> str:
    return parse_video_url(value)[0]


def parse_video_url(value: str) -> tuple[str, str]:
    value = value.strip()
    if not value:
        raise ValueError("Вставьте ссылку на видео.")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme not in {"https", "http"} or not host or parsed.netloc.lower() != host
            or re.search(r"[\s\\\x00-\x1f\x7f]", value)):
        raise ValueError("Нужна обычная ссылка https:// на видео.")
    path = parsed.path.rstrip("/")
    parts = path.strip("/").split("/")
    query = parse_qs(parsed.query)
    video_id = ""

    if host in {"youtu.be", "www.youtu.be"}:
        video_id = parts[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parts[0] == "watch":
            video_id = query.get("v", [""])[0]
        elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed", "v"}:
            video_id = parts[1]
    elif host in {"tiktok.com", "www.tiktok.com", "m.tiktok.com", "vm.tiktok.com", "vt.tiktok.com",
                  "tiktokv.com", "www.tiktokv.com"}:
        if host in {"vm.tiktok.com", "vt.tiktok.com"}:
            if re.fullmatch(r"/[A-Za-z0-9_-]+", path):
                return f"https://{host}{path}/", "TikTok"
        elif re.fullmatch(r"/(?:@[\w.-]*/video|share/video|embed)/[0-9]+|/t/[A-Za-z0-9_-]+", path):
            return f"https://www.tiktok.com{path}/", "TikTok"
        else:
            legacy = re.fullmatch(r"/(?:embed/v2|v)/([0-9]+)(?:\.html)?", path)
            if legacy:
                return f"https://www.tiktok.com/embed/{legacy[1]}/", "TikTok"
        raise ValueError(VIDEO_LINK_ERROR)
    elif host in {"instagram.com", "www.instagram.com", "m.instagram.com"}:
        if re.fullmatch(r"/share/(?:(?:p|reel)/)?[A-Za-z0-9_-]+", path):
            return f"https://www.instagram.com{path}/", "Instagram"
        post = re.fullmatch(r"/(?:[A-Za-z0-9_.]+/)?(p|tv|reels?)/([A-Za-z0-9_-]+)", path)
        if post and not (post[1] in {"reel", "reels"} and post[2] == "audio"):
            kind = "reel" if post[1] == "reels" else post[1]
            return f"https://www.instagram.com/{kind}/{post[2]}/", "Instagram"
        raise ValueError(VIDEO_LINK_ERROR)
    elif host in {"fb.watch", "www.fb.watch"}:
        if re.fullmatch(r"/[A-Za-z0-9_-]+", path):
            return f"https://fb.watch{path}/", "Facebook"
        raise ValueError(VIDEO_LINK_ERROR)
    elif host in {"facebook.com", "www.facebook.com", "m.facebook.com", "web.facebook.com",
                  "fb.com", "www.fb.com"}:
        return _facebook_url(path, query, parsed.query), "Facebook"
    else:
        raise ValueError("Поддерживаются ссылки YouTube, TikTok, Instagram и Facebook.")
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        return f"https://www.youtube.com/watch?v={video_id}", "YouTube"
    raise ValueError(VIDEO_LINK_ERROR)


def _facebook_url(path: str, query: dict[str, list[str]], raw_query: str) -> str:
    root = "https://www.facebook.com"
    reel = re.fullmatch(r"/reels?/([0-9]+)", path)
    if reel:
        return f"{root}/reel/{reel[1]}/"
    video = re.fullmatch(r"/(?:[^/]+/)?videos/(?:[^/]+/)?([0-9]+)", path)
    if video:
        return f"{root}/watch/?v={video[1]}"
    if path in {"/watch", "/watch/live", "/video.php", "/video/video.php", "/video/embed",
                "/permalink.php", "/story.php", "/photo.php"}:
        if any(re.fullmatch(r"[0-9]+|pfbid[A-Za-z0-9]+", query.get(key, [""])[0])
               for key in ("v", "video_id", "story_fbid")):
            suffix = "/" if path in {"/watch", "/watch/live"} else ""
            return f"{root}{path}{suffix}?{raw_query}"
    if re.fullmatch(r"/share/(?:(?:r|v|p)/)?[A-Za-z0-9_-]+", path):
        return f"{root}{path}/"
    if re.fullmatch(r"/(?:[^/]+/posts|groups/[^/]+/(?:permalink|posts))/(?:[0-9]+|pfbid[A-Za-z0-9]+)", path):
        return f"{root}{path}/"
    raise ValueError(VIDEO_LINK_ERROR)


def parse_time(value: str) -> float | None:
    value = value.strip().replace(",", ".")
    if not value:
        return None
    if not re.fullmatch(r"\d+(?::\d{1,2}){0,2}(?:\.\d{1,3})?", value):
        raise ValueError("Укажите время как 1:45, 01:02:30 или число секунд.")
    parts = [float(part) for part in value.split(":")]
    if len(parts) > 1 and any(part >= 60 for part in parts[1:]):
        raise ValueError("Секунды и минуты после двоеточия должны быть меньше 60.")
    result = 0.0
    for part in parts:
        result = result * 60 + part
    if not math.isfinite(result):
        raise ValueError("Некорректный таймкод.")
    return result


def format_time(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def validate_range(start: str, end: str, duration: float | None) -> tuple[float, float | None]:
    first = parse_time(start) or 0.0
    last = parse_time(end)
    if duration is not None:
        if first >= duration:
            raise ValueError("Начало фрагмента должно быть раньше конца видео.")
        if last is not None and last > duration + 0.05:
            raise ValueError(f"Конец фрагмента выходит за длительность видео ({format_time(duration)}).")
    if last is not None and last <= first:
        raise ValueError("Конец фрагмента должен быть позже начала.")
    return first, last


def available_heights(formats: list[dict]) -> list[int]:
    return sorted({int(f["height"]) for f in formats
                   if f.get("height") and f.get("vcodec") != "none"
                   and f.get("has_drm") is not True}, reverse=True)


def format_selector(height: int | None, container: str, audio: bool, *, allow_silent: bool = False) -> str:
    if audio:
        return "bestaudio/best"
    limit = f"[height<={height}]" if height else ""
    extension = "[ext=webm]" if container == "webm" else ""
    video = f"bestvideo{extension}{limit}"
    selector = f"{video}+bestaudio{extension}/best{extension}{limit}"
    return f"{selector}/{video}" if allow_silent else selector


def find_ffmpeg() -> Path:
    bundled = resource_root() / "tools" / "ffmpeg.exe"
    if bundled.is_file():
        return bundled
    import imageio_ffmpeg
    return Path(imageio_ffmpeg.get_ffmpeg_exe())


def find_node() -> str | None:
    bundled = resource_root() / "tools" / "node.exe"
    return str(bundled) if bundled.is_file() else shutil.which("node")


@dataclass(frozen=True)
class DownloadRequest:
    url: str
    directory: str
    audio: bool = False
    container: str = "mp4"
    height: int | None = None
    trim: bool = False
    start: str = ""
    end: str = ""

    def validate(self, duration: float | None = None) -> tuple[float, float | None]:
        normalize_url(self.url)
        choices = {"mp3", "m4a", "wav", "opus"} if self.audio else {"mp4", "mkv", "webm"}
        if self.container not in choices:
            raise ValueError("Выберите поддерживаемый формат файла.")
        if self.height is not None and (type(self.height) is not int or self.height <= 0):
            raise ValueError("Некорректное разрешение видео.")
        if not self.directory.strip():
            raise ValueError("Выберите папку для сохранения.")
        return validate_range(self.start, self.end, duration) if self.trim else (0.0, None)


def unique_destination(directory: Path, filename: str) -> Path:
    candidate = directory / filename
    stem, suffix = candidate.stem, candidate.suffix
    index = 2
    while candidate.exists():
        candidate = directory / f"{stem} ({index}){suffix}"
        index += 1
    return candidate


def friendly_error(message: str) -> str:
    plain = re.sub(r"\x1b\[[0-9;]*m", "", message).removeprefix("ERROR: ").strip()
    low = plain.lower()
    if any(term in low for term in ("sign in", "log in", "login required", "login page",
                                    "confirm you’re not a bot", "confirm you're not a bot")):
        return "Сайт запросил вход или ограничил доступ к ролику. Попробуйте другую публичную ссылку или повторите позже.\n\n" + plain
    if "private video" in low or "private post" in low:
        return "Это закрытое видео. Нужен ролик с открытым доступом."
    if "unsupported url" in low:
        return "Не удалось открыть ролик по этой ссылке. Скопируйте прямую ссылку на видео.\n\n" + plain
    if "requested format" in low:
        return "Выбранное сочетание качества и формата недоступно. Попробуйте MP4 или другое качество."
    if "not available" in low or "unavailable" in low or "removed" in low:
        return "Видео недоступно, удалено или ограничено в вашем регионе.\n\n" + plain
    if any(term in low for term in ("getaddrinfo", "name resolution", "failed to resolve", "nodename nor servname")):
        return "Не удалось определить адрес сайта (ошибка DNS). Доступ к сети может быть ограничен для этого запуска приложения.\n\n" + plain
    if any(term in low for term in ("certificate verify failed", "certificate_verify_failed", "sslerror", "ssl: certificate")):
        return "Не удалось проверить сертификат HTTPS. Проверьте дату Windows и настройки HTTPS в вашей сети.\n\n" + plain
    if "proxy" in low and any(term in low for term in ("error", "failed", "refused", "unable")):
        return "Не удалось подключиться через настроенный прокси. Проверьте доступность прокси или VPN.\n\n" + plain
    if "403" in low or "forbidden" in low:
        return "Сайт ограничил доступ к видео (HTTP 403).\n\n" + plain
    if "429" in low or "too many requests" in low:
        return "Сайт временно ограничил запросы (HTTP 429). Подождите немного и повторите загрузку.\n\n" + plain
    if "timed out" in low or "timeout" in low:
        return "Сервер не ответил вовремя. Повторите попытку.\n\n" + plain
    if "connection" in low and any(term in low for term in ("refused", "reset", "aborted", "unreachable")):
        return "Соединение с сайтом было прервано или отклонено.\n\n" + plain
    return plain or "Не удалось завершить загрузку. Попробуйте ещё раз."
