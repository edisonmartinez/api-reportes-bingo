from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel
import logging

from database import get_db

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# ============================================
# Función auxiliar para decodificar texto
# ============================================
def safe_decode(value):
    """Decodifica texto manejando errores de codificación"""
    if value is None:
        return None
    if isinstance(value, str):
        # Si ya es string, intentar limpiar caracteres problemáticos
        try:
            return value.encode('utf-8').decode('utf-8')
        except:
            # Si falla, reemplazar caracteres inválidos
            return value.encode('utf-8', errors='replace').decode('utf-8')
    return str(value)

# ============================================
# Endpoint: ListadoRendicion
# ============================================
@router.get("/listado-rendicion/{id_juego}", response_model=List[RendicionItem])
def listado_rendicion(id_juego: int, db: Session = Depends(get_db)):
    """
    Reporte de rendición de operaciones por juego.
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
        logger.info(f"Ejecutando reporte para id_juego={id_juego}")
        result = db.execute(query, {"id_juego": id_juego})
        rows = result.fetchall()
        
        logger.info(f"Encontradas {len(rows)} filas")
        
        reportes = []
        for idx, row in enumerate(rows):
            try:
                # Decodificar de forma segura el campo distribuidor
                distribuidor_safe = safe_decode(row.distribuidor)
                
                reporte_item = {
                    "numero_operacion": row.numero_operacion,
                    "distribuidor": distribuidor_safe,
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
                
            except Exception as e:
                logger.error(f"Error procesando fila {idx}: {str(e)}")
                # Continuar con la siguiente fila en lugar de fallar todo
                continue
        
        logger.info(f"Reporte completado: {len(reportes)} registros procesados")
        return reportes
        
    except Exception as e:
        error_msg = f"Error al ejecutar el reporte: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)