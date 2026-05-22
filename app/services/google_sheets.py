import gspread
from google.oauth2.service_account import Credentials
from app.config import settings
from app.models.schemas import GastoExtraido
from app.utils.logger import logger
from datetime import datetime

class GoogleSheetsService:
    """
    Servicio de integración con Google Sheets utilizando gspread y Service Accounts de Google Cloud.
    Registra dinámicamente cada gasto en la hoja de cálculo del respectivo equipo/proyecto.
    """

    def __init__(self) -> None:
        """
        Inicializa las credenciales de Google y prepara el cliente de gspread.
        """
        # Definimos los alcances (scopes) necesarios para Sheets
        self.scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        self._cliente = None

    def _obtener_cliente(self) -> gspread.Client:
        """
        Autentica y obtiene el cliente de gspread bajo demanda (Lazy Loading).
        
        Returns:
            Un cliente gspread.Client autenticado.
        """
        if self._cliente is None:
            logger.info("Autenticando Service Account en Google Sheets API...")
            credenciales_dict = settings.obtener_credenciales_google()
            credenciales = Credentials.from_service_account_info(
                credenciales_dict,
                scopes=self.scopes
            )
            self._cliente = gspread.authorize(credenciales)
        return self._cliente

    async def registrar_gasto(
        self,
        sheet_id: str,
        persona: str,
        telefono: str,
        gasto: GastoExtraido,
        link_imagen: str = ""
    ) -> bool:
        """
        Inserta un nuevo registro de gasto en la fila final de una hoja de cálculo específica.
        La estructura requerida en el Google Sheet es:
        Timestamp | Persona | Teléfono | Proveedor | Descripción | Categoría | Valor | Moneda | Fecha Recibo | Estado | Link Imagen
        
        Args:
            sheet_id: El ID único de la Google Sheet asignada al grupo de WhatsApp.
            persona: Nombre del remitente que envió el gasto.
            telefono: Teléfono del remitente.
            gasto: Objeto GastoExtraido devuelto por Gemini.
            link_imagen: URL de acceso al archivo adjunto subido en Drive.
            
        Returns:
            True si el registro fue exitoso, False en caso contrario.
        """
        try:
            # Obtenemos el cliente y abrimos el documento por su ID de hoja
            cliente = self._obtener_cliente()
            logger.info("Abriendo Google Sheet con ID: %s", sheet_id)
            documento = cliente.open_by_key(sheet_id)
            
            # Seleccionamos la primera hoja del documento
            hoja = documento.get_worksheet(0)
            
            # Preparamos los valores de la fila
            timestamp_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            fila_datos = [
                timestamp_actual,                     # Timestamp
                persona,                              # Persona
                telefono,                             # Teléfono
                gasto.proveedor or "",                 # Proveedor
                gasto.descripcion or "",               # Descripción
                gasto.categoria_id or "otros",        # Categoría
                gasto.valor or 0.0,                    # Valor
                gasto.moneda or "COP",                # Moneda
                gasto.fecha_recibo or "",             # Fecha Recibo
                "pendiente_revision",                  # Estado (por defecto)
                link_imagen                           # Link Imagen
            ]
            
            logger.info("Insertando fila de gasto en la hoja de cálculo...")
            hoja.append_row(fila_datos)
            logger.info("Fila agregada exitosamente a la Google Sheet.")
            return True
            
        except Exception as e:
            logger.exception("Error al intentar registrar el gasto en Google Sheets para el Sheet ID %s: %s", sheet_id, str(e))
            return False


# Instancia singleton para importar en la aplicación
google_sheets_service = GoogleSheetsService()
