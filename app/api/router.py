from fastapi import APIRouter
from app.api.endpoints import health, webhook

# Enrutador principal de la API
api_router = APIRouter()

# Registro de rutas de salud pública (monitoreo)
api_router.include_router(health.router, tags=["Salud"])

# Registro de rutas para el Webhook de WhatsApp con Meta
api_router.include_router(webhook.router, tags=["Webhook WhatsApp"])
