"""Civic reports and authority query API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.pothole import PotholeReportResponse, CivicAuthorityResponse
from app.crud import pothole as crud_pothole
from app.services.authorities import list_authorities, get_authority_by_code

router = APIRouter()


@router.get(
    "/reports",
    response_model=List[PotholeReportResponse],
    summary="List all dispatched civic hazard reports",
    description="Retrieve audit history of incident reports dispatched to municipal authorities.",
)
def list_reports(
    pothole_id: Optional[int] = Query(None, description="Filter by pothole ID"),
    authority_code: Optional[str] = Query(None, description="Filter by authority code (e.g. BMC, MCD, BBMP)"),
    status: Optional[str] = Query(None, description="Filter by report status (REPORTED, ACKNOWLEDGED, FAILED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List dispatched reports with pagination and filters."""
    _, items = crud_pothole.get_reports(
        db=db,
        skip=skip,
        limit=limit,
        pothole_id=pothole_id,
        authority_code=authority_code,
        status=status,
    )
    return [PotholeReportResponse.model_validate(item) for item in items]


@router.get(
    "/reports/{ticket_id}",
    response_model=PotholeReportResponse,
    summary="Get report details by ticket ID",
    description="Retrieve complete report data, location, photo evidence, and municipal acknowledgment logs.",
)
def get_report_by_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve single report by ticket ID."""
    report = crud_pothole.get_report_by_ticket_id(db, ticket_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ticket ID '{ticket_id}' not found.",
        )
    return PotholeReportResponse.model_validate(report)


@router.get(
    "/authorities",
    response_model=List[CivicAuthorityResponse],
    summary="List registered civic authorities and jurisdictions",
    description="Returns all configured municipal corporations, public works departments, and geographic bounds.",
)
def get_authorities():
    """Retrieve list of all civic authorities and jurisdictions."""
    authorities = list_authorities()
    result = []
    for auth in authorities:
        result.append(
            CivicAuthorityResponse(
                code=auth.code,
                name=auth.name,
                region=auth.region,
                contact_email=auth.contact_email,
                api_endpoint=auth.api_endpoint,
                description=auth.description,
                bounds=list(auth.bounds) if auth.bounds else None,
            )
        )
    return result
