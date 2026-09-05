from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2 import extensions
import os

# CONFIGURACIÓN GLOBAL ANTES DE CUALQUIER COSA
extensions.register_type(extensions.UNICODE)
extensions.register_type(extensions.UNICODEARRAY)
extensions.set_default_encoding('UTF8')

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

def get_db_connection():
    DB_USER = os.getenv('DB_USER', 'amagno_api')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
    DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'Salvatore')
    
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        options='-c client_encoding=UTF8'
    )
    
    return conn

@router.get("/persona/{persona_id}")
def obtener_persona(persona_id: int):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT nombre, apellido 
            FROM persona 
            WHERE id = %s
        """, (persona_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row is None:
            return {"error": "No encontrada"}
        
        # Retornar directamente, psycopg2 ya debería haber convertido
        return {
            "nombre": row[0],
            "apellido": row[1]
        }
        
    except Exception as e:
        if conn:
            conn.close()
        # NO convertir el error a string, retornar mensaje genérico
        return {"error": "Error interno al consultar"}