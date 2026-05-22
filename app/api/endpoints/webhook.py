from fastapi import APIRouter, Request, Response, Query, status, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from app.config import settings
from app.utils.logger import logger
from app.services.gasto_processor import gasto_processor

router = APIRouter()

@router.get(
    "/webhook",
    summary="Verificación del Webhook de WhatsApp",
    description="Endpoint requerido por Meta para validar la propiedad del webhook usando un token de verificación."
)
async def verificar_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
) -> Response:
    """
    Gestiona la verificación GET de Meta para registrar el webhook.
    Aplica limpieza de espacios (.strip()) y logs detallados para diagnóstico seguro en producción.
    """
    logger.info("============================================================")
    logger.info("🔍 PETICIÓN DE VERIFICACIÓN DE WEBHOOK RECIBIDA")
    logger.info("Parámetros Recibidos:")
    logger.info("  - hub.mode: %s", hub_mode)
    logger.info("  - hub.challenge: %s", hub_challenge)
    logger.info("  - hub.verify_token (recibido): %s", f"*** (Longitud: {len(hub_verify_token)})" if hub_verify_token else "Ninguno")
    
    token_config = settings.WHATSAPP_VERIFY_TOKEN
    logger.info("Configuración del Servidor:")
    logger.info("  - WHATSAPP_VERIFY_TOKEN (esperado): %s", f"*** (Longitud: {len(token_config)})" if token_config else "NO CONFIGURADO EN EL .ENV")
    
    if hub_mode and hub_verify_token and hub_challenge:
        # Aplicamos .strip() para evitar fallos por espacios accidentales invisibles en Render o Meta
        token_recibido_limpio = hub_verify_token.strip()
        token_config_limpio = token_config.strip() if token_config else ""
        
        if hub_mode == "subscribe" and token_recibido_limpio == token_config_limpio:
            logger.info("✅ VERIFICACIÓN EXITOSA: Los tokens coinciden. Retornando hub.challenge.")
            logger.info("============================================================")
            # Retornamos directamente un PlainText Response usando el objeto Response plano de FastAPI
            return Response(content=hub_challenge, media_type="text/plain", status_code=status.HTTP_200_OK)
        else:
            logger.warning("❌ VERIFICACIÓN FALLIDA: Los tokens NO coinciden o el modo no es 'subscribe'.")
            logger.info("============================================================")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token de verificación inválido"
            )
            
    logger.error("❌ VERIFICACIÓN RECHAZADA: Solicitud mal formada o faltan parámetros query.")
    logger.info("============================================================")
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Parámetros de verificación faltantes"
    )



@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Recepción de eventos de WhatsApp",
    description="Recibe eventos en tiempo real (mensajes de texto, imágenes, audios) enviados al bot por WhatsApp."
)
async def recibir_evento_webhook(request: Request, background_tasks: BackgroundTasks) -> Response:
    """
    Procesa las notificaciones de mensajes entrantes de la API de WhatsApp Cloud.
    Valida que los mensajes no sean propios del bot ni del sistema antes de procesarlos.
    
    Args:
        request: Petición HTTP que contiene el cuerpo JSON enviado por Meta.
        background_tasks: Gestor de tareas en segundo plano de FastAPI.
        
    Returns:
        Respuesta HTTP 200 OK inmediata para confirmar la recepción a Meta.
    """
    try:
        payload = await request.json()
    except Exception as e:
        logger.error("Error al parsear el JSON de la solicitud: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuerpo de solicitud inválido, se requiere JSON."
        )

    logger.debug("Evento recibido del webhook: %s", payload)

    # Validamos que sea un payload de WhatsApp válido
    if "object" not in payload or payload["object"] != "whatsapp_business_account":
        # Retornamos 200 para evitar reintentos de Meta si es una notificación de otro tipo
        return Response(status_code=status.HTTP_200_OK)

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" not in value:
                continue

            # Extraemos el nombre de perfil del remitente si está disponible
            contacts = value.get("contacts", [])
            persona_nombre = "Usuario"
            if contacts:
                persona_nombre = contacts[0].get("profile", {}).get("name", "Usuario")

            for message in value.get("messages", []):
                # -------------------------------------------------------------
                # IDENTIFICACIÓN DE REMITENTES (CRÍTICO)
                # -------------------------------------------------------------
                
                # 1. Ignorar mensajes emitidos por el propio Bot
                from_number = message.get("from")
                if from_number == settings.BOT_PHONE_NUMBER:
                    logger.debug("Mensaje ignorado: Enviado por el propio bot (%s)", from_number)
                    continue

                # 2. Ignorar mensajes de sistema o notificaciones administrativas de Meta
                msg_type = message.get("type")
                if msg_type in ["system", "notification"]:
                    logger.debug("Mensaje ignorado: Tipo de mensaje de sistema/notificación (%s)", msg_type)
                    continue

                # Extraer contenido detallado según el tipo de mensaje para imprimirlo en consola
                contenido_legible = ""
                if msg_type == "text":
                    contenido_legible = f"Texto: {message.get('text', {}).get('body', '')}"
                elif msg_type == "image":
                    caption = message.get("image", {}).get("caption", "Sin descripción")
                    contenido_legible = f"Imagen (ID: {message.get('image', {}).get('id')}) - Comentario: {caption}"
                elif msg_type == "audio":
                    contenido_legible = f"Audio (ID: {message.get('audio', {}).get('id')}, Voice note: {message.get('audio', {}).get('voice', False)})"
                elif msg_type == "document":
                    caption = message.get("document", {}).get("caption", "Sin descripción")
                    filename = message.get("document", {}).get("filename", "Sin nombre")
                    contenido_legible = f"Documento/PDF (Nombre: {filename}, ID: {message.get('document', {}).get('id')}) - Comentario: {caption}"
                else:
                    contenido_legible = f"Otros datos (Detalle crudo: {message})"

                # -------------------------------------------------------------
                # IMPRESIÓN DETALLADA EN CONSOLA (REQUERIDO)
                # -------------------------------------------------------------
                logger.info("============================================================")
                logger.info("       MENSAJE ENTRANTE PROCESADO POR EL WEBHOOK            ")
                logger.info("============================================================")
                logger.info(" Remitente : %s", from_number)
                logger.info(" Tipo      : %s", msg_type)
                logger.info(" ID Mensaje: %s", message.get("id"))
                logger.info(" Contenido : %s", contenido_legible)
                logger.info("============================================================")

                # -------------------------------------------------------------
                # PROGRAMAR TAREA EN SEGUNDO PLANO (COORDINADOR MVP)
                # -------------------------------------------------------------
                logger.info("Encolando procesamiento asíncrono para el gasto...")
                background_tasks.add_task(
                    gasto_processor.procesar_mensaje,
                    message,
                    persona_nombre
                )

    # Retornamos 200 OK siempre para Meta, garantizando que no reintenten enviar la misma carga
    return Response(status_code=status.HTTP_200_OK)
