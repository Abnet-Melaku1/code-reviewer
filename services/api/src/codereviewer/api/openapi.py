"""Emit the API's OpenAPI schema — the source of truth for the generated TS types.

Run as ``python -m codereviewer.api.openapi`` (the ``make gen-types`` pipeline pipes this
into ``openapi-typescript``). Output is deterministic so generated types diff cleanly.
"""

import json
import sys
from typing import Any

from codereviewer.api.main import create_app


def openapi_schema() -> dict[str, Any]:
    return create_app().openapi()


def to_json(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main() -> None:
    sys.stdout.write(to_json(openapi_schema()))


if __name__ == "__main__":
    main()
