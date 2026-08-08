from fastapi import APIRouter
from fastapi.responses import JSONResponse
import psycopg2
import os

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

@router.get("/test-conn")
def test_conexion():
    """Prueba de conexión con encoding forzado en el handshake"""
    DB_USER = os.getenv('DB_USER', 'amagno_api')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
    DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'Salvatore')
    
    conn = None
    try:
        # LA CLAVE: client_encoding='LATIN1' como argumento directo
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            client_encoding='LATIN1'  # <--- ESTO ARREGLA EL HANDSHAKE
        )
        
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
        if conn:
            conn.close()
        return {
            "status": "FALLO",
            "error_type": type(e).__name__
        }

@router.get("/persona/{persona_id}")
def obtener_persona(persona_id: int):
    """Consulta real con encoding forzado"""
    DB_USER = os.getenv('DB_USER', 'amagno_api')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
    DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'Salvatore')
    
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            client_encoding='LATIN1'  # <--- MISMO ARGUMENTO AQUÍ
        )
        
        cur = conn.cursor()
        cur.execute("SELECT nombre, apellido FROM persona WHERE id = %s", (persona_id,))
        row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not row:
            return {"error": "No encontrada"}
        
        # psycopg2 ya decodificó automáticamente usando LATIN1
        return {
            "nombre": row[0],
            "apellido": row[1]
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {"error": "Fallo en consulta", "tipo": type(e).__name__}