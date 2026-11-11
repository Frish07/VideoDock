import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QFileDialog, QLabel

from videodock.gui import MainWindow
from videodock.style import STYLE


class LanguageUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyle("Fusion")
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"VIDEODOCK_CONFIG_DIR": self.directory.name})
        self.environment.start()
        self.window = MainWindow()

    def tearDown(self):
        self.window.active_action = None
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.environment.stop()
        self.directory.cleanup()

    def test_selector_switches_live_and_saves_preference(self):
        window = self.window
        window.language_combo.setCurrentIndex(window.language_combo.findData("en"))
        self.assertEqual(window.language, "en")
        self.assertEqual(window.inspect_button.text(), "Find video")
        self.assertEqual(window.trim.text(), "Download only part of the video")
        self.assertEqual(window.url.accessibleName(), "Video link")
        self.assertEqual(window.end.placeholderText(), "Until the end")
        self.assertIn("Choose folder", window.browse_button.text())
        self.assertEqual(json.loads(window.store.path.read_text(encoding="utf-8"))["language"], "en")
        other = MainWindow()
        self.assertEqual(other.language, "en")
        self.assertEqual(other.inspect_button.text(), "Find video")
        other.close()
        other.deleteLater()
        window.set_language("ru")
        self.assertEqual(window.inspect_button.text(), "Найти видео")

    def test_switch_preserves_form_metadata_progress_and_running_job(self):
        window = self.window
        window.url.setText("https://youtu.be/BaW_jenozKc")
        window.directory.setText(str(Path(self.directory.name) / "Моя папка"))
        window.handle_event({"event": "metadata", "title": "Мой ролик", "channel": "Канал",
                             "url": "https://www.youtube.com/watch?v=BaW_jenozKc", "duration": 600,
                             "heights": [1080, 720, 144], "thumbnail": ""})
        window.quality.setCurrentIndex(window.quality.findData(720))
        window.container.setCurrentText("MKV")
        window.trim.setChecked(True)
        window.start.setText("1:45")
        window.end.setText("6:50")
        window.active_action = "download"
        window.set_busy(True)
        window.handle_event({"event": "progress", "downloaded": 1024, "total": 2048,
                             "percent": 50, "speed": 512, "eta": 2})
        before = window.request()
        window.set_language("en")
        self.assertEqual(window.request(), before)
        self.assertEqual(window.active_action, "download")
        self.assertFalse(window.download_button.isEnabled())
        self.assertTrue(window.language_combo.isEnabled())
        self.assertEqual(window.progress.value(), 50)
        self.assertEqual(window.video_title.text(), "Мой ролик")
        self.assertIn("up to 1080p", window.video_details.text())
        self.assertIn("Downloading stream: 1.0 KB", window.last_status)
        self.assertIn("512 B/s", window.last_status)
        self.assertIn("0:02 remaining", window.last_status)
        self.assertEqual(window.trim_hint.text(), "Clip duration: 5:05")
        window.handle_event({"event": "status", "message": "Объединяем видео и звук…"})
        self.assertEqual(window.last_status, "Merging video and audio…")
        window.set_language("ru")
        self.assertEqual(window.request(), before)
        self.assertEqual(window.last_status, "Объединяем видео и звук…")

    def test_errors_and_audio_mode_are_translated(self):
        window = self.window
        window.set_language("en")
        window.audio_mode.click()
        self.assertEqual(window.container.currentText(), "MP3")
        self.assertFalse(window.quality.isEnabled())
        self.assertIn("192 kbps", window.quality_hint.text())
        window.url.setText("https://example.com/not-youtube")
        window.start_download()
        self.assertEqual(window.last_status, "VideoDock supports links from YouTube, TikTok, Instagram and Facebook.")
        window.set_language("ru")
        self.assertEqual(window.last_status, "Поддерживаются ссылки YouTube, TikTok, Instagram и Facebook.")

    def test_history_content_and_about_page_survive_switching(self):
        window = self.window
        window.store.data["history"] = [{"title": "Загрузки", "path": str(Path(self.directory.name) / "Видео.mp4"),
                                          "size": 1048576, "container": "mp4", "date": "08.11.2026 12:00"}]
        window.show_page(1)
        window.set_language("en")
        visible_text = [widget.text() for widget in window.history_page.findChildren(QLabel)]
        self.assertIn("Downloads", visible_text)
        self.assertIn("Загрузки", visible_text)  # A video title is never translated.
        self.assertTrue(any("1.0 MB" in text for text in visible_text))
        window.show_page(2)
        self.assertTrue(any(widget.text() == "About VideoDock" for widget in window.pages.currentWidget().findChildren(QLabel)))
        window.set_language("ru")
        self.assertEqual(window.pages.currentIndex(), 2)

    def test_folder_dialog_uses_the_selected_language(self):
        self.window.set_language("en")
        with patch.object(QFileDialog, "getExistingDirectory", return_value="") as dialog:
            self.window.choose_folder()
        self.assertEqual(dialog.call_args.args[1], "Choose a download folder")


if __name__ == "__main__":
    unittest.main()
