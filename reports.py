from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import os

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

def get_db_connection():
    """Crear conexión a PostgreSQL"""
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

# ============================================
# Endpoint 1: Test de Conexión
# ============================================
@router.get("/test-conn")
def test_conexion():
    """Prueba de conexión a la base de datos"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SHOW server_version")
        version = cur.fetchone()[0]
        cur.close()
        conn.close()
        return {"status": "EXITOSA", "version": version}
    except Exception as e:
        if conn:
            conn.close()
        return {"status": "FALLO", "error": str(e)}

# ============================================
# Endpoint 2: Persona por ID
# ============================================
@router.get("/persona/{persona_id}")
def obtener_persona(persona_id: int):
    """Obtener nombre y apellido de una persona"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT nombre, apellido FROM persona WHERE id = %s", (persona_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        if not row:
            return {"error": "Persona no encontrada"}
        
        return {"nombre": row['nombre'], "apellido": row['apellido']}
    except Exception as e:
        if conn:
            conn.close()
        return {"error": str(e)}

# ============================================
# Endpoint 3: ListadoRendicion (REPORTE COMPLEJO)
# ============================================
@router.get("/listado-rendicion/{id_juego}")
def listado_rendicion(id_juego: int):
    """Reporte de rendición de operaciones por juego"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
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
            WHERE ope.id_juego = (SELECT id FROM juego WHERE fecha_sorteo = %s) AND ope.id_estado = 437 
            ORDER BY ped.nombre, ped.apellido
        """
        
        cur.execute(query, (id_juego,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convertir Decimal a float para JSON
        reportes = []
        for row in rows:
            reportes.append({
                "numero_operacion": row['numero_operacion'],
                "distribuidor": row['distribuidor'],
                "rendido": row['rendido'],
                "retirado": row['retirado'],
                "devuelto": row['devuelto'],
                "vendido": row['vendido'],
                "precio_carton": float(row['precio_carton']) if row['precio_carton'] else None,
                "comision": float(row['comision']) if row['comision'] else None,
                "monto_comision": float(row['monto_comision']) if row['monto_comision'] else None,
                "monto_a_rendir": float(row['monto_a_rendir']) if row['monto_a_rendir'] else None,
                "monto_efectivo": float(row['monto_efectivo']) if row['monto_efectivo'] else None,
                "monto_credito": float(row['monto_credito']) if row['monto_credito'] else None,
                "monto_telefonia": float(row['monto_telefonia']) if row['monto_telefonia'] else None,
                "monto_otro": float(row['monto_otro']) if row['monto_otro'] else None
            })
        
        return reportes
        
    except Exception as e:
        if conn:
            conn.close()
        return {"error": str(e)}