import json
import logging
import os
from functools import lru_cache
from typing import Any, Dict

from jsonschema import Draft202012Validator

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_item_schema() -> Dict[str, Any]:
    """
    Load the item JSON schema from the data/schemas directory.

    The function is cached for performance since the schema is static.
    """
    # Search for the schema relative to project root, falling back to package-relative path
    potential_paths = [
        os.path.join(os.getcwd(), 'data', 'schemas', 'item.schema.json'),
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'schemas', 'item.schema.json'),
    ]
    for path in potential_paths:
        normalized = os.path.abspath(path)
        if os.path.exists(normalized):
            with open(normalized, 'r', encoding='utf-8') as f:
                logger.debug('Loading item schema from %s', normalized)
                return json.load(f)
    # If not found, raise a clear error
    raise FileNotFoundError('Item schema file not found. Expected at data/schemas/item.schema.json')


def validate_item_dict(data: Dict[str, Any]) -> None:
    """
    Validate a single item dictionary against the item JSON schema.

    Raises:
        jsonschema.ValidationError if the data is invalid.
    """
    schema = _load_item_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
    if errors:
        # Log all errors, then raise the first to provide a clear exception
        for err in errors:
            logger.error('Item schema validation error at %s: %s', list(err.path), err.message)
        raise errors[0]


__all__ = [
    'validate_item_dict',
]
