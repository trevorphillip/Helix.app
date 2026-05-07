# desktop_launcher.py
import os
import subprocess
import sys
import time
import socket
import webbrowser
from http.client import HTTPConnection

# ---- tweak these if your entry file is named differently ----
APP_FILE = "app.py"       # your Streamlit app
APP_TITLE = "Helix — Genetics Suite"  # window title

# pick a free localhost port
def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

def wait_until_up(host: str, port: int, timeout: float = 20.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            conn = HTTPConnection(host, port, timeout=1.0)
            conn.request("GET", "/_stcore/health")
            r = conn.getresponse()
            if r.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False

def get_python_executable(project_root: str) -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_python):
        return venv_python
    return sys.executable


def run_streamlit_subprocess(project_root: str, app_path: str, port: int) -> subprocess.Popen:
    python_exe = get_python_executable(project_root)
    cmd = [
        python_exe,
        "-m",
        "streamlit",
        "run",
        app_path,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--global.developmentMode",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]
    return subprocess.Popen(cmd, cwd=project_root)

def find_project_root() -> str:
    bases = []
    if getattr(sys, "frozen", False):
        bases.append(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)))
        bases.append(os.path.dirname(sys.executable))
    here = os.path.abspath(os.path.dirname(__file__))
    bases.extend([here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))])

    for base in bases:
        candidate = os.path.join(base, APP_FILE)
        if os.path.exists(candidate):
            return base
    raise FileNotFoundError(f"Could not locate {APP_FILE}")

def get_app_file_path() -> str:
    """
    Resolve path to app.py both in development and when frozen by PyInstaller.
    """
    return os.path.join(find_project_root(), APP_FILE)

def main():
    port = find_free_port()
    project_root = find_project_root()
    app_path = get_app_file_path()

    # Ensure Streamlit picks up your theme config if you have .streamlit/config.toml
    # When frozen, we copy it as data next to the EXE; set working dir accordingly.
    os.chdir(project_root)

    proc = run_streamlit_subprocess(project_root, app_path, port)

    # Wait until the server is ready
    url = f"http://127.0.0.1:{port}"
    if not wait_until_up("127.0.0.1", port, timeout=25):
        print("Failed to start the embedded Streamlit server.")
        proc.terminate()
        sys.exit(1)

    # Create a native window that points at our local server
    try:
        import webview  # pywebview
        window = webview.create_window(APP_TITLE, url, width=1280, height=860, confirm_close=True)
        webview.start(gui="edgechromium" if sys.platform.startswith("win") else None)
    except Exception:
        # fallback: open default browser if webview is not available
        webbrowser.open(url)
        print(f"Opened {url} in your browser. Press Ctrl+C to quit.")
        try:
            while True:
                if proc.poll() is not None:
                    break
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    finally:
        if proc.poll() is None:
            proc.terminate()

if __name__ == "__main__":
    main()
