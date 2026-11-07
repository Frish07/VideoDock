"""Build a self-contained Windows folder: python build.py [--node PATH]."""
import argparse
import importlib.metadata
import json
import shutil
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    tools = root / "tools"
    tools.mkdir(exist_ok=True)
    import imageio_ffmpeg
    from PySide6.QtWidgets import QApplication
    from videodock.gui import make_logo

    source = Path(imageio_ffmpeg.get_ffmpeg_exe())
    shutil.copy2(source, tools / "ffmpeg.exe")
    node = args.node or (Path(shutil.which("node")) if shutil.which("node") else None)
    if node and node.is_file() and node.resolve() != (tools / "node.exe").resolve():
        shutil.copy2(node, tools / "node.exe")
    if not (tools / "node.exe").is_file():
        raise SystemExit("Node.js 22+ is required. Run build.py --node C:\\path\\to\\node.exe")
    subprocess.run([str(tools / "node.exe"), "--version"], check=True)
    app = QApplication.instance() or QApplication([])
    icon = root / "assets" / "videodock.ico"
    make_logo(256).save(str(icon), "ICO")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(root / "VideoDock.spec")], cwd=root, check=True)
    output = root / "dist" / "VideoDock"
    shutil.copy2(root / "README.md", output / "README.md")
    shutil.copy2(root / "THIRD_PARTY_NOTICES.md", output / "THIRD_PARTY_NOTICES.md")
    licenses = output / "licenses"
    licenses.mkdir(exist_ok=True)
    for package in ["PySide6-Essentials", "shiboken6", "yt-dlp", "yt-dlp-ejs", "imageio-ffmpeg", "certifi"]:
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files or []:
            name = str(file).lower()
            if "license" in name or "copying" in name:
                path = Path(distribution.locate_file(file))
                if path.is_file():
                    target = licenses / package / str(file)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, target)
    versions = {p: importlib.metadata.version(p) for p in ["PySide6-Essentials", "yt-dlp", "yt-dlp-ejs", "imageio-ffmpeg", "pyinstaller"]}
    (output / "versions.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")
    report = root / "build" / "ui-startup-check.json"
    report.unlink(missing_ok=True)
    import os
    env = dict(os.environ)
    env["VIDEODOCK_CONFIG_DIR"] = str(root / "build" / "ui-check-config")
    check = subprocess.Popen([str(output / "VideoDock.exe"), "--check-ui", str(report)], env=env)
    try:
        code = check.wait(timeout=20)
    except subprocess.TimeoutExpired:
        check.kill()
        check.wait()
        code = -1
    if code or not report.is_file():
        details = report.read_text(encoding="utf-8") if report.is_file() else "No UI startup report"
        raise SystemExit(f"Packaged UI startup check failed:\n{details}")
    result = json.loads(report.read_text(encoding="utf-8"))
    if not result.get("frozen") or not result.get("download_enabled"):
        raise SystemExit(f"Packaged UI startup check failed: {result}")
    print("Packaged UI startup: OK")
    print(f"Ready: {output / 'VideoDock.exe'}")


if __name__ == "__main__":
    main()
