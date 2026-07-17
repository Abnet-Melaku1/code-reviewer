.PHONY: gen-types

# Regenerate packages/types from the API's OpenAPI schema (source of truth: libs/schemas ->
# FastAPI -> OpenAPI -> TS). Never hand-edit the generated output.
gen-types:
	uv run python -m codereviewer.api.openapi > packages/types/openapi.json
	pnpm --filter @codereviewer/types run generate
