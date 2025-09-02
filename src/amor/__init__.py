from importlib.metadata import version, PackageNotFoundError

__all__ = ["__version__"]

try:
    __version__ = version("amor-mortuorum")
except PackageNotFoundError:  # pragma: no cover - during tests without packaging
    __version__ = "0.0.0"
