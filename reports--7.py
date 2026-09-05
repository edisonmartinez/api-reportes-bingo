from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2 import extensions
import os

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

def get_db_connection():
    """Conexión con encoding forzado desde el inicio"""
    DB_USER = os.getenv('DB_USER', 'amagno_api')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
    DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'Salvatore')
    
    # Crear conexión
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    # IMPORTANTE: Forzar encoding UTF8 inmediatamente
    conn.set_client_encoding('UTF8')
    
    # Verificar que se aplicó
    cur = conn.cursor()
    cur.execute("SHOW client_encoding")
    encoding = cur.fetchone()[0]
    cur.close()
    
    print(f"Client encoding configurado: {encoding}")
    
    return conn

@router.get("/persona/{persona_id}")
def obtener_persona(persona_id: int):
    """Obtener persona con encoding forzado"""
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
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        
        # Forzar conversión a string UTF-8
        nombre = row[0]
        apellido = row[1]
        
        # Si son bytes, decodificar explícitamente
        if isinstance(nombre, bytes):
            nombre = nombre.decode('utf-8', errors='replace')
        if isinstance(apellido, bytes):
            apellido = apellido.decode('utf-8', errors='replace')
        
        return JSONResponse(
            content={
                "nombre": str(nombre),
                "apellido": str(apellido)
            },
            headers={"Content-Type": "application/json; charset=utf-8"}
        )
        
    except Exception as e:
        if conn:
            conn.close()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )