# VS Code Setup (Mac Intel, 16GB)

## Open the workspace
- Open VS Code
- File → Open Workspace from File…
- Select: `secure-agentic-cloudops.code-workspace` (in the same folder you downloaded)

## Install recommended extensions
VS Code will prompt you automatically. Click **Install All**.

## Run services
- Terminal → Run Task → `Run: ingest-service (uvicorn)`
- Terminal → Run Task → `Run: detection-service (uvicorn)`

## Debug services
- Run and Debug panel
- Choose **Debug: ingest-service (FastAPI)** or **Debug: detection-service (FastAPI)**

## Common gotchas
- If Poetry creates venv elsewhere, run:
  ```bash
  poetry config virtualenvs.in-project true
  ```
  then reinstall:
  ```bash
  poetry install
  ```
