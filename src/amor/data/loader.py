from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from importlib import resources
from jsonschema import Draft7Validator, RefResolver, ValidationError

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when JSON validation fails."""

    def __init__(self, message: str, errors: Optional[list[ValidationError]] = None):
        super().__init__(message)
        self.errors = errors or []

    def to_human(self) -> str:
        parts = [str(self)]
        for e in self.errors:
            path = "/".join(str(p) for p in e.path) or "<root>"
            parts.append(f" - at {path}: {e.message}")
        return "\n".join(parts)


@dataclass(frozen=True)
class SchemaInfo:
    name: str
    uri: str
    schema: Dict[str, Any]


class SchemaRegistry:
    """Registry for bundled JSON Schemas.

    Discovers schemas from the package resource directory 'amor.data.schemas'.
    A schema's "name" is its filename without the ".schema.json" suffix.
    Its canonical URI is defined in the schema's $id if present, otherwise a synthetic
    package URI will be used.
    """

    _PKG = "amor.data.schemas"

    def __init__(self) -> None:
        self._schemas_by_name: dict[str, SchemaInfo] = {}
        self._schemas_by_uri: dict[str, SchemaInfo] = {}
        self._load_all()

    def _load_all(self) -> None:
        try:
            schema_dir = resources.files(self._PKG)
        except Exception as e:  # pragma: no cover - environment-specific
            logger.warning("Unable to access schema resources: %s", e)
            return

        for entry in schema_dir.iterdir():
            if not entry.name.endswith(".schema.json"):
                continue
            name = entry.name[:-len(".schema.json")]
            with entry.open("rb") as fh:
                schema = json.load(fh)
            uri = schema.get("$id") or f"resource://{self._PKG}/{entry.name}"
            info = SchemaInfo(name=name, uri=uri, schema=schema)
            self._schemas_by_name[name] = info
            self._schemas_by_uri[uri] = info
            logger.debug("Registered schema '%s' (uri=%s)", name, uri)

    def get(self, name_or_uri: str) -> Optional[SchemaInfo]:
        return self._schemas_by_name.get(name_or_uri) or self._schemas_by_uri.get(name_or_uri)

    def names(self) -> list[str]:
        return sorted(self._schemas_by_name.keys())

    def make_validator(self, name_or_uri: str) -> Draft7Validator:
        info = self.get(name_or_uri)
        if not info:
            raise KeyError(f"Schema not found: {name_or_uri}")
        # Build a resolver referencing all known schemas by $id for $ref resolution
        store = {si.uri: si.schema for si in self._schemas_by_uri.values()}
        resolver = RefResolver.from_schema(info.schema, store=store)
        return Draft7Validator(info.schema, resolver=resolver)


class DataLoader:
    """Load JSON files with optional $include expansion and JSON Schema validation.

    Features:
    - Caching to avoid re-reading the same file repeatedly
    - $include directive to include other JSON files
      * If an object contains only {"$include": "path.json"}, it is replaced by the included content
      * If an object contains $include alongside other keys, a deep merge is performed where the
        including object's keys override the included object's keys
      * If the target position is an array with an object {"$include": "..."}, the included
        array will replace that position
    - Automatic detection of schema when the document contains "$schema": "name-or-uri"
    """

    def __init__(self, schema_registry: Optional[SchemaRegistry] = None) -> None:
        self.schemas = schema_registry or SchemaRegistry()
        self._cache: dict[Path, Any] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def load(self, path: os.PathLike | str, *, validate: bool = True, schema: Optional[str] = None) -> Any:
        """Load a JSON file, resolve includes, and optionally validate.

        Args:
            path: Path to a JSON file
            validate: Whether to validate against a schema
            schema: Explicit schema name or URI. If None and validate is True,
                will use the document's $schema if present.
        Returns:
            Parsed Python object
        Raises:
            DataValidationError: if validation fails
            FileNotFoundError: if the file does not exist
        """
        abs_path = Path(path).resolve()
        logger.debug("Loading JSON: %s", abs_path)
        data = self._read_and_expand(abs_path)

        if validate:
            schema_name = schema or (isinstance(data, dict) and data.get("$schema"))
            if schema_name:
                self.validate_data(data, schema_name)
            else:
                logger.debug("No schema specified for %s; skipping validation", abs_path)
        return data

    def validate_data(self, data: Any, schema_name_or_uri: str) -> None:
        try:
            validator = self.schemas.make_validator(schema_name_or_uri)
        except KeyError as e:
            raise DataValidationError(f"Unknown schema: {schema_name_or_uri}") from e

        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            message = f"JSON validation failed for schema '{schema_name_or_uri}'"
            raise DataValidationError(message, errors)

    def _read_and_expand(self, path: Path, _stack: Optional[Tuple[Path, ...]] = None) -> Any:
        if path in self._cache:
            return self._cache[path]

        if not path.exists():
            raise FileNotFoundError(path)

        with path.open("rb") as fh:
            data = json.load(fh)

        expanded = self._expand_includes(data, base_dir=path.parent, _stack=_stack or tuple())
        self._cache[path] = expanded
        return expanded

    def _expand_includes(self, node: Any, *, base_dir: Path, _stack: Tuple[Path, ...]) -> Any:
        # Prevent infinite cycles
        def _load_include(target: str) -> Any:
            inc_path = (base_dir / target).resolve()
            if inc_path in _stack:
                cycle = " -> ".join(str(p) for p in _stack + (inc_path,))
                raise ValueError(f"Cyclic $include detected: {cycle}")
            return self._read_and_expand(inc_path, _stack=_stack + (inc_path,))

        if isinstance(node, dict):
            if "$include" in node:
                # Pure include replacement: only key is $include
                if len(node) == 1:
                    included = _load_include(str(node["$include"]))
                    return self._expand_includes(included, base_dir=base_dir, _stack=_stack)
                # Merge include with overrides
                included = _load_include(str(node["$include"]))
                if not isinstance(included, dict):
                    raise TypeError("Cannot merge $include with non-object content")
                merged = self._deep_merge(included, {k: v for k, v in node.items() if k != "$include"})
                return {k: self._expand_includes(v, base_dir=base_dir, _stack=_stack) for k, v in merged.items()}
            # Regular object: recurse
            return {k: self._expand_includes(v, base_dir=base_dir, _stack=_stack) for k, v in node.items()}
        elif isinstance(node, list):
            result = []
            for item in node:
                if isinstance(item, dict) and "$include" in item and len(item) == 1:
                    included = _load_include(str(item["$include"]))
                    if isinstance(included, list):
                        result.extend(self._expand_includes(included, base_dir=base_dir, _stack=_stack))
                    else:
                        result.append(self._expand_includes(included, base_dir=base_dir, _stack=_stack))
                else:
                    result.append(self._expand_includes(item, base_dir=base_dir, _stack=_stack))
            return result
        else:
            return node

    @staticmethod
    def _deep_merge(base: Any, override: Any) -> Any:
        if isinstance(base, dict) and isinstance(override, dict):
            out = dict(base)
            for k, v in override.items():
                if k in out:
                    out[k] = DataLoader._deep_merge(out[k], v)
                else:
                    out[k] = v
            return out
        return override


@lru_cache(maxsize=1)
def default_loader() -> DataLoader:
    return DataLoader()
