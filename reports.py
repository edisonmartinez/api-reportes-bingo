from fastapi import APIRouter
from fastapi.responses import JSONResponse
import psycopg2
import os

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

@router.get("/persona/{persona_id}")
def obtener_persona(persona_id: int):
    DB_USER = os.getenv('DB_USER', 'amagno_api')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
    DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'Salvatore')
    
    try:
        # Conexión con encoding LATIN1 forzado
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            options='-c client_encoding=LATIN1'  # ← CLAVE: forzar LATIN1
        )
        
        cur = conn.cursor()
        cur.execute("SELECT nombre, apellido FROM persona WHERE id = %s", (persona_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return {"error": "No encontrada"}
        
        # psycopg2 ya debería haber convertido de LATIN1 a Python strings
        # Pero por si acaso, decodificamos manualmente
        def safe_decode(val):
            if val is None:
                return ""
            if isinstance(val, bytes):
                return val.decode('latin-1')
            return str(val)
        
        return {
            "nombre": safe_decode(row[0]),
            "apellido": safe_decode(row[1])
        }
        
    except Exception as e:
        if conn:
            conn.close()
        error_type = type(e).__name__
        return {"error": f"Fallo: {error_type}"}