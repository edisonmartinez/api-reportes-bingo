from fastapi import APIRouter
from fastapi.responses import JSONResponse
import psycopg2
import os

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

@router.get("/persona/{persona_id}")
def obtener_persona_minimal(persona_id: int):
    """Consulta minimalista para diagnosticar"""
    DB_USER = os.getenv('DB_USER', 'amagno_api')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
    DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'Salvatore')
    
    try:
        # Conexión MUY básica
        conn = psycopg2.connect(
            f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
        
        # Consulta ultra-simple sin parámetros
        cur = conn.cursor()
        cur.execute("SET client_encoding TO 'LATIN1'")  # ← Forzar LATIN1
        cur.execute(f"SELECT nombre, apellido FROM persona WHERE id = {persona_id}")
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return {"error": "No encontrada"}
        
        # Decodificación manual byte por byte
        def safe_str(val):
            if val is None:
                return ""
            if isinstance(val, bytes):
                return val.decode('latin-1').encode('utf-8').decode('utf-8')
            return str(val)
        
        return {
            "nombre": safe_str(row[0]),
            "apellido": safe_str(row[1])
        }
        
    except Exception as e:
        # NO mostrar el error completo (ahí está el byte 0xf3)
        return {"error": "Fallo en consulta"}