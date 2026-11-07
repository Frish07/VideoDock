# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files('yt_dlp_ejs') + copy_metadata('yt-dlp') + copy_metadata('yt-dlp-ejs')
a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[('tools/ffmpeg.exe', 'tools'), ('tools/node.exe', 'tools')],
    datas=datas,
    hiddenimports=['yt_dlp_ejs', 'imageio_ffmpeg'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtOpenGL', 'PySide6.QtTest'],
    noarchive=False,
)
# The app already ships its own named FFmpeg in tools; avoid a second 100 MB copy.
a.datas = [item for item in a.datas if not (item[0].startswith('imageio_ffmpeg') and item[0].endswith('.exe'))]
a.binaries = [item for item in a.binaries if not (item[0].startswith('imageio_ffmpeg') and item[0].endswith('.exe'))]
# Qt 6.12 imports Windows' unversioned ICU API. A Poppler installation on the
# build PATH can supply a different icuuc.dll with version-suffixed exports.
# Never shadow the Windows system DLL with that unrelated ICU build.
a.binaries = [item for item in a.binaries if item[0].replace('\\', '/').rsplit('/', 1)[-1].lower() != 'icuuc.dll']
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name='VideoDock', debug=False,
    bootloader_ignore_signals=False, strip=False, upx=False, console=False,
    disable_windowed_traceback=False, icon='assets/videodock.ico',
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='VideoDock')
