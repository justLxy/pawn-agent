import os
from pathlib import Path


def load_env_file() -> None:
    """Load simple KEY=VALUE pairs from the nearest project .env file."""
    current = Path(__file__).resolve()
    candidates = [current.parent / ".env", current.parent.parent / ".env"]

    env_path = next((path for path in candidates if path.exists()), None)
    if not env_path:
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)
