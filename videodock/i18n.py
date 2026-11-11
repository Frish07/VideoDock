"""UI translations. Russian source messages also identify worker/validation errors.

Video titles, paths and extractor diagnostics are user/external content and are
never passed through the UI catalog.
"""
from __future__ import annotations

import re

LANGUAGES = {"ru": "Русский", "en": "English"}

ENGLISH = {
    "VideoDock — Загрузчик видео": "VideoDock — Video Downloader",
    "Сохраняй любимое.": "Keep your favorites.",
    "БИБЛИОТЕКА": "LIBRARY",
    "↓   Скачать": "↓   Download",
    "▤   Загрузки": "▤   Downloads",
    "ⓘ   О приложении": "ⓘ   About",
    "●  Локальное приложение": "●  Desktop app",
    "Версия {version}": "Version {version}",
    "Язык": "Language",
    "Язык интерфейса": "Interface language",
    "Новая загрузка": "New download",
    "Целое видео, нужный момент или только звук — в пару кликов.": "A full video, your favorite moment, or just the audio — in a few clicks.",
    "01   Ссылка на видео": "01   Video link",
    "Ссылка на видео": "Video link",
    "Вставьте ссылку на видео…": "Paste a video link…",
    "Вставить": "Paste",
    "Найти видео": "Find video",
    "Здесь появится ваше видео": "Your video will appear here",
    "Вставьте ссылку и нажмите «Найти видео».": "Paste a link and click “Find video”.",
    "Нажмите «Найти видео», чтобы выбрать доступное качество.": "Click “Find video” to see the available qualities.",
    "02   Что скачать": "02   Download options",
    "▣  Видео со звуком": "▣  Video with audio",
    "♫  Только аудио": "♫  Audio only",
    "Качество": "Quality",
    "Качество видео": "Video quality",
    "Исходное / лучшее": "Original / best",
    "Формат файла": "File format",
    "Доступные разрешения появятся после проверки ссылки.": "Available resolutions appear after checking the link.",
    "Доступные разрешения этого ролика.": "Available resolutions for this video.",
    "Скачивается выбранное разрешение или ближайшее доступное ниже.": "Uses the selected resolution or the closest available lower one.",
    "MP3 при конвертации — 192 кбит/с. Подходящие исходные дорожки копируются.": "MP3 conversion uses 192 kbps. Compatible source audio is copied.",
    "03   Нужный фрагмент": "03   Choose a clip",
    "Скачать только часть видео": "Download only part of the video",
    "Начало": "Start",
    "Конец": "End",
    "Начало фрагмента": "Clip start",
    "Конец фрагмента": "Clip end",
    "До конца": "Until the end",
    "конец": "end",
    "Например, 1:45 → 6:50. Пустой конец — до конца ролика.": "For example, 1:45 → 6:50. Leave the end blank to keep the rest.",
    "Длительность фрагмента: {duration}": "Clip duration: {duration}",
    "Пустой конец — до конца ролика. Точная обрезка включена.": "Leave the end blank to keep the rest. Precise trimming is enabled.",
    "04   Куда сохранить": "04   Save location",
    "Папка сохранения": "Download folder",
    "Выбрать папку…": "Choose folder…",
    "По умолчанию — «Загрузки». Выбранная папка запоминается.": "Defaults to Downloads. Your chosen folder is remembered.",
    "Куда сохранить файл": "Choose a download folder",
    "Журнал": "Log",
    "Скрыть журнал": "Hide log",
    "Открыть файл": "Open file",
    "Открыть папку": "Open folder",
    "Отменить": "Cancel",
    "Отмена…": "Canceling…",
    "↓  Скачать": "↓  Download",
    "Аудио": "Audio",
    "Загрузки": "Downloads",
    "Последние 30 файлов, сохранённых через VideoDock.": "The last 30 files saved with VideoDock.",
    "Здесь пока пусто": "No downloads yet",
    "Скачайте первый ролик — и он появится здесь.": "Download your first video and it will appear here.",
    "Видео": "Video",
    "Открыть": "Open",
    "Папка": "Folder",
    "О VideoDock": "About VideoDock",
    "Видео и звук, которые всегда под рукой": "Your videos and audio, always at hand",
    "1. Вставьте ссылку на видео или перетащите её в окно.\n2. Нажмите «Найти видео» и выберите качество.\n3. При желании задайте фрагмент и нажмите «Скачать».":
        "1. Paste a video link or drag it into the window.\n2. Click “Find video” and choose the quality.\n3. Optionally set a clip, then click “Download”.",
    "Видео: MP4, MKV, WebM. Аудио: MP3, M4A, WAV, Opus.\nИсходное качество выбирает максимальное доступное разрешение. MP4 сохраняется с видео H.264 и звуком AAC для совместимости с проигрывателями. WAV занимает больше места.":
        "Video: MP4, MKV, WebM. Audio: MP3, M4A, WAV, Opus.\nOriginal quality uses the highest available resolution. MP4 uses H.264 video and AAC audio for player compatibility. WAV takes up more space.",
    "Поддерживаются отдельные публичные видео с YouTube, TikTok, Instagram и Facebook. Сайт может запросить вход или ограничить загрузку. Обрезка фрагментов выполняется с перекодированием.":
        "Download individual public videos from YouTube, TikTok, Instagram and Facebook. The site may require sign-in or restrict downloads. Trimming a clip re-encodes it.",
    "Настройки и список последних файлов хранятся на этом компьютере. Видео загружаются напрямую с сайта.\nВ приложении используются yt-dlp, FFmpeg, Qt for Python и Node.js.":
        "Settings and recent downloads are stored on this computer. Videos are downloaded directly from the source site.\nBuilt with yt-dlp, FFmpeg, Qt for Python and Node.js.",
    "до {height}p": "up to {height}p",
    "Б": "B",
    "КБ": "KB",
    "МБ": "MB",
    "ГБ": "GB",
    "Вставьте ссылку, чтобы начать.": "Paste a link to get started.",
    "Получаем информацию о видео…": "Getting video information…",
    "Подготавливаем загрузку…": "Preparing the download…",
    "Видео найдено. Выберите параметры и нажмите «Скачать».": "Video found. Choose your options and click “Download”.",
    "Подключаемся к источнику…": "Connecting to the source…",
    "Скачиваем видео…": "Downloading video…",
    "Скачиваем аудио…": "Downloading audio…",
    "Скачиваем выбранный фрагмент. Точная обрезка может занять время…": "Downloading your clip. Precise trimming may take a while…",
    "Поток получен. Обрабатываем файл…": "Stream downloaded. Processing the file…",
    "Подготавливаем совместимый MP4…": "Preparing a compatible MP4…",
    "Обрабатываем аудио…": "Processing audio…",
    "Объединяем видео и звук…": "Merging video and audio…",
    "Скачиваем поток: {downloaded}": "Downloading stream: {downloaded}",
    "  ·  {speed}/с": "  ·  {speed}/s",
    "  ·  осталось {eta}": "  ·  {eta} remaining",
    "Готово! Файл сохранён · {size}": "Done! File saved · {size}",
    "Останавливаем загрузку…": "Stopping the download…",
    "Загрузка отменена. Можно изменить параметры и начать снова.": "Download canceled. You can change the options and try again.",
    "Не удалось создать временные файлы. Проверьте свободное место и доступ к папке.": "Could not create temporary files. Check free disk space and folder access.",
    "Не удалось запустить процесс загрузки. Перезапустите приложение.": "Could not start the download process. Restart the app.",
    "Процесс загрузки завершился неожиданно. Откройте журнал или повторите попытку.": "The download process stopped unexpectedly. Check the log or try again.",
    "Этот файл или папка больше не существует.": "This file or folder no longer exists.",
    "Вставьте ссылку на видео.": "Paste a video link.",
    "Нужна обычная ссылка https:// на видео.": "Enter a regular https:// link to a video.",
    "Поддерживаются ссылки YouTube, TikTok, Instagram и Facebook.": "VideoDock supports links from YouTube, TikTok, Instagram and Facebook.",
    "Не удалось найти видео в ссылке. Скопируйте ссылку на конкретный ролик.": "No video was found in this link. Copy a link to a specific video.",
    "Укажите время как 1:45, 01:02:30 или число секунд.": "Enter a time such as 1:45, 01:02:30, or a number of seconds.",
    "Секунды и минуты после двоеточия должны быть меньше 60.": "Seconds and minutes after a colon must be less than 60.",
    "Некорректный таймкод.": "Invalid timestamp.",
    "Начало фрагмента должно быть раньше конца видео.": "The clip must start before the video ends.",
    "Конец фрагмента выходит за длительность видео ({duration}).": "The clip end exceeds the video duration ({duration}).",
    "Конец фрагмента должен быть позже начала.": "The clip end must be after its start.",
    "Выберите поддерживаемый формат файла.": "Choose a supported file format.",
    "Некорректное разрешение видео.": "Invalid video resolution.",
    "Выберите папку для сохранения.": "Choose a download folder.",
    "Этот эфир ещё идёт или обрабатывается. Дождитесь публикации записи.": "This stream is still live or being processed. Wait until the recording is published.",
    "Вставьте ссылку на один ролик.": "Paste a link to a single video.",
    "Выбранный путь не является папкой.": "The selected path is not a folder.",
    "Временная папка должна находиться в папке сохранения.": "The temporary folder must be inside the download folder.",
    "Загрузка завершилась без готового файла. Попробуйте другой формат.": "No finished file was produced. Try another format.",
    "Получен пустой файл. Повторите загрузку.": "The downloaded file is empty. Try again.",
    "Не удалось проверить видео и звук в файле MP4.": "Could not verify the video and audio in the MP4 file.",
    "Не удалось подготовить совместимый MP4.": "Could not prepare a compatible MP4 file.",
    "Неизвестная операция.": "Unknown operation.",
    "Сайт запросил вход или ограничил доступ к ролику. Попробуйте другую публичную ссылку или повторите позже.": "The site requires sign-in or has restricted access to this video. Try another public link or try again later.",
    "Это закрытое видео. Нужен ролик с открытым доступом.": "This video is private. Choose a publicly available video.",
    "Не удалось открыть ролик по этой ссылке. Скопируйте прямую ссылку на видео.": "Could not open the video from this link. Copy the direct video link.",
    "Видео недоступно, удалено или ограничено в вашем регионе.": "This video is unavailable, removed or restricted in your region.",
    "Выбранное сочетание качества и формата недоступно. Попробуйте MP4 или другое качество.": "This quality and format combination is unavailable. Try MP4 or a different quality.",
    "Не удалось определить адрес сайта (ошибка DNS). Доступ к сети может быть ограничен для этого запуска приложения.": "Could not resolve the site's address (DNS error). This app session may have restricted network access.",
    "Не удалось проверить сертификат HTTPS. Проверьте дату Windows и настройки HTTPS в вашей сети.": "Could not verify the HTTPS certificate. Check the Windows date and your network's HTTPS settings.",
    "Не удалось подключиться через настроенный прокси. Проверьте доступность прокси или VPN.": "Could not connect through the configured proxy. Check your proxy or VPN connection.",
    "Сайт ограничил доступ к видео (HTTP 403).": "The site restricted access to this video (HTTP 403).",
    "Сайт временно ограничил запросы (HTTP 429). Подождите немного и повторите загрузку.": "The site temporarily limited requests (HTTP 429). Wait a while and try again.",
    "Сервер не ответил вовремя. Повторите попытку.": "The server did not respond in time. Try again.",
    "Соединение с сайтом было прервано или отклонено.": "The connection to the site was interrupted or refused.",
    "Не удалось завершить загрузку. Попробуйте ещё раз.": "Could not finish the download. Try again.",
}


def translate(source: str, language: str = "ru", **values) -> str:
    """Translate an app message; preserve unknown/external diagnostic text."""
    text = ENGLISH.get(source, source) if language == "en" else source
    if values:
        return text.format(**values)
    if language != "en":
        return text
    # Exceptions can arrive from the worker already formatted. Keep raw
    # diagnostics after the first paragraph exactly as the extractor supplied.
    if "\n\n" in source:
        summary, details = source.split("\n\n", 1)
        return translate(summary, language) + "\n\n" + details
    match = re.fullmatch(r"Конец фрагмента выходит за длительность видео \((.+)\)\.", source)
    if match:
        return translate("Конец фрагмента выходит за длительность видео ({duration}).", language, duration=match[1])
    return text
