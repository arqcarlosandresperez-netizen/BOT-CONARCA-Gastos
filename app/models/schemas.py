from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# Definición de categorías válidas según el documento de contexto
CategoriaLiteral = Literal[
    "materiales",
    "herramientas",
    "viaticos",
    "transporte",
    "mano_obra",
    "servicios",
    "administrativo",
    "otros"
]

class GastoExtraido(BaseModel):
    """
    Representa la información estructurada que Gemini 1.5 Flash debe extraer de un comprobante de gasto.
    Sigue de forma estricta los campos requeridos en el Google Sheet de destino.
    """
    valor: Optional[float] = Field(
        default=None, 
        description="Valor monetario del gasto sin símbolos ni separadores de miles."
    )
    moneda: str = Field(
        default="COP", 
        description="Código de la moneda en formato ISO (ej. COP, USD)."
    )
    proveedor: Optional[str] = Field(
        default=None, 
        description="Nombre del almacén, comercio o proveedor que emitió el comprobante."
    )
    descripcion: Optional[str] = Field(
        default=None, 
        description="Descripción corta o detalle de lo que se compró."
    )
    fecha_recibo: Optional[str] = Field(
        default=None, 
        description="Fecha en la que se realizó la compra en formato YYYY-MM-DD."
    )
    categoria_id: Optional[CategoriaLiteral] = Field(
        default=None, 
        description="ID exacto de la categoría asignada al gasto según catálogo disponible."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "valor": 250000.0,
                "moneda": "COP",
                "proveedor": "Ferretería El Perno",
                "descripcion": "Bultos de cemento y arena",
                "fecha_recibo": "2026-05-21",
                "categoria_id": "materiales"
            }
        }


class HealthResponse(BaseModel):
    """
    Esquema de respuesta estándar para el endpoint de diagnóstico de salud (/health).
    """
    status: str = Field(..., description="Estado de salud actual de la aplicación (ej: healthy)")
    timestamp: datetime = Field(..., description="Fecha y hora del servidor en formato ISO")
    version: str = Field(..., description="Versión actual de la aplicación")
