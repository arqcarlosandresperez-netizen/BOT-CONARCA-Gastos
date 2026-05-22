import hmac
import hashlib
from fastapi import Request, HTTPException, status
from app.utils.logger import logger

async def validar_firma_whatsapp(request: Request, app_secret: str = "") -> bool:
    """
    Valida la firma X-Hub-Signature-256 enviada por Meta en las cabeceras.
    Garantiza que la solicitud realmente proviene de los servidores de Meta.
    
    Args:
        request: Objeto de petición HTTP de FastAPI.
        app_secret: El secreto de la aplicación de Meta (opcional en MVP).
        
    Returns:
        True si la firma es válida o si la validación está deshabilitada temporalmente en el MVP.
        
    Raises:
        HTTPException: Si la firma no coincide o no está presente (cuando está configurada).
    """
    # En fase MVP, si no se provee un app_secret, registramos una advertencia y permitimos el paso
    if not app_secret:
        return True
        
    firma_cabecera = request.headers.get("X-Hub-Signature-256")
    if not firma_cabecera:
        logger.warning("Falta la cabecera X-Hub-Signature-256 en la solicitud del webhook")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Falta la firma de verificación X-Hub-Signature-256"
        )
        
    # Meta envía la firma en formato: sha256=hash_hexadecimal
    try:
        algoritmo, firma_recibida = firma_cabecera.split("=")
        if algoritmo != "sha256":
            raise ValueError()
    except ValueError:
        logger.error("Formato inválido para la firma X-Hub-Signature-256")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de firma X-Hub-Signature-256 inválido"
        )
        
    cuerpo = await request.body()
    firma_calculada = hmac.new(
        app_secret.encode("utf-8"),
        cuerpo,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(firma_calculada, firma_recibida):
        logger.error("La firma calculada no coincide con X-Hub-Signature-256")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firma de verificación inválida"
        )
        
    return True
