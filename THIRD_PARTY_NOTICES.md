# Компоненты VideoDock

В готовую сборку включены сторонние компоненты. Применимые тексты лицензий Python-пакетов копируются в папку `licenses` при сборке.

| Компонент | Назначение | Лицензия / исходники |
| --- | --- | --- |
| Python | Среда выполнения | PSF, https://www.python.org/psf/license/ |
| Qt for Python / PySide6 / Shiboken | Интерфейс | LGPLv3/GPLv3/commercial, https://code.qt.io/cgit/pyside/pyside-setup.git/ |
| Qt | Графические библиотеки | LGPLv3/GPLv3/commercial, https://code.qt.io/cgit/qt/ |
| yt-dlp | Получение видео | Unlicense и лицензии включённых компонентов, https://github.com/yt-dlp/yt-dlp |
| yt-dlp-ejs | JavaScript-проверки YouTube | https://github.com/yt-dlp/ejs |
| curl-cffi / cffi / pycparser | Сетевые запросы к источникам видео | MIT и лицензии включённых компонентов, https://github.com/lexiforest/curl_cffi |
| imageio-ffmpeg | Поставка FFmpeg | BSD-2-Clause, https://github.com/imageio/imageio-ffmpeg |
| FFmpeg | Объединение, обрезка, конвертация | GPL/LGPL в зависимости от конфигурации; конфигурация доступна через `_internal/tools/ffmpeg.exe -version`. https://ffmpeg.org/legal.html, https://github.com/imageio/imageio-binaries |
| Node.js | Выполнение EJS | MIT и лицензии включённых компонентов, https://github.com/nodejs/node/blob/main/LICENSE |
| Requests / urllib3 / certifi / Brotli / Mutagen / PyCryptodomex / websockets | Сетевые и медиа-зависимости yt-dlp | См. лицензии соответствующих дистрибутивов |

Qt поставляется динамическими библиотеками в `_internal/PySide6`; они не встраиваются статически в код приложения. Исходный код приложения приложен к проекту. Перед публичным распространением сборки необходимо соблюсти условия лицензий всех поставляемых бинарных компонентов, в том числе требования к предоставлению соответствующих исходников FFmpeg/Qt.
