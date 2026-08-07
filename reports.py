import os
import psycopg2
from psycopg2.extras import RealDictCursor

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import logging

from database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

class RendicionItem(BaseModel):
    numero_operacion: int
    distribuidor: str
    rendido: str
    retirado: int
    devuelto: int
    vendido: int
    precio_carton: Optional[float] = None
    comision: Optional[float] = None
    monto_comision: Optional[float] = None
    monto_a_rendir: Optional[float] = None
    monto_efectivo: Optional[float] = None
    monto_credito: Optional[float] = None
    monto_telefonia: Optional[float] = None
    monto_otro: Optional[float] = None

    class Config:
        from_attributes = True

@router.get("/listado-rendicion/{id_juego}", response_model=List[RendicionItem])
def listado_rendicion(id_juego: int, db: Session = Depends(get_db)):
    """
    Reporte de rendición - Con conversión de codificación forzada
    """
    
    # Consulta con conversión explícita a UTF8 usando CONVERT_FROM
    query = text("""
        SELECT 
            ope.numero_operacion, 
            CONVERT_FROM(CONVERT_TO(ped.nombre || ' ' || ped.apellido, 'UTF8'), 'UTF8') AS distribuidor, 
            CASE WHEN ope.rendido=true THEN 'SI' ELSE 'NO' END AS rendido, 
            COALESCE(ret.cantidad,0) AS retirado, 
            COALESCE(dev.cantidad,0) AS devuelto, 
            CASE 
                WHEN ope.rendido=true THEN COALESCE(ret.cantidad,0) - COALESCE(dev.cantidad,0) 
                ELSE 0 
            END AS vendido, 
            ju.precio_carton, 
            ope.comision, 
            (COALESCE(ret.cantidad,0.0) - COALESCE(dev.cantidad,0.0)) * ope.comision AS monto_comision, 
            (COALESCE(ret.cantidad,0.0) - COALESCE(dev.cantidad,0.0)) * (ju.precio_carton - ope.comision) AS monto_a_rendir, 
            COALESCE(cobef.monto,0.0) AS monto_efectivo, 
            COALESCE(cobcr.monto,0.0) AS monto_credito, 
            COALESCE(cobgi.monto,0.0) AS monto_telefonia, 
            COALESCE(cobot.monto,0.0) AS monto_otro 
        FROM operacion_bingo ope 
        LEFT JOIN juego ju ON ope.id_juego = ju.id 
        LEFT JOIN distribuidor di ON ope.id_distribuidor = di.id 
        LEFT JOIN persona ped ON di.id_persona = ped.id 
        LEFT JOIN (
            SELECT id_operacion, COUNT(*) AS cantidad 
            FROM operacion_bingo_detalle_retiro 
            GROUP BY id_operacion
        ) AS ret ON ret.id_operacion = ope.id 
        LEFT JOIN (
            SELECT id_operacion, COUNT(*) AS cantidad 
            FROM operacion_bingo_detalle_devolucion 
            GROUP BY id_operacion
        ) AS dev ON dev.id_operacion = ope.id 
        LEFT JOIN (
            SELECT id_operacion, SUM(monto) AS monto 
            FROM operacion_bingo_detalle_cobro 
            WHERE id_estado=464 AND id_tipo_valor=450 
            GROUP BY id_operacion
        ) AS cobef ON cobef.id_operacion = ope.id 
        LEFT JOIN (
            SELECT id_operacion, SUM(monto) AS monto 
            FROM operacion_bingo_detalle_cobro 
            WHERE id_estado=464 AND id_tipo_valor=456 
            GROUP BY id_operacion
        ) AS cobcr ON cobcr.id_operacion = ope.id 
        LEFT JOIN (
            SELECT id_operacion, SUM(monto) AS monto 
            FROM operacion_bingo_detalle_cobro 
            WHERE id_estado=464 AND id_tipo_valor=455 
            GROUP BY id_operacion
        ) AS cobgi ON cobgi.id_operacion = ope.id 
        LEFT JOIN (
            SELECT id_operacion, SUM(monto) AS monto 
            FROM operacion_bingo_detalle_cobro 
            WHERE id_estado=464 AND id_tipo_valor=454 
            GROUP BY id_operacion
        ) AS cobot ON cobot.id_operacion = ope.id 
        WHERE ope.id_juego = :id_juego AND ope.id_estado = 437 
        ORDER BY ped.nombre, ped.apellido
    """)
    
    try:
        logger.info(f"Ejecutando reporte para id_juego={id_juego}")
        result = db.execute(query, {"id_juego": id_juego})
        rows = result.fetchall()
        logger.info(f"Encontradas {len(rows)} filas")
        
        reportes = []
        for row in rows:
            reporte_item = {
                "numero_operacion": row.numero_operacion,
                "distribuidor": row.distribuidor if row.distribuidor else "",
                "rendido": row.rendido,
                "retirado": row.retirado,
                "devuelto": row.devuelto,
                "vendido": row.vendido,
                "precio_carton": float(row.precio_carton) if row.precio_carton else None,
                "comision": float(row.comision) if row.comision else None,
                "monto_comision": float(row.monto_comision) if row.monto_comision else None,
                "monto_a_rendir": float(row.monto_a_rendir) if row.monto_a_rendir else None,
                "monto_efectivo": float(row.monto_efectivo) if row.monto_efectivo else None,
                "monto_credito": float(row.monto_credito) if row.monto_credito else None,
                "monto_telefonia": float(row.monto_telefonia) if row.monto_telefonia else None,
                "monto_otro": float(row.monto_otro) if row.monto_otro else None
            }
            reportes.append(reporte_item)
        
        logger.info(f"Reporte completado: {len(reportes)} registros")
        return reportes
        
    except Exception as e:
        error_msg = f"Error al ejecutar el reporte: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# ============================================
# Endpoint de PRUEBA: Obtener persona por ID
# ============================================
class PersonaItem(BaseModel):
    nombre: str
    apellido: str

@router.get("/persona/{persona_id}", response_model=PersonaItem)
def obtener_persona(persona_id: int):
    """
    Reporte simple de prueba: obtiene nombre y apellido de una persona por su ID.
    """
    
    # Obtener credenciales del entorno
    DB_USER = os.getenv('DB_USER', 'amagno_api')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'AmagnoAPI_Secure2026!')
    DB_HOST = os.getenv('DB_HOST', '132.255.166.96')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'Salvatore')
    
    conn = None
    try:
        logger.info(f"Buscando persona con id={persona_id}")
        
        # Conexión directa con psycopg2
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            options='-c client_encoding=UTF8'
        )
        
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT nombre, apellido 
            FROM persona 
            WHERE id = %s
        """
        
        cur.execute(query, (persona_id,))
        row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if row is None:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        
        # Manejo seguro de la decodificación
        nombre = row['nombre']
        apellido = row['apellido']
        
        # Si son bytes, decodificar
        if isinstance(nombre, bytes):
            nombre = nombre.decode('utf-8', errors='replace')
        if isinstance(apellido, bytes):
            apellido = apellido.decode('utf-8', errors='replace')
        
        logger.info(f"Persona encontrada: {nombre} {apellido}")
        
        return {
            "nombre": nombre,
            "apellido": apellido
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error al obtener persona: {str(e)}"
        logger.error(error_msg)
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=error_msg)
