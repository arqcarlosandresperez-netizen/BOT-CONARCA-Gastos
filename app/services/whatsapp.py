import httpx
from app.config import settings
from app.utils.logger import logger

class WhatsAppService:
    """
    Servicio de integración con la API de nube de WhatsApp (Meta Cloud API).
    Permite enviar mensajes de respuesta y descargar archivos multimedia enviados por los usuarios.
    """
    
    def __init__(self) -> None:
        """
        Inicializa las cabeceras base y la URL de Meta API.
        """
        self.url_base = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_NUMBER_ID}"
        self.headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
        
    async def enviar_mensaje_texto(self, para: str, mensaje: str) -> bool:
        """
        Envía un mensaje de texto simple a un usuario de WhatsApp.
        
        Args:
            para: Número de teléfono del destinatario con código de país.
            mensaje: El cuerpo del mensaje de texto.
            
        Returns:
            True si el mensaje se envió con éxito, False en caso contrario.
        """
        url = f"{self.url_base}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": para,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": mensaje
            }
        }
        
        try:
            async with httpx.AsyncClient() as cliente:
                respuesta = await cliente.post(url, json=payload, headers=self.headers, timeout=10.0)
                
            if respuesta.status_code == 200:
                logger.info("Mensaje de texto enviado con éxito a %s", para)
                return True
            else:
                logger.error(
                    "Fallo al enviar mensaje a %s. Status: %s. Detalle: %s",
                    para, respuesta.status_code, respuesta.text
                )
                return False
        except Exception as e:
            logger.exception("Excepción ocurrida al intentar enviar mensaje de texto a %s: %s", para, str(e))
            return False

    async def descargar_media(self, media_id: str) -> bytes:
        """
        Descarga un archivo multimedia (imagen, audio, pdf) desde los servidores de Meta usando su ID.
        
        Args:
            media_id: El ID del archivo multimedia en la API de Meta.
            
        Returns:
            Los bytes del archivo descargado.
            
        Raises:
            Exception: Si la descarga falla o hay un error de red.
        """
        url_media_info = f"https://graph.facebook.com/v19.0/{media_id}"
        
        try:
            # 1. Obtener la URL de descarga temporal
            async with httpx.AsyncClient() as cliente:
                cabeceras_auth = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}
                respuesta_info = await cliente.get(url_media_info, headers=cabeceras_auth)
                
                if respuesta_info.status_code != 200:
                    raise Exception(f"No se pudo obtener información de la media. Status: {respuesta_info.status_code}")
                
                url_descarga = respuesta_info.json().get("url")
                if not url_descarga:
                    raise Exception("URL de descarga ausente en los metadatos de la media.")

                # 2. Descargar el binario del archivo
                logger.info("Descargando archivo binario desde: %s", url_descarga)
                respuesta_archivo = await cliente.get(url_descarga, headers=cabeceras_auth)
                
                if respuesta_archivo.status_code != 200:
                    raise Exception(f"Fallo al descargar el archivo físico. Status: {respuesta_archivo.status_code}")
                
                return respuesta_archivo.content
                
        except Exception as e:
            logger.exception("Error descargando media ID %s: %s", media_id, str(e))
            raise e


# Instancia singleton para importar en la aplicación
whatsapp_service = WhatsAppService()
