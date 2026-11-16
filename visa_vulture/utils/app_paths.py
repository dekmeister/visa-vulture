"""Resolution of filesystem locations that differ when running frozen.

When run from source or a pip install, relative paths keep resolving against
the current working directory, as they always have. When packaged as a
standalone executable (e.g. with PyInstaller), the working directory is
unpredictable (it depends on how the exe was launched) and the install folder
may not be writable, so:

- user-editable content (the custom ``instruments/`` folder) is looked up next
  to the executable, and
- writable output (log files) goes to a per-user data directory.
"""

import os
import sys
from pathlib import Path

APP_DIR_NAME = "VISAVulture"


def is_frozen() -> bool:
    """Return True when running as a packaged executable."""
    return bool(getattr(sys, "frozen", False))


def app_base_dir() -> Path:
    """Directory that user-editable content is resolved against.

    The executable's folder when frozen, otherwise the current working
    directory.
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def user_data_dir() -> Path:
    """Per-user writable directory for application output such as logs.

    Windows: %LOCALAPPDATA%\\VISAVulture
    macOS:   ~/Library/Application Support/VISAVulture
    Other:   $XDG_STATE_HOME/VISAVulture (default ~/.local/state/VISAVulture)
    """
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        root = Path(base) if base else Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_STATE_HOME")
        root = Path(base) if base else Path.home() / ".local" / "state"
    return root / APP_DIR_NAME


def resolve_custom_instruments_dir() -> Path:
    """Location of the custom instruments folder."""
    return app_base_dir() / "instruments"


def resolve_log_file(log_file: str | Path) -> Path:
    """Resolve the configured log file path.

    Absolute paths are used as-is. Relative paths resolve against the user
    data directory when frozen, and against the working directory otherwise.
    """
    path = Path(log_file)
    if path.is_absolute() or not is_frozen():
        return path
    return user_data_dir() / path
