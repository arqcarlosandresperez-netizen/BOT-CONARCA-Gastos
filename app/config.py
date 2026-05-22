import os
from typing import Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json

class Settings(BaseSettings):
    """
    Configuración global y validación de variables de entorno de la aplicación.
    Utiliza Pydantic Settings para cargar variables desde el entorno o un archivo .env.
    """
    # Configuración del Servidor
    PORT: int = Field(default=8000, description="Puerto en el que correrá el servidor FastAPI")
    HOST: str = Field(default="0.0.0.0", description="Host para el servidor FastAPI")
    LOG_LEVEL: str = Field(default="info", description="Nivel de logs de la aplicación")

    # Meta Cloud API (WhatsApp)
    WHATSAPP_TOKEN: str = Field(..., description="Token de acceso permanente de WhatsApp Cloud API")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(..., description="ID del número de teléfono del bot en WhatsApp")
    WHATSAPP_VERIFY_TOKEN: str = Field(..., description="Token de verificación para el webhook de Meta")
    BOT_PHONE_NUMBER: str = Field(..., description="Número de teléfono dedicado al bot con formato +57...")

    # Google AI Studio (Gemini)
    GEMINI_API_KEY: str = Field(..., description="API Key para el servicio de Gemini")

    # Google Cloud (Service Account)
    GOOGLE_SERVICE_ACCOUNT_JSON: str = Field(..., description="Contenido en string del archivo JSON de la Service Account de Google")

    @field_validator("GOOGLE_SERVICE_ACCOUNT_JSON")
    @classmethod
    def validar_service_account_json(cls, v: str) -> str:
        """
        Valida que el string provisto sea un JSON válido para evitar fallos tardíos en el cliente de Google.
        
        Args:
            v: El valor del string JSON a validar.
            
        Returns:
            El mismo valor si es un JSON válido.
            
        Raises:
            ValueError: Si el string no tiene una estructura JSON válida.
        """
        try:
            json.loads(v)
        except json.JSONDecodeError as e:
            raise ValueError(f"GOOGLE_SERVICE_ACCOUNT_JSON no es un JSON válido: {str(e)}")
        return v

    def obtener_credenciales_google(self) -> Dict[str, Any]:
        """
        Deserializa la variable GOOGLE_SERVICE_ACCOUNT_JSON en un diccionario de Python.
        
        Returns:
            Un diccionario con las credenciales de la Service Account.
        """
        return json.loads(self.GOOGLE_SERVICE_ACCOUNT_JSON)

    # Configuración de Pydantic Settings para cargar desde el archivo .env
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignora otras variables del sistema que no estén definidas aquí
    )


# Instancia única de configuración a ser importada en el resto de la aplicación
settings = Settings()
