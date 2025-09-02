from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("amormortuorum")
except PackageNotFoundError:  # pragma: no cover - during development
    __version__ = "0.0.0-dev"
