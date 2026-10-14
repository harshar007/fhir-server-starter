async def test_create_organization_plain_json(client):
    resp = await client.post(
        "/api/v1/organizations/",
        json={"name": "Acme Health Clinic", "active": True},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Acme Health Clinic"
    assert body["active"] is True
    assert isinstance(body["id"], int)
    assert body["created_by"] == "u-test"


async def test_create_organization_fhir_json(client):
    resp = await client.post(
        "/api/v1/organizations/",
        json={
            "name": "Acme Health Clinic",
            "active": True,
            "identifier": [{"system": "urn:example:tax-id", "value": "12-3456789", "use": "official"}],
        },
        headers={"Accept": "application/fhir+json"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["resourceType"] == "Organization"
    assert body["name"] == "Acme Health Clinic"
    assert body["identifier"][0]["value"] == "12-3456789"
    assert "id" in body and isinstance(body["id"], str)


async def test_create_organization_invalid_identifier_use_fails_fhir_validation(client):
    """`use` passes Pydantic's own schema (it's just a plain str there) but
    fails HL7's real base R4 required-binding enum for Identifier.use —
    demonstrating exactly why native FHIR validation catches things plain
    request-schema validation can't."""
    resp = await client.post(
        "/api/v1/organizations/",
        json={
            "name": "Acme Health Clinic",
            "identifier": [{"system": "urn:example:tax-id", "value": "X", "use": "not-a-real-use-code"}],
        },
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["resourceType"] == "OperationOutcome"
    assert body["issue"][0]["severity"] == "error"
    assert "identifier" in body["issue"][0]["expression"][0]


async def test_get_organization_by_id(client):
    create = await client.post("/api/v1/organizations/", json={"name": "Lookup Org"})
    org_id = create.json()["id"]

    resp = await client.get(f"/api/v1/organizations/{org_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Lookup Org"


async def test_get_organization_not_found_returns_operation_outcome(client):
    resp = await client.get("/api/v1/organizations/999999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["resourceType"] == "OperationOutcome"
    assert body["issue"][0]["code"] == "not-found"


async def test_list_organizations(client):
    await client.post("/api/v1/organizations/", json={"name": "Org A"})
    await client.post("/api/v1/organizations/", json={"name": "Org B"})

    resp = await client.get("/api/v1/organizations/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 2
    assert len(body["data"]) >= 2


async def test_patch_organization_name(client):
    create = await client.post("/api/v1/organizations/", json={"name": "Old Name"})
    org_id = create.json()["id"]

    resp = await client.patch(f"/api/v1/organizations/{org_id}", json={"name": "New Name"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "New Name"
    assert body["updated_by"] == "u-test"


async def test_delete_organization(client):
    create = await client.post("/api/v1/organizations/", json={"name": "Temp Org"})
    org_id = create.json()["id"]

    resp = await client.delete(f"/api/v1/organizations/{org_id}")
    assert resp.status_code == 204

    follow_up = await client.get(f"/api/v1/organizations/{org_id}")
    assert follow_up.status_code == 404


async def test_create_organization_v2_full_features_and_sequence(client):
    payload = {
        "name": "General Hospital V2",
        "active": True,
        "alias": ["Gen Hosp"],
        "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1234567890", "use": "official"}],
        "type": [{"system": "http://terminology.hl7.org/CodeSystem/organization-type", "code": "prov", "display": "Healthcare Provider"}],
        "telecom": [{"system": "phone", "value": "555-1212", "use": "work"}],
        "address": [{"line": ["100 Hospital Way"], "city": "Metropolis", "postal_code": "12345"}],
        "endpoint": [{"reference": "Endpoint/ep-1", "display": "FHIR Server Endpoint"}],
        "part_of": 190001,
    }

    # Plain JSON response check
    plain_resp = await client.post(
        "/api/v1/organizations/",
        json=payload,
        headers={"Accept": "application/json"},
    )
    assert plain_resp.status_code == 201, plain_resp.text
    plain = plain_resp.json()
    assert plain["name"] == "General Hospital V2"
    assert plain["org_id"] == "org-test"
    assert plain["id"] >= 190000
    assert plain["alias"] == ["Gen Hosp"]
    assert len(plain["endpoint"]) == 1
    assert plain["endpoint"][0]["reference"] == "Endpoint/ep-1"
    assert plain["part_of"] == 190001

    # FHIR response check for the same created resource
    fhir_resp = await client.get(
        f"/api/v1/organizations/{plain['id']}",
        headers={"Accept": "application/fhir+json"},
    )
    assert fhir_resp.status_code == 200, fhir_resp.text
    fhir = fhir_resp.json()
    assert fhir["resourceType"] == "Organization"
    assert fhir["id"] == str(plain["id"])
    assert fhir["alias"] == ["Gen Hosp"]
    assert fhir["endpoint"][0]["reference"] == "Endpoint/ep-1"
    assert fhir["partOf"]["reference"] == "Organization/190001"


async def test_patch_organization_v2_dedicated_columns(client):
    create_resp = await client.post(
        "/api/v1/organizations/",
        json={"name": "Patch Target Clinic", "alias": ["Initial Alias"]},
    )
    assert create_resp.status_code == 201
    org_id = create_resp.json()["id"]

    patch_payload = {
        "alias": ["Updated Alias"],
        "endpoint": [{"reference": "Endpoint/new-ep"}],
    }
    patch_resp = await client.patch(
        f"/api/v1/organizations/{org_id}",
        json=patch_payload,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    patched = patch_resp.json()
    assert patched["name"] == "Patch Target Clinic"
    assert patched["alias"] == ["Updated Alias"]
    assert patched["endpoint"][0]["reference"] == "Endpoint/new-ep"
