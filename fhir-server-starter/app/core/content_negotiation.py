from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)

FHIR_MEDIA_TYPE = "application/fhir+json"


def wants_fhir(request: Request) -> bool:
    """True when the client's Accept header asks for the FHIR representation."""
    accept = request.headers.get("accept", "")
    chose_fhir = FHIR_MEDIA_TYPE in accept
    logger.debug(
        "Content negotiated",
        extra={"event": "content.negotiated", "accept": accept, "format": "fhir" if chose_fhir else "plain"},
    )
    return chose_fhir


def format_response(
    fhir_data: dict, plain_data: dict, request: Request, status_code: int = 200
) -> JSONResponse:
    """Serialize and return either the FHIR or the plain JSON
    representation depending on the Accept header. Always returns a
    JSONResponse (not response_model=) so FastAPI never re-validates the
    already-shaped dict — see app/routers/organization.py.

    Returning a Response instance directly makes FastAPI use ITS
    status_code, not the route decorator's `status_code=` — pass the
    route's intended status explicitly (e.g. 201 on create) or every
    response silently comes back as 200."""
    if wants_fhir(request):
        return JSONResponse(
            content=jsonable_encoder(fhir_data), status_code=status_code, media_type=FHIR_MEDIA_TYPE
        )
    return JSONResponse(content=jsonable_encoder(plain_data), status_code=status_code)


def format_paginated_response(
    fhir_list: list[dict],
    plain_list: list[dict],
    total: int,
    limit: int,
    offset: int,
    request: Request,
) -> JSONResponse:
    """Plain JSON envelope: {total, limit, offset, data: [...]}.
    FHIR Bundle: {resourceType: "Bundle", type: "searchset", total, entry: [{resource: ...}]}."""
    if wants_fhir(request):
        bundle = {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": total,
            "entry": [{"resource": r} for r in fhir_list],
        }
        return JSONResponse(content=jsonable_encoder(bundle), media_type=FHIR_MEDIA_TYPE)
    return JSONResponse(
        content=jsonable_encoder({"total": total, "limit": limit, "offset": offset, "data": plain_list})
    )
