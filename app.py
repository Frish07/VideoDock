import sys
import os
from pathlib import Path


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        from videodock.worker import run_worker
        return run_worker(sys.argv[2])
    from videodock.gui import launch
    initial_url = sys.argv[2] if len(sys.argv) == 3 and sys.argv[1] == "--url" else None
    return launch(initial_url)


if __name__ == "__main__":
    check_path = Path(sys.argv[2]) if len(sys.argv) == 3 and sys.argv[1] == "--check-ui" else None
    try:
        if check_path:
            os.environ["QT_QPA_PLATFORM"] = "offscreen"
            from videodock.gui import launch
            raise SystemExit(launch(check_path=check_path))
        raise SystemExit(main())
    except Exception:
        import traceback
        trace = traceback.format_exc()
        crash_path = check_path or (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "VideoDock" / "VideoDock" / "startup-error.log")
        try:
            crash_path.parent.mkdir(parents=True, exist_ok=True)
            crash_path.write_text(trace, encoding="utf-8")
        except OSError:
            pass
        raise
