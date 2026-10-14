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


async def test_fhir_organization_search_parameters(client):
    # Seed Organization 1: Root hospital with full details
    org1_payload = {
        "name": "Metro Health System",
        "active": True,
        "alias": ["Metro Health", "MHS"],
        "identifier": [{"system": "http://hl7.org/fhir/sid/us-npi", "value": "1122334455", "use": "official"}],
        "type": [{"system": "http://terminology.hl7.org/CodeSystem/organization-type", "code": "prov", "display": "Healthcare Provider"}],
        "telecom": [{"system": "phone", "value": "555-0199", "use": "work"}],
        "address": [{"use": "work", "line": ["100 Metro Ave"], "city": "Metropolis", "state": "NY", "postal_code": "10001", "country": "USA"}],
        "endpoint": [{"reference": "Endpoint/ep-metro-1", "display": "Metro Main Endpoint"}],
        "part_of": None,
    }
    r1 = await client.post("/api/v1/organizations/", json=org1_payload)
    assert r1.status_code == 201
    id1 = r1.json()["id"]

    # Seed Organization 2: Child clinic with different attributes
    org2_payload = {
        "name": "Suburban Dental Clinic",
        "active": False,
        "alias": ["Suburban Dental"],
        "identifier": [{"system": "urn:tax-id", "value": "99-777666", "use": "secondary"}],
        "type": [{"system": "http://terminology.hl7.org/CodeSystem/organization-type", "code": "dept", "display": "Hospital Department"}],
        "telecom": [{"system": "phone", "value": "555-0288", "use": "work"}],
        "address": [{"use": "billing", "line": ["200 Suburb Ln"], "city": "Springfield", "state": "IL", "postal_code": "62701", "country": "USA"}],
        "endpoint": [],
        "part_of": id1,
    }
    r2 = await client.post("/api/v1/organizations/", json=org2_payload)
    assert r2.status_code == 201
    id2 = r2.json()["id"]

    # 1. Search by _id
    resp = await client.get(f"/api/v1/organizations/?_id={id1}")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["data"][0]["id"] == id1

    # Comma-separated _id (OR)
    resp = await client.get(f"/api/v1/organizations/?_id={id1},{id2}")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 2

    # 2. Search by active
    resp = await client.get("/api/v1/organizations/?active=true&name=Metro")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])
    assert not any(o["id"] == id2 for o in resp.json()["data"])

    resp = await client.get("/api/v1/organizations/?active=false&name=Suburban")
    assert resp.status_code == 200
    assert any(o["id"] == id2 for o in resp.json()["data"])

    # 3. Search by name & alias
    # Partial name
    resp = await client.get("/api/v1/organizations/?name=Metro")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # Alias match
    resp = await client.get("/api/v1/organizations/?name=MHS")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # Exact modifier
    resp = await client.get("/api/v1/organizations/?name:exact=Metro Health System")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # Contains modifier
    resp = await client.get("/api/v1/organizations/?name:contains=System")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # 4. Search by phonetic
    resp = await client.get("/api/v1/organizations/?phonetic=Metro")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # 5. Search by identifier
    # Value only
    resp = await client.get("/api/v1/organizations/?identifier=1122334455")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # System and value
    resp = await client.get("/api/v1/organizations/?identifier=http://hl7.org/fhir/sid/us-npi|1122334455")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # System only
    resp = await client.get("/api/v1/organizations/?identifier=http://hl7.org/fhir/sid/us-npi|")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # 6. Search by type
    resp = await client.get("/api/v1/organizations/?type=prov")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    resp = await client.get("/api/v1/organizations/?type=http://terminology.hl7.org/CodeSystem/organization-type|dept")
    assert resp.status_code == 200
    assert any(o["id"] == id2 for o in resp.json()["data"])

    # 7. Search by address (general)
    resp = await client.get("/api/v1/organizations/?address=Metro Ave")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # 8. Address sub-field searches
    # address-city
    resp = await client.get("/api/v1/organizations/?address-city=Metropolis")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    resp = await client.get("/api/v1/organizations/?address-city=Springfield")
    assert resp.status_code == 200
    assert any(o["id"] == id2 for o in resp.json()["data"])

    # address-state
    resp = await client.get("/api/v1/organizations/?address-state=NY")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # address-postalcode
    resp = await client.get("/api/v1/organizations/?address-postalcode=10001")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # address-country
    resp = await client.get("/api/v1/organizations/?address-country=USA")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # address-use
    resp = await client.get("/api/v1/organizations/?address-use=billing")
    assert resp.status_code == 200
    assert any(o["id"] == id2 for o in resp.json()["data"])

    # 9. Search by endpoint
    resp = await client.get("/api/v1/organizations/?endpoint=ep-metro-1")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # 10. Search by partof
    resp = await client.get(f"/api/v1/organizations/?partof={id1}")
    assert resp.status_code == 200
    assert any(o["id"] == id2 for o in resp.json()["data"])

    # 11. Search by :missing modifier
    # Root org has no part_of -> partof:missing=true
    resp = await client.get("/api/v1/organizations/?partof:missing=true&name=Metro")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # Child org has part_of -> partof:missing=false
    resp = await client.get("/api/v1/organizations/?partof:missing=false&name=Suburban")
    assert resp.status_code == 200
    assert any(o["id"] == id2 for o in resp.json()["data"])

    # Endpoint missing
    resp = await client.get("/api/v1/organizations/?endpoint:missing=true&name=Suburban")
    assert resp.status_code == 200
    assert any(o["id"] == id2 for o in resp.json()["data"])

    resp = await client.get("/api/v1/organizations/?endpoint:missing=false&name=Metro")
    assert resp.status_code == 200
    assert any(o["id"] == id1 for o in resp.json()["data"])

    # 12. Combined search with multiple parameters
    resp = await client.get("/api/v1/organizations/?name=Metro&active=true&address-city=Metropolis")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["data"][0]["id"] == id1

    # 13. FHIR Bundle searchset format with Accept: application/fhir+json
    fhir_resp = await client.get(
        "/api/v1/organizations/?name=Metro&address-city=Metropolis",
        headers={"Accept": "application/fhir+json"},
    )
    assert fhir_resp.status_code == 200
    bundle = fhir_resp.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["resourceType"] == "Organization"
    assert bundle["entry"][0]["resource"]["name"] == "Metro Health System"

    # 14. Standard FHIR POST _search endpoint
    post_search_resp = await client.post(
        "/api/v1/organizations/_search",
        data={"name": "Suburban", "active": "false"},
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/fhir+json"},
    )
    assert post_search_resp.status_code == 200
    bundle = post_search_resp.json()
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "searchset"
    assert bundle["total"] == 1
    assert bundle["entry"][0]["resource"]["name"] == "Suburban Dental Clinic"

    # 15. Standard FHIR _count and _sort
    sort_resp = await client.get("/api/v1/organizations/?_count=2&_sort=name")
    assert sort_resp.status_code == 200
    assert len(sort_resp.json()["data"]) <= 2


