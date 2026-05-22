from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.api.router import api_router
from app.utils.logger import logger

# Inicializamos la aplicación FastAPI con metadatos descriptivos
app = FastAPI(
    title="Bot de Control de Gastos por WhatsApp",
    description="Microservicio backend para la extracción automática de gastos mediante IA (Gemini 1.5 Flash) y su sincronización en Google Sheets & Drive.",
    version="1.0.0"
)

# Configuración de CORS para permitir peticiones si en el futuro se conecta un Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar a dominios específicos de ArquiCost en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro del enrutador principal que agrupa todas las rutas (/health, /webhook)
app.include_router(api_router)


@app.on_event("startup")
async def al_iniciar():
    """
    Evento disparado automáticamente cuando el servidor FastAPI arranca.
    Verifica que las configuraciones críticas estén cargadas correctamente.
    """
    logger.info("=========================================================")
    logger.info("   INICIANDO BOT DE CONTROL DE GASTOS POR WHATSAPP       ")
    logger.info("=========================================================")
    logger.info("Host de ejecución: %s:%s", settings.HOST, settings.PORT)
    logger.info("Número de Teléfono del Bot: %s", settings.BOT_PHONE_NUMBER)
    logger.info("Webhook Verify Token: %s", settings.WHATSAPP_VERIFY_TOKEN)
    logger.info("Google Service Account Cargada: %s", "SÍ" if settings.GOOGLE_SERVICE_ACCOUNT_JSON else "NO")
    logger.info("Servidor listo y escuchando peticiones.")
    logger.info("=========================================================")


@app.on_event("shutdown")
async def al_apagar():
    """
    Evento disparado automáticamente cuando el servidor FastAPI se detiene.
    Permite limpiar recursos, cerrar conexiones de base de datos o APIs.
    """
    logger.info("Cerrando recursos y apagando el servidor FastAPI de forma segura...")


@app.exception_handler(Exception)
async def manejador_excepciones_global(request: Request, exc: Exception):
    """
    Manejador global de excepciones no controladas.
    Evita fugas de información interna al cliente y registra el error con detalle.
    
    Args:
        request: La petición HTTP original.
        exc: La excepción capturada.
        
    Returns:
        JSONResponse con un mensaje genérico de error de servidor (500).
    """
    logger.error("Excepción no controlada en la ruta %s: %s", request.url.path, str(exc), exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ocurrió un error interno en el servidor. Por favor, contacte al administrador."}
    )


@app.get(
    "/",
    status_code=status.HTTP_200_OK,
    tags=["General"],
    summary="Página de inicio y estado base"
)
async def inicio():
    """
    Ruta raíz para indicar que el bot está en línea de forma interactiva.
    
    Returns:
        Un JSON indicando que el servicio está activo.
    """
    return {
        "servicio": "Bot de Gastos Conarca",
        "estado": "En línea",
        "ia_motor": "Gemini 1.5 Flash",
        "fase": "1.0 - MVP",
        "documentacion": "/docs"  # Redirección rápida al Swagger interactivo de FastAPI
    }
