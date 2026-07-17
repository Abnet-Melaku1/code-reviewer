import json

from codereviewer.api.openapi import openapi_schema, to_json


def test_openapi_schema_has_expected_metadata() -> None:
    spec = openapi_schema()

    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"] == "CodeReviewer.ai API"
    assert "/healthz" in spec["paths"]


def test_to_json_is_deterministic() -> None:
    # Stable output (sorted keys) so the generated types diff cleanly and a stale-check works.
    first = to_json(openapi_schema())
    second = to_json(openapi_schema())

    assert first == second
    assert json.loads(first)["info"]["title"] == "CodeReviewer.ai API"


def test_operation_ids_are_unique() -> None:
    # The tag_name operation-id scheme is readable but not unique by construction; a duplicate
    # would produce an invalid OpenAPI doc that generators mishandle. Guard it.
    paths = openapi_schema()["paths"]
    operation_ids = [
        operation["operationId"]
        for methods in paths.values()
        for operation in methods.values()
        if isinstance(operation, dict) and "operationId" in operation
    ]

    assert operation_ids
    assert len(operation_ids) == len(set(operation_ids))
