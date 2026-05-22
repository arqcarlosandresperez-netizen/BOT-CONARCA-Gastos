import google.generativeai as genai
from app.config import settings
from app.models.schemas import GastoExtraido
from app.utils.logger import logger
from typing import Optional
import json

class GeminiService:
    """
    Servicio de Inteligencia Artificial utilizando Gemini 1.5 Flash.
    Permite procesar texto, imágenes, PDFs o audios de comprobantes de gastos 
    y estructurarlos de forma determinista a un formato JSON compatible con Pydantic.
    """
    
    def __init__(self) -> None:
        """
        Inicializa y configura el cliente oficial de Google Generative AI con la API Key.
        """
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.modelo_nombre = "gemini-1.5-flash"
        
    async def analizar_gasto(
        self, 
        archivo_bytes: Optional[bytes] = None, 
        mime_type: Optional[str] = None, 
        texto_adicional: Optional[str] = None
    ) -> GastoExtraido:
        """
        Envía un archivo (imagen, audio, pdf) y/o texto a Gemini para extraer estructuradamente el gasto.
        
        Args:
            archivo_bytes: Opcional. Los bytes del archivo adjunto (recibo).
            mime_type: Opcional. El tipo MIME del archivo (ej: 'image/jpeg', 'application/pdf', 'audio/mp3').
            texto_adicional: Opcional. Texto descriptivo del mensaje enviado por el usuario.
            
        Returns:
            Un objeto GastoExtraido con los campos detectados de forma tipada.
        """
        # Configuramos el prompt de sistema del contexto
        prompt_sistema = """
        Eres un asistente experto en contabilidad y administración financiera que extrae datos de gastos de forma extremadamente precisa.
        Analiza el contenido provisto (que puede incluir imágenes de recibos, audios transcritos, PDFs o explicaciones en texto) y responde ÚNICAMENTE con un JSON válido que siga exactamente el esquema especificado, sin explicaciones ni markdown.

        Categorías disponibles (debes usar estrictamente uno de los siguientes IDs exactos en minúscula):
        - materiales
        - herramientas
        - viaticos
        - transporte
        - mano_obra
        - servicios
        - administrativo
        - otros

        Campos obligatorios en el JSON de salida:
        - valor: número flotante/entero sin símbolos, signos ni comas de miles (ej: 250000.0). Pon null si no se puede determinar.
        - moneda: siempre "COP" por defecto si es en pesos colombianos, a menos que identifiques claramente otra moneda (ej: "USD").
        - proveedor: nombre exacto del almacén, negocio o empresa emisora del recibo. Pon null si no es visible.
        - descripcion: descripción corta en español del concepto comprado.
        - fecha_recibo: fecha de la compra en formato estricto YYYY-MM-DD. Si no es legible en el comprobante, usa la fecha actual de hoy.
        - categoria_id: id exacto de la lista de categorías (materiales, herramientas, viaticos, transporte, mano_obra, servicios, administrativo, otros).

        Si no logras extraer un campo de la imagen o del texto, colócalo como null.
        """

        model = genai.GenerativeModel(
            model_name=self.modelo_nombre,
            system_instruction=prompt_sistema
        )

        contenidos = []

        # 1. Agregar el archivo multimedia si existe
        if archivo_bytes and mime_type:
            logger.info("Adjuntando archivo multimedia para Gemini con MimeType: %s", mime_type)
            contenidos.append({
                "mime_type": mime_type,
                "data": archivo_bytes
            })

        # 2. Agregar instrucciones de texto
        instrucciones = "Extrae la información de este recibo de gasto."
        if texto_adicional:
            instrucciones += f"\nContexto provisto por el usuario: '{texto_adicional}'"
        
        contenidos.append(instrucciones)

        try:
            logger.info("Enviando petición a Gemini 1.5 Flash...")
            # Forzamos respuesta en formato JSON estructurado
            response = model.generate_content(
                contenidos,
                generation_config={"response_mime_type": "application/json"}
            )
            
            logger.info("Gemini respondió exitosamente.")
            logger.debug("Respuesta cruda de Gemini: %s", response.text)
            
            # Cargamos la respuesta en un diccionario y lo parseamos con Pydantic
            datos_json = json.loads(response.text)
            return GastoExtraido(**datos_json)

        except Exception as e:
            logger.exception("Error al interactuar con Gemini o parsear la respuesta: %s", str(e))
            
            # --- DIAGNÓSTICO EN TIEMPO DE ERROR ---
            try:
                logger.info("Iniciando autodiagnóstico: listando modelos disponibles con la API Key...")
                modelos_disponibles = []
                for m in genai.list_models():
                    modelos_disponibles.append(m.name)
                logger.info("Modelos accesibles con esta API Key: %s", modelos_disponibles)
            except Exception as diag_err:
                logger.error("Error crítico durante el autodiagnóstico de Gemini (posible API Key inválida o API deshabilitada en GCP): %s", str(diag_err))
            
            # Retornamos un objeto vacío/fallido para no romper el flujo
            return GastoExtraido(
                valor=None,
                moneda="COP",
                proveedor=None,
                descripcion="Error al procesar con IA",
                fecha_recibo=None,
                categoria_id="otros"
            )


# Instancia singleton para importar en la aplicación
gemini_service = GeminiService()

