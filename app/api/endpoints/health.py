from fastapi import APIRouter, status
from datetime import datetime
from app.models.schemas import HealthResponse

router = APIRouter()

@router.get(
    "/health", 
    response_model=HealthResponse, 
    status_code=status.HTTP_200_OK,
    summary="Diagnóstico de salud de la aplicación",
    description="Permite verificar que la instancia del servidor FastAPI está activa y respondiendo."
)
async def check_health() -> HealthResponse:
    """
    Retorna el estado de salud y la hora actual del servidor.
    
    Returns:
        Un objeto HealthResponse con información de diagnóstico.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0"
    )
