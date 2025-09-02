"""Data loading and validation utilities.

This package provides:
- SchemaRegistry: discovers and exposes bundled JSON Schemas.
- DataLoader: JSON loading with $include support and JSON Schema validation.
"""

from .loader import DataLoader, SchemaRegistry, DataValidationError

__all__ = [
    "DataLoader",
    "SchemaRegistry",
    "DataValidationError",
]
