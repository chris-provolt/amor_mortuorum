from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

from jsonschema import Draft202012Validator, exceptions as js_exceptions, validators


# Public logger for the module
logger = logging.getLogger("amor.json")


# ---------------------------
# Exceptions
# ---------------------------

class JsonLoaderError(Exception):
    """Base error for JSON loader issues."""


class JsonFileNotFoundError(JsonLoaderError):
    def __init__(self, path: Union[str, Path]):
        self.path = Path(path)
        super().__init__(f"JSON file not found: {self.path}")


class JsonParseError(JsonLoaderError):
    def __init__(self, path: Union[str, Path], message: str, lineno: Optional[int] = None, colno: Optional[int] = None):
        self.path = Path(path)
        self.message = message
        self.lineno = lineno
        self.colno = colno
        location = f" (line {lineno}, column {colno})" if lineno is not None and colno is not None else ""
        super().__init__(f"Failed to parse JSON at {self.path}{location}: {message}")


class JsonSchemaError(JsonLoaderError):
    def __init__(self, path: Union[str, Path], errors: Sequence[js_exceptions.ValidationError]):
        self.path = Path(path)
        self.errors = list(errors)
        formatted = _format_schema_errors(self.path, self.errors)
        super().__init__(formatted)


class JsonKeyValidationError(JsonLoaderError):
    def __init__(self, path: Union[str, Path], missing_keys: Iterable[str]):
        self.path = Path(path)
        self.missing_keys = sorted(set(missing_keys))
        joined = ", ".join(self.missing_keys)
        super().__init__(
            f"Missing required keys in {self.path}: {joined}. "
            f"Add them to the JSON or provide defaults."
        )


class DuplicateKeyError(JsonLoaderError):
    def __init__(self, key: Any, path: Union[str, Path]):
        self.key = key
        self.path = Path(path)
        super().__init__(f"Duplicate index key '{key}' encountered while loading directory {self.path}")


# ---------------------------
# Utilities
# ---------------------------

JsonObject = Dict[str, Any]


def _extend_with_default(validator_class):
    """Extend a jsonschema validator to set defaults onto instances.

    This modifies the 'properties' validator, so that when a property
    has a 'default' value and is missing on the instance, it will be
    injected before further validation.
    """

    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        if not isinstance(instance, dict):
            # Not an object → let the base validator handle it
            for error in validate_properties(validator, properties, instance, schema):
                yield error
            return

        for prop, subschema in properties.items():
            if "default" in subschema and prop not in instance:
                instance[prop] = deepcopy(subschema["default"])  # safe copy
        # continue with standard property validation
        for error in validate_properties(validator, properties, instance, schema):
            yield error

    return validators.extend(validator_class, {"properties": set_defaults})


DefaultingValidator = _extend_with_default(Draft202012Validator)


def _read_json(path: Union[str, Path]) -> Any:
    p = Path(path)
    if not p.exists():
        raise JsonFileNotFoundError(p)
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise JsonParseError(p, e.msg, e.lineno, e.colno) from e


@dataclass
class ValidationResult:
    data: Any
    defaults_applied: List[str]


def _apply_explicit_defaults(data: Any, defaults: Mapping[str, Any]) -> List[str]:
    """Apply explicit defaults to top-level keys if they are missing.

    Returns a list of keys that were inserted.
    """
    applied: List[str] = []
    if not isinstance(data, MutableMapping):
        return applied
    for k, v in defaults.items():
        if k not in data:
            data[k] = deepcopy(v)
            applied.append(k)
    return applied


def _validate_schema(
    path: Union[str, Path],
    data: Any,
    schema: Optional[Mapping[str, Any]],
) -> List[str]:
    """Validate with JSON Schema and apply defaults from schema if present.

    Returns a list of top-level defaults that appear to have been applied.
    """
    if not schema:
        return []

    if not isinstance(data, (dict, list)):
        raise JsonSchemaError(path, [js_exceptions.ValidationError("Root must be object or array")])

    before_top_keys = set(data.keys()) if isinstance(data, dict) else set()

    validator = DefaultingValidator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        raise JsonSchemaError(path, errors)

    after_top_keys = set(data.keys()) if isinstance(data, dict) else set()
    applied = sorted(list(after_top_keys - before_top_keys))
    return applied


def _validate_required_keys(
    path: Union[str, Path],
    data: Any,
    required_keys: Optional[Iterable[str]],
) -> None:
    if not required_keys:
        return
    if not isinstance(data, Mapping):
        raise JsonKeyValidationError(path, required_keys)
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise JsonKeyValidationError(path, missing)


