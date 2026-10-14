# FHIR Server Starter Kit

A minimal, teaching-oriented FHIR R4 server: one fully-wired example
resource (`Organization`), dual FHIR/plain JSON responses, native base R4
structural validation, real `OperationOutcome` error bodies, JWT/RBAC auth,
optional Redis, Docker. Built on top of the generic layered-architecture
foundation in the sibling `fastapi-starter-kit` repo, with a FHIR-specific
layer added on top.

This is deliberately **not** production-complete — it strips out everything
that isn't needed to understand the core shape, so you can learn the
pattern and then add resources on top of it. See "What's simplified" below
for exactly what was cut and why.

## What's included

- **Layered architecture**: `Router → Service → Repository → Model`.
  `app/routers/organization.py` → `app/services/organization_service.py` →
  `app/repository/organization_repository.py` → `app/models/organization.py`
  is the full reference implementation — copy this shape for any new
  resource.
- **Dual content negotiation** (`app/core/content_negotiation.py`):
  `Accept: application/fhir+json` returns full FHIR R4 camelCase JSON;
  `Accept: application/json` (or no header) returns simplified snake_case
  JSON. Every route returns both via `format_response()` /
  `format_paginated_response()`.
- **Native FHIR R4 validation** (`app/fhir/validation/base_r4.py` +
  `app/fhir/spec/fhir.schema.json`): HL7's own published base R4 JSON
  Schema, validated with `jsonschema.Draft6Validator`, one validator
  instance cached per resource type. `OrganizationService` validates the
  resource **before** writing it — an invalid payload never reaches the
  database. This catches things Pydantic's own request-schema validation
  can't (e.g. `identifier.use` codes outside FHIR's required binding) —
  see `tests/integration/test_organization.py`'s
  `test_create_organization_invalid_identifier_use_fails_fhir_validation`.
- **Real `OperationOutcome` errors** (`app/errors/`): every error response
  is a genuine FHIR `OperationOutcome` resource
  (`{"resourceType": "OperationOutcome", "issue": [...]}`), built from
  `app/errors/fhir_codes.py`'s `IssueSeverity`/`IssueType` enums — the same
  vocabulary the real spec defines — not a generic `{"error": {...}}`
  envelope.
- **FHIR mapper pattern** (`app/fhir/mappers/organization/`): `fhir.py`
  (camelCase builders + `to_fhir_organization()`), `plain.py` (snake_case
  - `to_plain_organization()`), and a `preview_fhir_organization()` helper
    that builds the FHIR shape from a not-yet-persisted payload so validation
    can run _before_ `repository.create()` is ever called.
- **Config, DB, Redis, logging, auth, DI, middleware, Docker, tests** —
  all copied unchanged from `fastapi-starter-kit`; see that repo's README
  for the full rundown of each. Nothing FHIR-specific was added to any of
  those layers.
- **Auth is not optional here**: unlike the generic starter kit (where
  auth is opt-in), every `Organization` route is gated by
  `require_permission("organization", "<action>")`. `created_by`/
  `updated_by` come from the verified JWT's `sub` claim, never from the
  request body — set `JWKS_URL`/`JWT_ISSUER` in `.env` to run for real, or
  use the test client's `get_current_user` override (see
  `tests/conftest.py::make_test_user`) for local experimentation.

## What's simplified (and why)

This cuts several things the real production fhir-server has, specifically
so a newcomer can see the whole FHIR-handling path in one sitting:

- **One JSONB column instead of normalized child tables.** Organization's
  repeating/nested FHIR elements (`identifier[]`, `type[]`, `alias[]`,
  `telecom[]`, `address[]`, `contact[]`, `endpoint[]`, `partOf`) are stored
  as a single `fhir_data` JSONB blob on the `organization` row
  (`app/models/organization.py`), instead of one child table per repeating
  element. This avoids ~8 child-table models, repository `_with_relationships()`
  eager-loading, and `selectinload` wiring just to show the FHIR
  request/response/validation cycle. The tradeoff: you can't efficiently
  query or index _into_ individual nested fields at the DB level. A real
  resource with meaningfully-queried sub-elements should use normalized
  child tables instead — see the real project's `app/models/<resource>/`
  packages for that pattern.
- **No multi-tenancy.** The real fhir-server stamps every row with
  `user_id`/`org_id` as tenant-scoping columns and enforces cross-org 404
  masking. This starter drops that entirely — `Organization` rows aren't
  scoped to a tenant at all, only gated by RBAC permission. Add
  `org_id`-style scoping yourself once you have more than one resource and
  an actual multi-tenant need.
