# lightweight launcher that uses your .venv to run Streamlit
import os, sys, subprocess, time

def find_project_root():
    # start near the EXE, walk up a few folders looking for app.py and .venv
    bases = []
    if getattr(sys, "frozen", False):
        bases += [os.path.dirname(sys.executable)]
    here = os.path.abspath(os.path.dirname(__file__))
    bases += [here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))]

    for base in bases:
        app = os.path.join(base, "app.py")
        py  = os.path.join(base, ".venv", "Scripts", "python.exe")
        if os.path.exists(app) and os.path.exists(py):
            return base, py, app
    raise FileNotFoundError("Could not locate project root with app.py and .venv\\Scripts\\python.exe")

def main():
    root, py, app = find_project_root()
    # launch streamlit from your venv
    cmd = [py, "-m", "streamlit", "run", app, "--server.headless=false", "--browser.gatherUsageStats=false"]
    subprocess.Popen(cmd, cwd=root, close_fds=True)
    # small message window for double-click runs
    print("Launching Helix… you can close this window.")
    time.sleep(2)

if __name__ == "__main__":
    main()
