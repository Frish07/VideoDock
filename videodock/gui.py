from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (QProcess, QProcessEnvironment, QStandardPaths,
                            Qt, QTimer, QUrl)
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QIcon, QPainter,
                           QPainterPath, QPixmap)
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox,
                               QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QProgressBar, QPushButton,
                               QScrollArea, QSizePolicy, QStackedWidget, QTextEdit,
                               QVBoxLayout, QWidget)

from .core import DownloadRequest, format_time, normalize_url, resource_root, validate_range
from .style import STYLE
from . import __version__


def label(text, kind="", wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setObjectName(kind)
    widget.setWordWrap(wrap)
    return widget


def button(text, kind="", callback=None):
    widget = QPushButton(text)
    widget.setObjectName(kind)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if callback:
        widget.clicked.connect(callback)
    return widget


def card(title=None):
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(10)
    if title:
        layout.addWidget(label(title, "cardTitle"))
    return frame, layout


def make_logo(size=48):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#77e0b5"))
    painter.drawRoundedRect(1, 1, size - 2, size - 2, size * .26, size * .26)
    path = QPainterPath()
    path.moveTo(size * .39, size * .27)
    path.lineTo(size * .72, size * .5)
    path.lineTo(size * .39, size * .73)
    path.closeSubpath()
    painter.setBrush(QColor("#142a20"))
    painter.drawPath(path)
    painter.end()
    return pixmap


class Store:
    def __init__(self):
        config = os.environ.get("VIDEODOCK_CONFIG_DIR") or QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
        self.path = Path(config) / "settings.json"
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.data = data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            self.data = {}

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_name("settings.tmp")
            temp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            temp.replace(self.path)
        except OSError:
            pass

    def save_error(self, message, url, journal):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            content = f"VideoDock {__version__}\n{datetime.now().isoformat(timespec='seconds')}\n{url}\n\n{message}\n\n{journal}\n"
            self.path.with_name("last-error.log").write_text(content, encoding="utf-8")
        except OSError:
            pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoDock — YouTube загрузчик")
        self.setWindowIcon(QIcon(make_logo(128)))
        self.resize(1120, 850)
        self.setMinimumSize(900, 660)
        self.setAcceptDrops(True)
        self.store = Store()
        self.metadata = None
        self.active_action = None
        self.process = None
        self.tempdir = None
        self.staging = None
        self.event_offset = 0
        self.event_pending = b""
        self.cancelled = False
        self.failed = False
        self.succeeded = False
        self.pending_download = False
        self.pending_close = False
        self.latest_file = None
        self.operation_started = 0
        self.last_status = "Вставьте ссылку, чтобы начать."
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.poll_events)
        self.build_ui()
        self.update_summary()

    def build_ui(self):
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.setCentralWidget(root)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(184)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(17, 28, 17, 24)
        side.setSpacing(8)
        logo = label("")
        logo.setPixmap(make_logo(40))
        side.addWidget(logo)
        side.addSpacing(5)
        side.addWidget(label("VideoDock", "brand"))
        side.addWidget(label("Сохраняй любимое.", "small"))
        side.addSpacing(30)
        side.addWidget(label("БИБЛИОТЕКА", "eyebrow"))
        side.addSpacing(6)
        navs = QButtonGroup(self)
        for index, text in enumerate(["↓   Скачать", "▤   Загрузки", "ⓘ   О приложении"]):
            nav = button(text, "nav")
            nav.setCheckable(True)
            nav.setChecked(index == 0)
            nav.clicked.connect(lambda checked=False, i=index: self.show_page(i))
            navs.addButton(nav)
            side.addWidget(nav)
        side.addStretch()
        side.addWidget(label("●  Локальное приложение", "small"))
        side.addWidget(label(f"Версия {__version__}", "small"))
        outer.addWidget(sidebar)
        self.pages = QStackedWidget()
        outer.addWidget(self.pages, 1)
        page = QWidget()
        page.setObjectName("workspace")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(26, 18, 26, 18)
        layout.setSpacing(12)
        heading = QHBoxLayout()
        heading_text = QVBoxLayout()
        heading_text.setSpacing(4)
        heading_text.addWidget(label("Новая загрузка", "heading"))
        heading_text.addWidget(label("Целое видео, нужный момент или только звук — в пару кликов.", "muted"))
        heading.addLayout(heading_text, 1)
        heading.addWidget(label("YouTube", "badge"), 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(heading)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        body.setObjectName("workspace")
        content = QVBoxLayout(body)
        content.setContentsMargins(0, 0, 6, 0)
        content.setSpacing(12)

        self.source_card, source = card("01   Ссылка на видео")
        row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setAccessibleName("Ссылка на YouTube")
        self.url.setPlaceholderText("Вставьте ссылку youtube.com или youtu.be…")
        self.url.setClearButtonEnabled(True)
        self.url.textChanged.connect(self.url_changed)
        self.url.returnPressed.connect(self.inspect)
        self.paste_button = button("Вставить", callback=self.paste_url)
        self.inspect_button = button("Найти видео", callback=self.inspect)
        row.addWidget(self.url, 1)
        row.addWidget(self.paste_button)
        row.addWidget(self.inspect_button)
        source.addLayout(row)
        self.preview = QFrame()
        self.preview.setObjectName("preview")
        preview = QHBoxLayout(self.preview)
        preview.setContentsMargins(10, 10, 14, 10)
        preview.setSpacing(16)
        self.thumbnail = label("▶")
        self.thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail.setFixedSize(112, 63)
        self.thumbnail.setStyleSheet("background:#24382f; color:#8ee8c1; border-radius:8px; font-size:27px;")
        preview.addWidget(self.thumbnail)
        details = QVBoxLayout()
        details.setSpacing(6)
        self.video_title = label("Здесь появится ваше видео", "cardTitle", True)
        self.video_title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.video_details = label("Вставьте ссылку и нажмите «Найти видео».", "muted", True)
        details.addWidget(self.video_title)
        details.addWidget(self.video_details)
        preview.addLayout(details, 1)
        source.addWidget(self.preview)
        content.addWidget(self.source_card)

        options_row = QHBoxLayout()
        options_row.setSpacing(16)
        self.format_card, fmt = card("02   Что скачать")
        mode = QHBoxLayout()
        self.video_mode = button("▣  Видео со звуком", "segment")
        self.audio_mode = button("♫  Только аудио", "segment")
        self.mode_group = QButtonGroup(self)
        for btn in [self.video_mode, self.audio_mode]:
            btn.setCheckable(True)
            self.mode_group.addButton(btn)
            mode.addWidget(btn)
            btn.clicked.connect(self.mode_changed)
        self.video_mode.setChecked(True)
        fmt.addLayout(mode)
        fields = QHBoxLayout()
        fields.setSpacing(14)
        quality_col = QVBoxLayout()
        quality_col.addWidget(label("Качество", "muted"))
        self.quality = QComboBox()
        self.quality.setAccessibleName("Качество видео")
        self.quality.addItem("Исходное / лучшее", None)
        self.quality.currentIndexChanged.connect(self.update_summary)
        quality_col.addWidget(self.quality)
        container_col = QVBoxLayout()
        container_col.addWidget(label("Формат файла", "muted"))
        self.container = QComboBox()
        self.container.setAccessibleName("Формат файла")
        self.container.addItems(["MP4", "MKV", "WEBM"])
        self.container.currentIndexChanged.connect(self.update_summary)
        container_col.addWidget(self.container)
        fields.addLayout(quality_col, 3)
        fields.addLayout(container_col, 2)
        fmt.addLayout(fields)
        self.quality_hint = label("Разрешения от 144p — после проверки ссылки.", "small", True)
        fmt.addWidget(self.quality_hint)
        options_row.addWidget(self.format_card, 6)
        self.trim_card, trim = card("03   Нужный фрагмент")
        self.trim = QCheckBox("Скачать только часть видео")
        self.trim.toggled.connect(self.trim_changed)
        trim.addWidget(self.trim)
        times = QHBoxLayout()
        times.setSpacing(12)
        for key, title, placeholder in [("start", "Начало", "0:00"), ("end", "Конец", "До конца")]:
            col = QVBoxLayout()
            col.addWidget(label(title, "muted"))
            entry = QLineEdit()
            entry.setPlaceholderText(placeholder)
            entry.setAccessibleName(f"{title} фрагмента")
            entry.setEnabled(False)
            entry.textChanged.connect(self.update_summary)
            col.addWidget(entry)
            setattr(self, key, entry)
            times.addLayout(col)
        trim.addLayout(times)
        self.trim_hint = label("Например, 1:45 → 6:50. Пустой конец — до конца ролика.", "small", True)
        trim.addWidget(self.trim_hint)
        options_row.addWidget(self.trim_card, 5)
        content.addLayout(options_row)

        self.folder_card, folder = card("04   Куда сохранить")
        folder_row = QHBoxLayout()
        downloads = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation) or str(Path.home() / "Downloads")
        self.directory = QLineEdit(self.store.data.get("directory") or downloads)
        self.directory.setAccessibleName("Папка сохранения")
        self.directory.textChanged.connect(self.update_summary)
        folder_row.addWidget(self.directory, 1)
        self.browse_button = button("Выбрать папку…", callback=self.choose_folder)
        folder_row.addWidget(self.browse_button)
        folder.addLayout(folder_row)
        self.directory.setToolTip("По умолчанию — «Загрузки». Выбранная папка запоминается.")
        content.addWidget(self.folder_card)
        content.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        self.status_card, status = card()
        status.setSpacing(10)
        top = QHBoxLayout()
        self.status_label = label(self.last_status, "status", True)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.elapsed = label("", "small")
        top.addWidget(self.status_label, 1)
        top.addWidget(self.elapsed)
        self.log_button = button("Журнал", "textButton", self.toggle_log)
        top.addWidget(self.log_button)
        status.addLayout(top)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        status.addWidget(self.progress)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(250)
        self.log.setMaximumHeight(100)
        self.log.hide()
        status.addWidget(self.log)
        self.open_file = button("Открыть файл", "textButton", self.open_latest)
        self.open_file.hide()
        self.open_folder = button("Открыть папку", "textButton", self.open_latest_folder)
        self.open_folder.hide()
        links = QHBoxLayout()
        links.addWidget(self.open_file)
        links.addWidget(self.open_folder)
        links.addStretch()
        status.addLayout(links)
        layout.addWidget(self.status_card)
        action = QHBoxLayout()
        self.summary = label("", "muted", True)
        action.addWidget(self.summary, 1)
        self.cancel_button = button("Отменить", callback=self.cancel)
        self.cancel_button.hide()
        action.addWidget(self.cancel_button)
        self.download_button = button("↓  Скачать", "primary", self.start_download)
        self.download_button.setMinimumWidth(165)
        action.addWidget(self.download_button)
        layout.addLayout(action)
        self.pages.addWidget(page)
        self.history_page = QWidget()
        self.history_page.setObjectName("workspace")
        self.history_layout = QVBoxLayout(self.history_page)
        self.history_layout.setContentsMargins(30, 30, 30, 25)
        self.history_layout.setSpacing(18)
        self.pages.addWidget(self.history_page)
        about = QWidget()
        about.setObjectName("workspace")
        about_layout = QVBoxLayout(about)
        about_layout.setContentsMargins(36, 35, 36, 35)
        about_layout.addWidget(label("О VideoDock", "heading"))
        about_card, about_text = card("Видео и звук, которые всегда под рукой")
        about_text.addWidget(label("1. Вставьте ссылку на видео или перетащите её в окно.\n2. Нажмите «Найти видео» и выберите качество.\n3. При желании задайте фрагмент и нажмите «Скачать».", "status", True))
        about_text.addWidget(label("Видео: MP4, MKV, WebM. Аудио: MP3, M4A, WAV, Opus.\nИсходное качество — максимальное из доступных у ролика. Формат MP4 сохраняет исходные кодеки; совместимость зависит от проигрывателя. WAV занимает больше места, но не повышает качество источника.", "muted", True))
        about_text.addWidget(label("Для фрагментов используется точная обрезка с перекодированием: это может занять время. Прямые эфиры, закрытые ролики и платный контент не поддерживаются. YouTube иногда ограничивает загрузки из отдельных сетей.", "muted", True))
        about_text.addWidget(label("Настройки и список последних файлов хранятся на этом компьютере. Видео загружаются напрямую с YouTube.\nОснова приложения: yt-dlp, FFmpeg, Qt for Python и Node.js.", "muted", True))
        about_layout.addWidget(about_card)
        about_layout.addStretch()
        about_layout.addWidget(label(f"VideoDock {__version__}", "small"))
        self.pages.addWidget(about)

    def show_page(self, index):
        if index == 1:
            self.render_history()
        self.pages.setCurrentIndex(index)

    def render_history(self):
        while self.history_layout.count():
            item = self.history_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.history_layout.addWidget(label("Загрузки", "heading"))
        self.history_layout.addWidget(label("Последние 30 файлов, сохранённых через VideoDock.", "muted"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        inner.setObjectName("workspace")
        rows = QVBoxLayout(inner)
        rows.setContentsMargins(0, 0, 6, 0)
        rows.setSpacing(12)
        history = self.store.data.get("history", [])
        if not isinstance(history, list):
            history = []
        if not history:
            empty, empty_layout = card("Здесь пока пусто")
            empty_layout.addWidget(label("Скачайте первый ролик — и он появится здесь.", "muted"))
            rows.addWidget(empty)
        for entry in history[:30]:
            if not isinstance(entry, dict) or not entry.get("path"):
                continue
            frame, row = card()
            row.addWidget(label(entry.get("title", "Видео"), "cardTitle", True))
            path = entry["path"]
            row.addWidget(label(path, "small", True))
            bottom = QHBoxLayout()
            bottom.addWidget(label(f"{entry.get('container', '').upper()}  ·  {self.size_text(entry.get('size'))}  ·  {entry.get('date', '')}", "muted"), 1)
            open_btn = button("Открыть", callback=lambda checked=False, p=path: self.open_path(p))
            open_btn.setEnabled(Path(path).is_file())
            bottom.addWidget(open_btn)
            bottom.addWidget(button("Папка", callback=lambda checked=False, p=path: self.open_path(str(Path(p).parent))))
            row.addLayout(bottom)
            rows.addWidget(frame)
        rows.addStretch()
        scroll.setWidget(inner)
        self.history_layout.addWidget(scroll, 1)

    def paste_url(self):
        self.url.setText(QApplication.clipboard().text().strip())
        if self.url.text():
            self.inspect()

    def url_changed(self):
        self.metadata = None
        self.video_title.setText("Здесь появится ваше видео")
        self.video_details.setText("Нажмите «Найти видео», чтобы выбрать доступное качество.")
        self.thumbnail.clear()
        self.thumbnail.setText("▶")
        self.quality.clear()
        self.quality.addItem("Исходное / лучшее", None)
        self.update_summary()

    def mode_changed(self):
        selected = self.container.currentText()
        self.container.blockSignals(True)
        self.container.clear()
        audio = self.audio_mode.isChecked()
        self.container.addItems(["MP3", "M4A", "WAV", "OPUS"] if audio else ["MP4", "MKV", "WEBM"])
        if selected in [self.container.itemText(i) for i in range(self.container.count())]:
            self.container.setCurrentText(selected)
        self.container.blockSignals(False)
        self.quality.setEnabled(not audio)
        self.quality_hint.setText("MP3 — 192 кбит/с. M4A и Opus — исходный звук, когда доступен." if audio else "Скачивается выбранное разрешение или ближайшее доступное ниже.")
        self.update_summary()

    def trim_changed(self, checked):
        self.start.setEnabled(checked)
        self.end.setEnabled(checked)
        self.update_summary()

    def update_summary(self, *args):
        if not hasattr(self, "summary"):
            return
        audio = self.audio_mode.isChecked()
        text = f"{'Аудио' if audio else self.quality.currentText()}  ·  {self.container.currentText()}"
        if self.trim.isChecked():
            try:
                start, end = validate_range(self.start.text(), self.end.text(), (self.metadata or {}).get("duration"))
                text += f"  ·  {format_time(start)} → {format_time(end) if end is not None else 'конец'}"
                duration = end - start if end is not None else None
                self.trim_hint.setText(f"Длительность фрагмента: {format_time(duration)}" if duration is not None else "Пустой конец — до конца ролика. Точная обрезка включена.")
                self.trim_hint.setObjectName("small")
            except ValueError as exc:
                self.trim_hint.setText(str(exc))
                self.trim_hint.setObjectName("error")
            self.trim_hint.style().unpolish(self.trim_hint)
            self.trim_hint.style().polish(self.trim_hint)
        else:
            self.trim_hint.setText("Например, 1:45 → 6:50. Пустой конец — до конца ролика.")
            self.trim_hint.setObjectName("small")
            self.trim_hint.style().unpolish(self.trim_hint)
            self.trim_hint.style().polish(self.trim_hint)
        self.summary.setText(text)

    def choose_folder(self):
        selected = QFileDialog.getExistingDirectory(self, "Куда сохранить файл", self.directory.text())
        if selected:
            self.directory.setText(selected)
            self.remember_directory()

    def remember_directory(self):
        self.store.data["directory"] = self.directory.text().strip()
        self.store.save()

    def set_status(self, text, kind="status"):
        self.last_status = text
        # Long extractor diagnostics belong in the expandable log.
        self.status_label.setText(text.split("\n\n")[0][:420])
        self.status_label.setToolTip(text)
        self.status_label.setObjectName(kind)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def report_error(self, message):
        self.failed = True
        self.pending_download = False
        self.log.append(message)
        self.store.save_error(message, self.url.text(), self.log.toPlainText())
        self.set_status(message, "error")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

    def set_busy(self, busy):
        for widget in [self.source_card, self.format_card, self.trim_card, self.folder_card]:
            widget.setEnabled(not busy)
        self.download_button.setEnabled(not busy)
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText("Отменить")

    def inspect(self):
        if self.active_action:
            return
        try:
            url = normalize_url(self.url.text())
        except ValueError as exc:
            self.report_error(str(exc))
            return
        self.start_job({"action": "inspect", "url": url})

    def request(self):
        return DownloadRequest(url=normalize_url(self.url.text()), directory=self.directory.text().strip(),
                               audio=self.audio_mode.isChecked(), container=self.container.currentText().lower(),
                               height=self.quality.currentData(), trim=self.trim.isChecked(),
                               start=self.start.text(), end=self.end.text())

    def start_download(self):
        if self.active_action:
            return
        try:
            request = self.request()
            request.validate((self.metadata or {}).get("duration"))
        except ValueError as exc:
            self.report_error(str(exc))
            return
        if not self.metadata or self.metadata.get("url") != request.url:
            self.pending_download = True
            self.inspect()
            return
        self.remember_directory()
        staging = Path(request.directory).expanduser().resolve() / f".videodock-{uuid.uuid4().hex}"
        self.start_job({"action": "download", "request": asdict(request), "staging": str(staging)})

    def start_job(self, job):
        self.cleanup_job()
        try:
            self.tempdir = tempfile.TemporaryDirectory(prefix="videodock-")
            workdir = Path(self.tempdir.name)
            jobpath = workdir / "job.json"
            jobpath.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            self.report_error(f"Не удалось создать временные файлы. Проверьте свободное место и доступ к папке.\n\n{exc}")
            self.cleanup_job()
            return
        self.staging = Path(job["staging"]) if job.get("staging") else None
        self.active_action = job["action"]
        self.cancelled = self.failed = self.succeeded = False
        self.event_offset = 0
        self.event_pending = b""
        self.operation_started = time.monotonic()
        self.open_file.hide()
        self.open_folder.hide()
        self.log.clear()
        self.set_busy(True)
        self.progress.setRange(0, 0)
        self.set_status("Получаем информацию о видео…" if job["action"] == "inspect" else "Подготавливаем загрузку…")
        self.process = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(env)
        self.process.setProgram(sys.executable)
        args = ["--worker", str(jobpath)]
        if not getattr(sys, "frozen", False):
            args.insert(0, str(resource_root() / "app.py"))
        self.process.setArguments(args)
        self.process.finished.connect(self.job_finished)
        self.process.errorOccurred.connect(self.process_error)
        self.process.start()
        self.timer.start()

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.report_error("Не удалось запустить процесс загрузки. Перезапустите приложение.")
            self.job_finished(-1, QProcess.ExitStatus.CrashExit)

    def poll_events(self):
        if not self.tempdir:
            return
        eventfile = Path(self.tempdir.name) / "events.jsonl"
        try:
            with eventfile.open("rb") as stream:
                stream.seek(self.event_offset)
                data = stream.read()
                self.event_offset = stream.tell()
            self.event_pending += data
            while b"\n" in self.event_pending:
                line, self.event_pending = self.event_pending.split(b"\n", 1)
                try:
                    self.handle_event(json.loads(line))
                except (ValueError, KeyError):
                    continue
        except FileNotFoundError:
            pass
        if self.active_action:
            self.elapsed.setText(format_time(time.monotonic() - self.operation_started))

    def handle_event(self, event):
        kind = event["event"]
        if kind in {"log", "warning"}:
            self.log.append(event.get("message", ""))
        elif kind == "status":
            self.set_status(event["message"])
            self.progress.setRange(0, 0)
        elif kind == "metadata":
            self.succeeded = True
            self.metadata = event
            self.video_title.setText(event["title"])
            heights = event.get("heights", [])
            top = f"  ·  до {heights[0]}p" if heights else ""
            self.video_details.setText(f"{event['channel']}  ·  {format_time(event.get('duration'))}{top}")
            pix = QPixmap(event.get("thumbnail", ""))
            if not pix.isNull():
                self.thumbnail.setPixmap(pix.scaled(self.thumbnail.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.quality.clear()
            self.quality.addItem("Исходное / лучшее", None)
            for height in heights:
                self.quality.addItem(f"{height}p" + ("  ·  4K" if height == 2160 else "  ·  8K" if height == 4320 else ""), height)
            self.quality_hint.setText("Доступные разрешения этого ролика." if not self.audio_mode.isChecked() else "MP3 — 192 кбит/с. M4A и Opus — исходный звук, когда доступен.")
            self.set_status("Видео найдено. Выберите параметры и нажмите «Скачать».", "success")
            self.update_summary()
        elif kind == "progress":
            percent = event.get("percent")
            if percent is not None:
                self.progress.setRange(0, 100)
                self.progress.setValue(int(percent))
            else:
                self.progress.setRange(0, 0)
            text = f"Скачиваем поток: {self.size_text(event.get('downloaded'))}"
            if event.get("total"):
                text += f" / {self.size_text(event['total'])}  ·  {percent:.0f}%"
            if event.get("speed"):
                text += f"  ·  {self.size_text(event['speed'])}/с"
            if event.get("eta") is not None:
                text += f"  ·  осталось {format_time(event['eta'])}"
            self.set_status(text)
        elif kind == "error":
            self.report_error(event["message"])
        elif kind == "complete":
            self.succeeded = True
            self.latest_file = event["path"]
            self.set_status(f"Готово! Файл сохранён · {self.size_text(event.get('size'))}", "success")
            self.progress.setRange(0, 100)
            self.progress.setValue(100)
            self.open_file.show()
            self.open_folder.show()
            history = self.store.data.get("history", [])
            if not isinstance(history, list):
                history = []
            entry = {key: event.get(key) for key in ["path", "title", "size", "container", "audio", "start", "end"]}
            entry["date"] = datetime.now().strftime("%d.%m.%Y %H:%M")
            self.store.data["history"] = [entry, *history][:30]
            self.store.save()

    def job_finished(self, exit_code, exit_status):
        self.poll_events()
        self.timer.stop()
        action = self.active_action
        self.active_action = None
        if self.cancelled and not self.succeeded:
            self.set_status("Загрузка отменена. Можно изменить параметры и начать снова.")
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
        elif not self.succeeded and not self.failed:
            self.report_error("Процесс загрузки завершился неожиданно. Откройте журнал или повторите попытку.")
        elif action == "inspect" and self.succeeded:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
        self.set_busy(False)
        pending = self.pending_download and self.succeeded and not self.cancelled and not self.failed
        self.pending_download = False
        self.cleanup_job()
        if self.pending_close:
            QTimer.singleShot(0, self.close)
        elif pending:
            QTimer.singleShot(0, self.start_download)

    def cleanup_job(self):
        if self.process is not None and self.process.state() != QProcess.ProcessState.NotRunning:
            return
        if self.staging and self.staging.name.startswith(".videodock-"):
            shutil.rmtree(self.staging, ignore_errors=True)
            self.staging = None
        if self.tempdir:
            try:
                self.tempdir.cleanup()
            except OSError:
                pass
            self.tempdir = None
        if self.process:
            self.process.deleteLater()
            self.process = None

    def cancel(self):
        if not self.process or not self.active_action:
            return
        self.cancelled = True
        self.pending_download = False
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Отмена…")
        self.set_status("Останавливаем загрузку…")
        pid = self.process.processId()
        if os.name == "nt" and pid:
            # Stop only this worker and its descendants, including FFmpeg.
            self.killer = QProcess(self)
            victim = self.process
            def ensure_stopped(*_):
                if self.process is victim and victim.state() != QProcess.ProcessState.NotRunning:
                    victim.kill()
            self.killer.finished.connect(ensure_stopped)
            self.killer.finished.connect(self.killer.deleteLater)
            self.killer.start("taskkill.exe", ["/PID", str(pid), "/T", "/F"])
            QTimer.singleShot(4000, ensure_stopped)
        else:
            self.process.kill()

    def toggle_log(self):
        self.log.setVisible(not self.log.isVisible())
        self.log_button.setText("Скрыть журнал" if self.log.isVisible() else "Журнал")

    @staticmethod
    def size_text(size):
        value = float(size or 0)
        for unit in ["Б", "КБ", "МБ", "ГБ"]:
            if value < 1024 or unit == "ГБ":
                return f"{value:.1f} {unit}" if unit != "Б" else f"{value:.0f} Б"
            value /= 1024

    def open_path(self, path):
        if not Path(path).exists():
            self.set_status("Этот файл или папка больше не существует.", "error")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).resolve())))

    def open_latest(self):
        if self.latest_file:
            self.open_path(self.latest_file)

    def open_latest_folder(self):
        if self.latest_file:
            self.open_path(str(Path(self.latest_file).parent))

    def dragEnterEvent(self, event):
        if not self.active_action and (event.mimeData().hasUrls() or event.mimeData().hasText()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if self.active_action:
            return
        mime = event.mimeData()
        text = mime.urls()[0].toString() if mime.hasUrls() else mime.text().strip()
        self.show_page(0)
        self.url.setText(text)
        self.inspect()
        event.acceptProposedAction()

    def closeEvent(self, event):
        if self.active_action:
            self.pending_close = True
            self.cancel()
            event.ignore()
        else:
            self.remember_directory()
            self.cleanup_job()
            event.accept()


def launch(initial_url=None, check_path=None):
    app = QApplication([sys.argv[0]] if initial_url or check_path else sys.argv)
    app.setApplicationName("VideoDock")
    app.setOrganizationName("VideoDock")
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    window = MainWindow()
    available = app.primaryScreen().availableGeometry()
    window.resize(min(1120, available.width() - 30), min(850, available.height() - 45))
    window.show()
    if check_path:
        def check_startup():
            result = {"version": __version__, "frozen": bool(getattr(sys, "frozen", False)),
                      "title": window.windowTitle(), "download_enabled": window.download_button.isEnabled()}
            Path(check_path).write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
            window.close()
        QTimer.singleShot(100, check_startup)
    elif initial_url:
        window.url.setText(initial_url)
        QTimer.singleShot(0, window.inspect)
    return app.exec()
