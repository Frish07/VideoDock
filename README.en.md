# VideoDock

[Документация на русском](README.md)

A Windows 10/11 desktop YouTube downloader with Russian and English interfaces.

## Run the app

In the project folder, open `dist/VideoDock/VideoDock.exe` or `Запустить VideoDock.cmd`. If you have `VideoDock-Windows.zip`, extract the entire archive and run `VideoDock/VideoDock.exe`. The portable build includes Python, FFmpeg, Node.js and the required libraries. Keep the entire `VideoDock` folder, including `_internal`, when moving it to another computer.

## Choose the language

Use the **Язык / Language** selector at the bottom of the sidebar to choose **Русский** or **English**. The interface updates immediately and remembers your choice. You can switch during a download without resetting the link, quality, timestamps, destination or progress. Russian is the default language.

The app's pages, hints, statuses and errors are translated. Video titles, file paths and technical extractor messages keep their original text. Native Windows dialogs follow Windows' own language settings.

## Download a video or audio

1. Paste a YouTube link or drag it into the window, then click **Find video**.
2. Choose **Video with audio** or **Audio only**, the quality and file format.
3. To save a clip, enable **Download only part of the video** and enter a start and end, such as `1:45` and `6:50`. Hours, minutes, seconds and fractional seconds are supported. A blank start means 0:00; a blank end means the end of the video.
4. Choose a folder and click **Download**. The default is your system **Downloads** folder. Other folders are remembered.

After downloading, open the file or its folder. The **Downloads** page shows the last 30 successful downloads. Existing files are preserved by adding a number to the new filename. Canceling stops the worker and FFmpeg and removes the current operation's temporary files.

## Quality and formats

- **Original / best** selects the highest available resolution. A selected resolution is an upper limit: the chosen resolution or the closest available lower one is used. YouTube's lowest standard option is usually 144p.
- **MP4** uses H.264 video and AAC audio (mono or stereo) for playback in built-in players. Full downloads copy compatible tracks and convert the others automatically while retaining the resolution.
- **MKV** supports the broadest set of source streams. **WebM** uses source streams compatible with that container.
- Audio: **MP3 at 192 kbps, M4A, WAV, Opus**. M4A and Opus keep the source codec when possible; otherwise the audio is converted. WAV does not improve the source's quality.
- Clips use FFmpeg with precise trimming and re-encoding. High resolutions and long clips can take longer to process. Depending on the media server, more data than the clip itself may be transferred.
- Progress is shown per stream. Video and audio may be downloaded in sequence; trimming and merging show an activity indicator and elapsed time.

Ongoing live streams, private videos and paid content are not supported. YouTube may require sign-in or restrict a network. Open **Log** for details. The app does not automatically read browser cookies. Download content you are entitled to save.

## Run from source

Requires Python 3.10+ (tested with 3.13) and Node.js 22+ on PATH.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

FFmpeg is provided by `imageio-ffmpeg`. Settings and history are stored under `%LOCALAPPDATA%/VideoDock/VideoDock/settings.json`; Qt determines the exact location. The `language` setting is `ru` or `en`. The most recent error is saved alongside the settings in `last-error.log`. Unexpected startup errors are saved to `startup-error.log`.

Temporary media files use a `.videodock-*` folder in the selected destination and are removed on completion or cancellation. After an operating-system crash, leftover temporary folders can be removed manually.

## Build and test

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe build.py
```

`build.py` produces `dist/VideoDock` and checks that the packaged interface starts and switches between Russian and English. Supply a specific Node executable with `--node C:\path\node.exe`. Dependencies are pinned in the requirements files; if YouTube changes, update `yt-dlp[default]` with its matching EJS package, test and rebuild.

Source layout: `videodock/gui.py` provides the interface and process control, `i18n.py` contains translations, `core.py` validates input and chooses formats, and `worker.py` runs downloads in a separate process using JSONL events. Final files are published only after processing succeeds.
