from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
from decimal import Decimal

from database import get_db

# Crear router
router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

# ============================================
# Modelo de respuesta
# ============================================
class RendicionItem(BaseModel):
    numero_operacion: int
    distribuidor: str
    rendido: str
    retirado: int
    devuelto: int
    vendido: int
    precio_carton: Optional[Decimal] = None
    comision: Optional[Decimal] = None
    monto_comision: Optional[Decimal] = None
    monto_a_rendir: Optional[Decimal] = None
    monto_efectivo: Optional[Decimal] = None
    monto_credito: Optional[Decimal] = None
    monto_telefonia: Optional[Decimal] = None
    monto_otro: Optional[Decimal] = None

    class Config:
        from_attributes = True

# ============================================
# Endpoint: ListadoRendicion
# ============================================
@router.get("/listado-rendicion/{id_juego}", response_model=List[RendicionItem])
def listado_rendicion(id_juego: int, db: Session = Depends(get_db)):
    """
    Reporte de rendición de operaciones por juego.
    
    - **id_juego**: ID del juego a consultar
    - Retorna: Lista de operaciones con información completa de rendición
    """
    
    query = text("""
        SELECT 
            ope.numero_operacion, 
            ped.nombre || ' ' || ped.apellido AS distribuidor, 
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
        result = db.execute(query, {"id_juego": id_juego})
        rows = result.fetchall()
        
        # Convertir a lista de diccionarios
        reportes = []
        for row in rows:
            reportes.append({
                "numero_operacion": row.numero_operacion,
                "distribuidor": row.distribuidor,
                "rendido": row.rendido,
                "retirado": row.retirado,
                "devuelto": row.devuelto,
                "vendido": row.vendido,
                "precio_carton": row.precio_carton,
                "comision": row.comision,
                "monto_comision": row.monto_comision,
                "monto_a_rendir": row.monto_a_rendir,
                "monto_efectivo": row.monto_efectivo,
                "monto_credito": row.monto_credito,
                "monto_telefonia": row.monto_telefonia,
                "monto_otro": row.monto_otro
            })
        
        return reportes
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al ejecutar el reporte: {str(e)}"
        )