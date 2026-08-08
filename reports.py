from fastapi import APIRouter
from fastapi.responses import JSONResponse
import psycopg2
import os

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

@router.get("/test-conn")
def test_conexion():
    """Solo prueba la conexión, no consulta datos"""
    DB_USER = os.getenv('DB_USER', 'amagno_api')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
    DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'Salvatore')
    
    conn = None
    try:
        # Intentar conectar
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        
        # Consultar SOLO parámetros del servidor (no datos de tablas)
        cur = conn.cursor()
        cur.execute("SHOW server_version")
        version = cur.fetchone()[0]
        
        cur.execute("SHOW server_encoding")
        encoding = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return {
            "status": "CONEXION EXITOSA",
            "server_version": version,
            "server_encoding": encoding
        }
        
    except Exception as e:
        # Si falla, devolver solo el tipo de error, no el mensaje completo
        if conn:
            conn.close()
        return {
            "status": "FALLO",
            "error_type": type(e).__name__,
            "error_code": getattr(e, 'pgcode', 'N/A')
        }