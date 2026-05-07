# helix_desktop/launcher_gui.py
import os, sys, time, atexit, subprocess, urllib.request
from pathlib import Path

PORT = int(os.environ.get("HELIX_PORT", "8571"))
URL  = f"http://127.0.0.1:{PORT}"

def start_streamlit(app_path: str, port: int) -> subprocess.Popen:
    cmd = [
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.headless", "true",
        "--server.address", "127.0.0.1",
        "--server.port", str(port),
        "--browser.gatherUsageStats", "false",
        "--server.fileWatcherType", "none",
    ]
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(cmd, cwd=str(Path(app_path).parent), env=os.environ.copy(),
                            creationflags=creationflags)
    atexit.register(lambda: proc.terminate())
    return proc

def wait_until_up(url: str, timeout: float = 45.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(0.25)
    return False

def main():
    root = Path(__file__).resolve().parents[1]
    app_py = str(root / "app.py")

    proc = start_streamlit(app_py, PORT)
    if not wait_until_up(URL, 60):
        proc.terminate()
        raise RuntimeError("Streamlit server failed to start.")

    import webview
    w = webview.create_window("Helix — Genetics Suite", URL, width=1280, height=840, resizable=True)
    try:
        webview.start(gui="edgechromium")
    finally:
        # Close Streamlit when window exits
        try:
            proc.terminate()
        except Exception:
            pass

if __name__ == "__main__":
    main()