def _format_schema_errors(path: Path, errors: Sequence[js_exceptions.ValidationError]) -> str:
    """Create a readable, multi-line error message from jsonschema errors."""
    lines = [f"Schema validation failed for {path}:"]

    # Group required property errors for a concise listing
    missing_by_path: Dict[str, List[str]] = {}
    other_msgs: List[str] = []

    for err in errors:
        if err.validator == "required" and isinstance(err.message, str):
            # message like: "'id' is a required property"
            missing_prop = None
            try:
                # err.message is standardized; parse between quotes
                missing_prop = err.message.split("'")[1]
            except Exception:
                missing_prop = None
            where = ".".join([str(p) for p in err.absolute_path]) or "$"
            key = where
            if missing_prop:
                missing_by_path.setdefault(key, []).append(missing_prop)
            else:
                other_msgs.append(f" - At {where}: {err.message}")
        else:
            where = ".".join([str(p) for p in err.absolute_path]) or "$"
            other_msgs.append(f" - At {where}: {err.message}")

    for loc, props in sorted(missing_by_path.items()):
        props_list = ", ".join(sorted(set(props)))
        loc_display = "root" if loc == "$" else loc
        lines.append(f" - Missing required keys at {loc_display}: {props_list}")

    lines.extend(other_msgs)

    return "\n".join(lines)


# ---------------------------
# Public API
# ---------------------------

def load_json_file(
    path: Union[str, Path],
    *,
    schema: Optional[Mapping[str, Any]] = None,
    required_keys: Optional[Iterable[str]] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    apply_defaults: bool = True,
    log: Optional[logging.Logger] = None,
) -> JsonObject:
    """Load a JSON file and validate it.

    - If a JSON Schema is provided, the file is validated against it.
      Defaults declared in the schema will be applied to the instance.
    - Additionally, 'required_keys' can enforce top-level keys.
    - 'defaults' can provide explicit top-level defaults to inject prior to validation.

    Raises JsonLoaderError subclasses on failure.
    Returns the parsed JSON (usually a dict) with defaults applied where safe.
    """
    lg = log or logger

    data = _read_json(path)

    applied_keys: List[str] = []

    if apply_defaults and defaults:
        applied_keys.extend(_apply_explicit_defaults(data, defaults))

    # Validate with schema (also applies schema defaults)
    schema_applied: List[str] = []
    if schema:
        schema_applied = _validate_schema(path, data, schema)

    # Enforce required keys after defaults and schema application
    _validate_required_keys(path, data, required_keys)

    # Log defaults that were applied at the top level
    applied_all = sorted(set(applied_keys + schema_applied))
    if applied_all:
        lg.info(
            "Applied default values for missing keys in %s: %s",
            str(path),
            ", ".join(applied_all),
        )

    return data  # type: ignore[return-value]


def load_json_directory(
    dir_path: Union[str, Path],
    *,
    pattern: str = "*.json",
    schema: Optional[Mapping[str, Any]] = None,
    required_keys: Optional[Iterable[str]] = None,
    defaults: Optional[Mapping[str, Any]] = None,
    apply_defaults: bool = True,
    index_by: Optional[str] = None,
    strict_index: bool = True,
    log: Optional[logging.Logger] = None,
) -> Union[List[JsonObject], Dict[Any, JsonObject]]:
    """Load and validate all JSON files in a directory.

    - pattern: glob to select JSON files
    - index_by: if provided, returns a dict mapping the value of this key to each object
      (objects must be mappings). Otherwise returns a list of objects.
    - strict_index: if True, duplicate index keys raise DuplicateKeyError. If False, last wins.

    Raises JsonLoaderError on file-level or validation errors.
    """
    lg = log or logger

    d = Path(dir_path)
    if not d.exists() or not d.is_dir():
        raise JsonFileNotFoundError(dir_path)

    files = sorted(d.glob(pattern))

    results: List[JsonObject] = []
    for fp in files:
        item = load_json_file(
            fp,
            schema=schema,
            required_keys=required_keys,
            defaults=defaults,
            apply_defaults=apply_defaults,
            log=lg,
        )
        results.append(item)

    if index_by is None:
        return results

    indexed: Dict[Any, JsonObject] = {}
    for obj in results:
        if not isinstance(obj, Mapping):
            raise JsonKeyValidationError(dir_path, [index_by])
        if index_by not in obj:
            raise JsonKeyValidationError(dir_path, [index_by])
        key = obj[index_by]
        if strict_index and key in indexed:
            raise DuplicateKeyError(key, dir_path)
        if key in indexed:
            lg.warning(
                "Duplicate index key '%s' encountered in %s; overwriting due to strict_index=False",
                key,
                dir_path,
            )
        indexed[key] = obj  # type: ignore[assignment]

    return indexed


__all__ = [
    "load_json_file",
    "load_json_directory",
    "JsonLoaderError",
    "JsonFileNotFoundError",
    "JsonParseError",
    "JsonSchemaError",
    "JsonKeyValidationError",
    "DuplicateKeyError",
]
