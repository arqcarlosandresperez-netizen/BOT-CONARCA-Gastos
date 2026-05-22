from fastapi import APIRouter, Request, Response, Query, status, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from app.config import settings
from app.utils.logger import logger
from app.services.gasto_processor import gasto_processor

router = APIRouter()

@router.get(
    "/webhook",
    response_class=PlainTextResponse,
    summary="Verificación del Webhook de WhatsApp",
    description="Endpoint requerido por Meta para validar la propiedad del webhook usando un token de verificación."
)
async def verificar_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token")
) -> str:
    """
    Gestiona la verificación GET de Meta para registrar el webhook.
    
    Args:
        hub_mode: El modo enviado por Meta (debe ser 'subscribe').
        hub_challenge: El reto aleatorio enviado por Meta a retornar.
        hub_verify_token: El token de verificación enviado por Meta.
        
    Returns:
        El valor de hub_challenge si el token de verificación coincide.
        
    Raises:
        HTTPException: Si la validación falla (403 Forbidden).
    """
    logger.info("Recibida solicitud de verificación de webhook de Meta.")
    
    if hub_mode and hub_verify_token:
        if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("Webhook verificado exitosamente con Meta.")
            return hub_challenge
        else:
            logger.warning("Fallo en la verificación del webhook: token inválido.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Token de verificación inválido"
            )
            
    logger.error("Solicitud de verificación mal formada.")
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
