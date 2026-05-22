from google.oauth2.service_account import Credentials
import google.auth.transport.requests
import httpx
from app.config import settings
from app.utils.logger import logger
import json
from typing import Dict, Any

class GoogleDriveService:
    """
    Servicio de integración con Google Drive utilizando REST API y Service Accounts de Google Cloud.
    Permite subir los archivos multimedia (recibos) a carpetas específicas de Drive de forma asíncrona.
    """

    def __init__(self) -> None:
        """
        Inicializa los scopes y el estado de las credenciales.
        """
        self.scopes = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        self._credenciales = None

    def _obtener_token_acceso(self) -> str:
        """
        Refresca y retorna un token de acceso OAuth2 vigente a partir de la Service Account.
        
        Returns:
            String con el token de acceso de Google.
        """
        if self._credenciales is None:
            logger.info("Cargando credenciales de la Service Account para Google Drive...")
            credenciales_dict = settings.obtener_credenciales_google()
            self._credenciales = Credentials.from_service_account_info(
                credenciales_dict,
                scopes=self.scopes
            )
        
        # Validamos si el token es nulo o está por expirar y lo refrescamos
        if not self._credenciales.valid:
            logger.info("Refrescando token de acceso OAuth2 de Google Drive...")
            peticion = google.auth.transport.requests.Request()
            self._credenciales.refresh(peticion)
            
        return self._credenciales.token

    async def subir_archivo(
        self,
        contenido: bytes,
        nombre_archivo: str,
        tipo_mime: str,
        carpeta_destino_id: str
    ) -> str:
        """
        Sube un archivo de forma asíncrona a una carpeta de Google Drive utilizando la API REST v3.
        Realiza una petición multipart/related para enviar metadatos y contenido en una sola llamada.
        
        Args:
            contenido: Los bytes del archivo a subir.
            nombre_archivo: Nombre con el que se guardará en Drive.
            tipo_mime: Tipo MIME del archivo (ej. 'image/jpeg', 'application/pdf').
            carpeta_destino_id: ID de la carpeta contenedora en Google Drive.
            
        Returns:
            La URL web pública o interna del archivo subido en Google Drive.
            Retorna string vacío si la subida falla.
        """
        try:
            token = self._obtener_token_acceso()
            url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
            
            # Definimos los metadatos del archivo en formato JSON
            metadatos = {
                "name": nombre_archivo,
                "parents": [carpeta_destino_id]
            }

            # Construimos el cuerpo multipart/related de manera manual
            # Esto garantiza que la API de Google Drive v3 reciba el formato exacto requerido (RFC 2387)
            # y previene que sea rechazado por enviarse como 'multipart/form-data'
            boundary = "boundary_conarca_gastos_whatsapp"
            
            cuerpo_metadata = (
                f"--{boundary}\r\n"
                "Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(metadatos)}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: {tipo_mime}\r\n\r\n"
            ).encode("utf-8")
            
            cuerpo_footer = f"\r\n--{boundary}--\r\n".encode("utf-8")
            
            # Consolidamos todo el payload en formato binario
            cuerpo_completo = cuerpo_metadata + contenido + cuerpo_footer
            
            cabeceras = {
                "Authorization": f"Bearer {token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
                "Content-Length": str(len(cuerpo_completo))
            }

            logger.info("Subiendo archivo '%s' (%s bytes) a Google Drive...", nombre_archivo, len(contenido))
            
            async with httpx.AsyncClient() as cliente:
                respuesta = await cliente.post(
                    url, 
                    headers=cabeceras, 
                    content=cuerpo_completo, 
                    timeout=30.0
                )
                
            if respuesta.status_code == 200:
                datos_archivo = respuesta.json()
                archivo_id = datos_archivo.get("id")
                logger.info("Archivo subido con éxito a Drive. ID Asignado: %s", archivo_id)
                
                # Retorna la URL estándar para previsualizar el archivo en el navegador
                return f"https://drive.google.com/file/d/{archivo_id}/view?usp=drivesdk"
            else:
                logger.error(
                    "Fallo al subir archivo a Drive. Status: %s. Detalle: %s",
                    respuesta.status_code, respuesta.text
                )
                return ""

        except Exception as e:
            logger.exception("Error al subir archivo a Google Drive: %s", str(e))
            return ""


# Instancia singleton para importar en la aplicación
google_drive_service = GoogleDriveService()