async def test_create_organization_full_fhir_r4_structure(client):
    """Verifies that an Organization created with the full FHIR R4 structure
    (identifier with type/period, telecom with rank, address with district/text/type,
    contact with purpose CodeableConcept, name HumanName, telecom ContactPoint, address Address,
    endpoint Reference, and generated meta) matches HL7 FHIR standard perfectly."""
    payload = {
        "name": "St. Jude Children's Research Hospital",
        "active": True,
        "alias": ["St. Jude", "SJCRH"],
        "identifier": [
            {
                "use": "official",
                "type": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v2-0203",
                            "code": "PRN",
                            "display": "Provider number",
                        }
                    ],
                    "text": "Provider number",
                },
                "system": "http://hl7.org/fhir/sid/us-npi",
                "value": "9876543210",
            }
        ],
        "type": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/organization-type",
                        "code": "prov",
                        "display": "Healthcare Provider",
                    }
                ],
                "text": "Healthcare Provider",
            }
        ],
        "telecom": [
            {
                "system": "phone",
                "value": "+1-800-822-6344",
                "use": "work",
                "rank": 1,
            }
        ],
        "address": [
            {
                "use": "work",
                "type": "both",
                "text": "262 Danny Thomas Place, Memphis, TN 38105",
                "line": ["262 Danny Thomas Place"],
                "city": "Memphis",
                "district": "Shelby",
                "state": "TN",
                "postal_code": "38105",
                "country": "USA",
            }
        ],
        "part_of": None,
        "contact": [
            {
                "purpose": {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/contactentity-type",
                            "code": "ADMIN",
                            "display": "Administrative",
                        }
                    ],
                    "text": "Administrative Contact",
                },
                "name": {
                    "use": "official",
                    "text": "Dr. James Downing",
                    "family": "Downing",
                    "given": ["James"],
                    "prefix": ["Dr."],
                },
                "telecom": [
                    {
                        "system": "email",
                        "value": "james.downing@stjude.org",
                        "use": "work",
                    }
                ],
                "address": {
                    "line": ["262 Danny Thomas Place, Administration"],
                    "city": "Memphis",
                    "state": "TN",
                    "postal_code": "38105",
                },
            }
        ],
        "endpoint": [
            {
                "reference": "Endpoint/ep-stjude-1",
                "display": "St. Jude FHIR API Gateway",
            }
        ],
    }

    create_resp = await client.post(
        "/api/v1/organizations/",
        json=payload,
        headers={"Accept": "application/fhir+json"},
    )
    assert create_resp.status_code == 201, create_resp.text
    fhir = create_resp.json()

    # Structural assertions matching FHIR R4 Organization specification
    assert fhir["resourceType"] == "Organization"
    assert "id" in fhir
    assert "meta" in fhir
    assert fhir["meta"]["versionId"] == "1"
    assert fhir["name"] == "St. Jude Children's Research Hospital"
    assert fhir["active"] is True
    assert fhir["alias"] == ["St. Jude", "SJCRH"]

    # Identifier
    assert len(fhir["identifier"]) == 1
    ident = fhir["identifier"][0]
    assert ident["use"] == "official"
    assert ident["value"] == "9876543210"
    assert ident["system"] == "http://hl7.org/fhir/sid/us-npi"
    assert ident["type"]["coding"][0]["code"] == "PRN"

    # Type
    assert fhir["type"][0]["coding"][0]["code"] == "prov"

    # Telecom
    assert fhir["telecom"][0]["system"] == "phone"
    assert fhir["telecom"][0]["rank"] == 1

    # Address
    assert fhir["address"][0]["city"] == "Memphis"
    assert fhir["address"][0]["district"] == "Shelby"
    assert fhir["address"][0]["postalCode"] == "38105"

    # Contact
    assert len(fhir["contact"]) == 1
    contact = fhir["contact"][0]
    assert contact["purpose"]["coding"][0]["code"] == "ADMIN"
    assert contact["name"]["family"] == "Downing"
    assert contact["telecom"][0]["value"] == "james.downing@stjude.org"
    assert contact["address"]["city"] == "Memphis"

    # Endpoint
    assert fhir["endpoint"][0]["reference"] == "Endpoint/ep-stjude-1"
