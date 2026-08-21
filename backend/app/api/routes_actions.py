from fastapi import APIRouter, Depends, HTTPException

from app.clients.real_debrid_client import RealDebridApiError, RealDebridAuthError
from app.models.schemas import ResolveRequest, ResolveResponse
from app.services.link_service import LinkService
from app.services.real_deps import get_link_service

router = APIRouter(prefix="/api/actions", tags=["actions"])


@router.post("/resolve", response_model=ResolveResponse)
async def resolve_magnet(payload: ResolveRequest, link_service: LinkService = Depends(get_link_service)):
    try:
        result = await link_service.resolve(payload.magnet)
        return ResolveResponse(**result)
    except Exception as exc:
        return ResolveResponse(
            success=False,
            message="Real-Debrid desativado ou sem assinatura Premium ativa."
        )
