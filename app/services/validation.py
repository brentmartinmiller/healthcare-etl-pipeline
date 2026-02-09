"""
JSON Schema validation service.

Demonstrates:
- Schema-driven data validation (a core pattern for healthcare interop)
- Collecting all errors rather than failing on the first one
"""

from typing import Any

import jsonschema


def validate_against_schema(data: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    """
    Validate a dict against a JSON schema.
    Returns a list of error messages (empty list = valid).
    """
    validator = jsonschema.Draft7Validator(schema)
    return [error.message for error in validator.iter_errors(data)]
