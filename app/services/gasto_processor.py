import os
import json
from typing import Dict, Any, Optional
from app.utils.logger import logger
from app.services.whatsapp import whatsapp_service
from app.services.gemini import gemini_service
from app.services.google_sheets import google_sheets_service
from app.services.google_drive import google_drive_service
from app.models.schemas import GastoExtraido

class GastoProcessor:
    """
    Coordinador de negocio principal (Fase 1 - MVP).
    Gestiona el flujo completo: identifica el grupo, descarga los recibos,
    los almacena en Drive, procesa la IA con Gemini, los registra en Sheets
    y envía confirmaciones dinámicas por WhatsApp.
    """

    def __init__(self) -> None:
        """
        Inicializa el procesador de gastos.
        """
        pass

    def _obtener_config_grupo(self, chat_id: str, remitente: str) -> Dict[str, Any]:
        """
        Carga grupos.json dinámicamente y mapea el chat_id o remitente a su configuración.
        Ofrece un fallback seguro a la clave 'default'.
        
        Args:
            chat_id: ID del grupo o canal de WhatsApp.
            remitente: Número de teléfono del usuario remitente.
            
        Returns:
            Diccionario con la configuración del proyecto ('sheet_id', 'drive_folder_id', 'nombre').
        """
        ruta_config = os.path.join(os.getcwd(), "grupos.json")
        config_defecto = {
            "nombre": "Gastos Sin Categorizar",
            "sheet_id": "",
            "drive_folder_id": ""
        }

        if not os.path.exists(ruta_config):
            logger.warning("El archivo grupos.json no existe. Se usará configuración vacía.")
            return config_defecto

        try:
            with open(ruta_config, "r", encoding="utf-8") as f:
                grupos = json.load(f)
        except Exception as e:
            logger.error("Error leyendo grupos.json: %s. Usando fallback.", str(e))
            return config_defecto

        # 1. Intentar buscar por chat_id (JID del grupo)
        if chat_id in grupos:
            logger.info("Grupo identificado por Chat ID: %s (%s)", chat_id, grupos[chat_id]["nombre"])
            return grupos[chat_id]

        # 2. Intentar buscar por número del remitente (Pruebas 1 a 1 directas)
        if remitente in grupos:
            logger.info("Proyecto identificado por Remitente: %s (%s)", remitente, grupos[remitente]["nombre"])
            return grupos[remitente]

        # 3. Intentar buscar configuración 'default'
        if "default" in grupos:
            logger.info("Chat/Remitente no configurado. Utilizando canal por defecto: %s", grupos["default"]["nombre"])
            return grupos["default"]

        logger.warning("No se encontró ninguna configuración válida en grupos.json.")
        return config_defecto

    async def procesar_mensaje(self, message: Dict[str, Any], persona_nombre: str) -> None:
        """
        Orquesta de forma asíncrona la recepción del webhook para extraer el gasto y registrarlo.
        Diseñado para ejecutarse en BackgroundTasks de FastAPI para evitar timeouts con Meta Cloud API.
        
        Args:
            message: Diccionario con la estructura del mensaje del webhook de WhatsApp.
            persona_nombre: Nombre del perfil del usuario emisor del mensaje.
        """
        remitente = message.get("from", "")
        # En WhatsApp Cloud API, los grupos vienen con un context o chat_id, o usamos remitente como chat_id
        chat_id = message.get("context", {}).get("from", remitente)
        msg_type = message.get("type")
        msg_id = message.get("id")

        logger.info("Iniciando procesamiento asíncrono del gasto para mensaje ID: %s", msg_id)

        # 1. Obtener la configuración del grupo/proyecto asignado
        grupo_config = self._obtener_config_grupo(chat_id, remitente)
        sheet_id = grupo_config.get("sheet_id")
        drive_folder_id = grupo_config.get("drive_folder_id")
        grupo_nombre = grupo_config.get("nombre")

        if not sheet_id or not drive_folder_id:
            logger.error("Configuración incompleta para el chat %s. Se requiere sheet_id y drive_folder_id.", chat_id)
            await whatsapp_service.enviar_mensaje_texto(
                para=remitente,
                mensaje="❌ *Error de Configuración*\nTu grupo/número no está correctamente enlazado a un proyecto en el sistema. Contacta al administrador."
            )
            return

        archivo_bytes: Optional[bytes] = None
        mime_type: Optional[str] = None
        texto_adicional: Optional[str] = None
        link_imagen = ""

        # 2. Descargar y almacenar multimedia en Google Drive si aplica
        if msg_type == "image":
            image_data = message.get("image", {})
            media_id = image_data.get("id")
            mime_type = image_data.get("mime_type", "image/jpeg")
            texto_adicional = image_data.get("caption")  # El subtítulo de la foto

            logger.info("Mensaje contiene imagen (ID: %s). Iniciando descarga...", media_id)
            try:
                # Descargar binario de los servidores de Meta
                archivo_bytes = await whatsapp_service.descargar_media(media_id)
                
                # Generar nombre de archivo único
                extension = mime_type.split("/")[-1] if "/" in mime_type else "jpg"
                nombre_archivo = f"Gasto_{remitente}_{msg_id}.{extension}"
                
                # Subir archivo a la carpeta del proyecto en Google Drive
                link_imagen = await google_drive_service.subir_archivo(
                    contenido=archivo_bytes,
                    nombre_archivo=nombre_archivo,
                    tipo_mime=mime_type,
                    carpeta_destino_id=drive_folder_id
                )
            except Exception as e:
                logger.error("Fallo crítico en el procesamiento de la imagen: %s", str(e))
                await whatsapp_service.enviar_mensaje_texto(
                    para=remitente,
                    mensaje="❌ *Error de Imagen*\nNo logramos procesar la imagen enviada. Por favor, vuelve a intentarlo."
                )
                return

        elif msg_type == "text":
            texto_adicional = message.get("text", {}).get("body")
            logger.info("Procesando entrada basada únicamente en texto: '%s'", texto_adicional)

        else:
            logger.warning("Tipo de mensaje %s no soportado en la Fase 1 (MVP).", msg_type)
            await whatsapp_service.enviar_mensaje_texto(
                para=remitente,
                mensaje=f"⚠️ *Formato no soportado*\nPor ahora solo puedo procesar fotos de recibos o mensajes de texto descriptivos. ¡Muy pronto habilitaremos audios y PDFs!"
            )
            return

        # 3. Invocar al motor de Inteligencia Artificial (Gemini 1.5 Flash)
        logger.info("Enviando datos a Gemini para extracción estructurada...")
        gasto: GastoExtraido = await gemini_service.analizar_gasto(
            archivo_bytes=archivo_bytes,
            mime_type=mime_type,
            texto_adicional=texto_adicional
        )

        logger.info(
            "Datos extraídos por Gemini: Proveedor: %s, Concepto: %s, Valor: %s, Categoría: %s",
            gasto.proveedor, gasto.descripcion, gasto.valor, gasto.categoria_id
        )

        # 4. Persistir registro en Google Sheets
        logger.info("Registrando gasto en la Google Sheet del proyecto: %s", grupo_nombre)
        exito_sheets = await google_sheets_service.registrar_gasto(
            sheet_id=sheet_id,
            persona=persona_nombre,
            telefono=remitente,
            gasto=gasto,
            link_imagen=link_imagen
        )

        if not exito_sheets:
            logger.error("Error al persistir el registro del gasto en Google Sheets.")
            await whatsapp_service.enviar_mensaje_texto(
                para=remitente,
                mensaje="❌ *Error de Registro*\nNo logramos guardar los datos del gasto en la hoja de cálculo. Por favor, reintenta más tarde."
            )
            return

        # 5. Envío de confirmación estilizada al usuario por WhatsApp
        # Formatear el valor monetario de forma elegante
        valor_formateado = f"${gasto.valor:,.2f}" if gasto.valor is not None else "No especificado"
        categoria_formateada = gasto.categoria_id.upper() if gasto.categoria_id else "OTROS"

        mensaje_confirmacion = (
            "✅ *¡Gasto Registrado Exitosamente!*\n\n"
            f"📍 *Proyecto:* {grupo_nombre}\n"
            f"👤 *Remitente:* {persona_nombre}\n"
            f"🏢 *Proveedor:* {gasto.proveedor or 'No legible'}\n"
            f"📝 *Concepto:* {gasto.descripcion or 'Gasto genérico'}\n"
            f"💰 *Valor:* {valor_formateado} {gasto.moneda}\n"
            f"🏷️ *Categoría:* {categoria_formateada}\n"
            f"📅 *Fecha Recibo:* {gasto.fecha_recibo or 'Hoy'}\n\n"
            "El registro se encuentra en estado *pendiente de revisión* en tu planilla de Google Sheets."
        )

        if link_imagen:
            mensaje_confirmacion += f"\n📂 *Ver Recibo en Drive:* {link_imagen}"

        logger.info("Enviando mensaje de confirmación exitosa a %s", remitente)
        await whatsapp_service.enviar_mensaje_texto(para=remitente, mensaje=mensaje_confirmacion)


# Instancia singleton lista para usar en la aplicación
gasto_processor = GastoProcessor()
