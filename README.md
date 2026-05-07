# Helix

Helix is a Python bioinformatics project with a Streamlit desktop UI, a small FastAPI mobile API, and shared core genomics utilities.

## Components

- `app.py`: main Streamlit application
- `mobile_api.py`: FastAPI service for RNA tooling
- `helix_core/`: shared logic for sequence analysis and visualization support
- `helix_desktop/`: desktop UI helpers
- `mobile_app/`: mobile-facing package code

## Configuration

Set these environment variables before starting the Streamlit app:

- `HELIX_USER`
- `HELIX_PASS`
- `HELIX_SALT` (optional)

The project can also load these values from `.env`.

## Run

- Web UI: `helix-web`
- Desktop window on PC: `helix-pc`
- API server: `helix-api`
- Windows shortcut in this repo: `Run Helix Desktop.bat`
