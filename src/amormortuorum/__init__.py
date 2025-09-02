from importlib.metadata import version, PackageNotFoundError

__all__ = [
    "__version__",
]

try:
    __version__ = version("amormortuorum")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"
