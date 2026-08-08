from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

@router.get("/persona/{persona_id}")
def obtener_persona(persona_id: int):
    """Endpoint de prueba sin base de datos"""
    return {
        "nombre": "Test",
        "apellido": "User",
        "id": persona_id
    }