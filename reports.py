from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json

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
        password=DB_PASSWORD
    )
    return conn

@router.get("/persona/{persona_id}")
def obtener_persona_cruda(persona_id: int):
    """Endpoint crudo sin validación de Pydantic"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT nombre, apellido 
            FROM persona 
            WHERE id = %s
        """, (persona_id,))
        
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if row is None:
            return JSONResponse(
                status_code=404,
                content={"error": "Persona no encontrada"}
            )
        
        # Convertir a diccionario simple
        result = {
            "nombre": str(row['nombre']) if row['nombre'] else "",
            "apellido": str(row['apellido']) if row['apellido'] else ""
        }
        
        # Devolver JSONResponse directamente, sin pasar por Pydantic
        return JSONResponse(
            status_code=200,
            content=result,
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
    except Exception as e:
        if conn:
            conn.close()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers={"Content-Type": "application/json; charset=utf-8"}
        )