- **No terminology service.** Coded fields (`identifier.use`,
  `address.use`, etc.) are validated only against HL7's base R4 required
  bindings baked into `fhir.schema.json`. There's no code-system lookup,
  no display-text resolution, no external terminology server integration.
- **Validation is native-only — no Java validator sidecar, no profile
  layering.** The real project supports a pluggable validation backend
  (native vs. a Java `org.hl7.fhir.validation` sidecar) and layers
  base → country → organization-specific FHIR profiles on top of the base
  spec, backed by a `fhir_profile` table. None of that exists here:
  `validate_base_r4()` always runs the same base R4 JSON Schema check,
  nothing else.
- **One resource.** Organization is the only FHIR resource modeled. The
  real project has ~34; this starter exists so you can add your second one
  yourself and see every layer it touches.

## Running it

```bash
cp .env.example .env   # fill in DATABASE_URL, JWKS_URL/JWT_ISSUER
uv sync
just migrate
just dev                # http://localhost:8000/docs, /docs/scalar, /redoc
```

Or via Docker:

```bash
docker compose up -d
```

## Running without Redis

Set `REDIS__ENABLED=false` (env var, or in `configs/config.yaml`) and drop
the `redis` service from `docker-compose.yml`. Rate limiting falls back to
a per-process sliding window. No other changes needed — the app still
boots and serves requests.

## Running the tests

```bash
uv run pytest
```

Uses an in-memory SQLite DB per test (`tests/conftest.py`), a JSONB→JSON
compile shim for SQLite, and an in-process sequence simulator standing in
for the Postgres `organization_pub_seq` sequence. Auth is satisfied via a
`get_current_user` dependency override (`make_test_user()`), not a real
JWKS fetch.

## Adding a second FHIR resource

Follow the `Organization` shape end to end:

1. **Model** (`app/models/<resource>.py`) — `id` PK (internal, never
   exposed), `<resource>_id` (public, sequence-backed, exposed in every
   response/reference), audit columns (`created_by`/`updated_by`,
   `created_at`/`updated_at`), plus either a single JSONB column for
   nested elements (simple case, like `Organization`) or normalized child
   tables (if you need to query into a nested field).
2. **Schemas** (`app/schemas/<resource>.py`) — `<Resource>CreateSchema` /
   `<Resource>PatchSchema` (plain input, `extra="forbid"`) and
   `FHIR<Resource>Schema` / `Plain<Resource>Response` (dual-format output),
   following `app/schemas/organization.py`.
3. **Mapper package** (`app/fhir/mappers/<resource>/`) — `fhir.py`
   (`to_fhir_<resource>()`, camelCase, strips `None`, `"id": str(...)`),
   `plain.py` (`to_plain_<resource>()`, snake*case, `"id": int`), and a
   `preview_fhir*<resource>()` that builds the FHIR shape from an
   unpersisted payload for validate-before-persist.
4. **Repository** (`app/repository/<resource>_repository.py`) — extends
   `BaseRepository`; `create()`/`get_by_<resource>_id()`/`list()`/
   `patch()`/`delete()`, session-per-operation.
5. **Service** (`app/services/<resource>_service.py`) — calls
   `validate_base_r4("<FhirResourceType>", preview_fhir_<resource>(...))`
   _before_ every create/patch write; owns `to_fhir()`/`to_plain()`.
6. **Router** (`app/routers/<resource>.py`) — `APIRouter(prefix=...,
tags=...)`, every route gated with
   `Depends(require_permission("<resource>", "<action>"))`, inline
   `responses=` with both `application/json` and `application/fhir+json`
   content types via `inline_schema()` — never `response_model=`.
7. **DI** (`app/di/modules/<resource>.py` + `app/di/dependencies/<resource>.py`)
   — wire repository → service → FastAPI dependency; add the new
   `providers.Container(...)` to `app/di/container.py`.
8. **Migration** — `just migrate-generate "add_<resource>_table"`.
9. **Enable it** — add `<resource>` to `configs/config.yaml`'s
   `routes.enabled` list.
10. **Tests** — add `tests/integration/test_<resource>.py` following
    `test_organization.py`: one valid-create test per content type, one
    deliberately-invalid-FHIR-field test asserting a 422 `OperationOutcome`,
    get/list/patch/delete.

No test function in this project needs `@pytest.mark.anyio` or
`import pytest` — `asyncio_mode = "auto"` in `pyproject.toml` handles async
tests automatically; adding either is a convention violation, not a fix.
