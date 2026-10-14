# Postman Testing Guide: FHIR R4 Organization & Search

This folder contains the complete Postman collection and environment to test the FHIR R4 Organization resource and all official search parameters per [HL7 FHIR R4 Organization Search Specification](https://www.hl7.org/fhir/R4/organization.html#search).

---

## Files Included

1. **`FHIR_Organization_Search.postman_collection.json`**
   - Complete collection containing over 30 organized requests covering setup, every search parameter, `:missing` modifier searches, combined filters, content negotiation, pagination, sorting, and CRUD.
2. **`FHIR_Starter.postman_environment.json`**
   - Environment variables configured for local testing (`baseUrl`: `http://localhost:8000`, `token`: `dev-token`).
3. **`sample_payloads/full_organization.json`**
   - Full FHIR R4 Organization resource payload including all elements (`identifier`, `type`, `telecom`, `address`, `contact` with purpose/name/telecom/address, `endpoint`, `partOf`, and `meta`).

---

## 1. Start the FHIR Server

Make sure the server is running on `http://localhost:8000`:

```powershell
cd P:\fhir-server-starter\fhir-server-starter
uv run uvicorn app.main:app --reload --port 8000
```

Verify that the server is up by visiting:
- Health check: `http://localhost:8000/health`
- Interactive API Docs (Scalar): `http://localhost:8000/docs/scalar`
- Swagger UI: `http://localhost:8000/docs`

---

## 2. Import into Postman

1. Open Postman.
2. Click **Import** (top left).
3. Select or drag-and-drop:
   - `postman/FHIR_Organization_Search.postman_collection.json`
   - `postman/FHIR_Starter.postman_environment.json`
4. Select the environment **FHIR Server Local** in the top-right environment selector.

---

## 3. Recommended Test Flow

Run the requests in the collection folders in sequence:

### Folder 1: Setup & Create Organizations
1. **Create Root Organization (Full FHIR R4 Structure)**:
   - Creates a full root Organization (*St. Jude Children's Research Hospital*).
   - Postman test script automatically stores the returned ID in the collection variable `{{rootOrgId}}`.
2. **Create Child Organization (Linked via part_of)**:
   - Creates a department/clinic linked to `{{rootOrgId}}`.
   - Postman test script automatically stores the returned ID in `{{childOrgId}}`.

### Folder 2: FHIR Search Parameters (HL7 R4)
Test each search parameter defined in Section 8.6.6 of the FHIR R4 specification:
- `_id`: Logical resource ID (single or comma-separated OR list)
- `active`: Record status (`active=true` or `active=false`)
- `name`: Matches `name` or `alias` (partial substring)
- `name:exact`: Exact string match
- `name:contains`: Substring search
- `phonetic`: Phonetic search on organization name
- `identifier`: Token search by value, `system|value`, or `system|`
- `type`: Token search on CodeableConcept (`prov`, `dept`, etc.)
- `address`: General text search across line, city, state, postalCode, country
- `address-city`: City specified in address (e.g. `Memphis`)
- `address-state`: State specified in address (e.g. `TN`)
- `address-postalcode`: Postal code (e.g. `38105`)
- `address-country`: Country (e.g. `USA`)
- `address-use`: Use code (`work`, `billing`, etc.)
- `endpoint`: Technical endpoint reference (e.g. `ep-stjude-1`)
- `partof`: Parent organization reference

### Folder 3: Missing Value Searches (`:missing` modifier)
Standard FHIR `:missing` modifier testing:
- `partof:missing=true`: Finds root organizations with no parent.
- `partof:missing=false`: Finds child organizations that have a parent.
- `endpoint:missing=true`: Finds organizations without endpoints.
- `endpoint:missing=false`: Finds organizations with endpoints.

### Folder 4: Combined Searches & Advanced Features
- **Multi-parameter Search**: `GET /organizations?name=St. Jude&active=true&address-city=Memphis`
- **FHIR POST `_search`**: `POST /organizations/_search` with `application/x-www-form-urlencoded` or `application/json`
- **Content Negotiation**:
  - `Accept: application/fhir+json` returns FHIR `Bundle` (`type: "searchset"`)
  - `Accept: application/json` returns `{total, limit, offset, data: [...]}`
- **Pagination & Sorting**: `_count`, `_offset`, `_sort=name`, `_sort=-name`

### Folder 5: CRUD Operations
- Retrieve Organization by ID (both FHIR and plain JSON formats)
- Patch Organization (partial update)
- Delete Organization
