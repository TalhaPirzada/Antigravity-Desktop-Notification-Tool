import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_root() -> Path:
    """Directory that holds assets/ and bin/.

    Source checkout: repository root.
    Packaged binary: the directory containing the executable (release archives
    ship assets/ and the macOS notifier app next to it).
    """
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
