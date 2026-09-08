from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from typing import Optional
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
# Endpoint 3: ListadoRendicion (FECHA SORTEO)
# ============================================
@router.get("/listado-rendicion/{fecha_sorteo}")
def listado_rendicion(fecha_sorteo: str):
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
        
        cur.execute(query, (fecha_sorteo,))
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

# ========================================================
# Endpoint 4: ListadoRendicion (TIPO JUEGO / FECHA SORTEO)
# ========================================================
@router.get("/listado-rendicion/{tipo_juego}/{fecha_sorteo}")
def listado_rendicion(tipo_juego: str, fecha_sorteo: str):
    """
    Reporte de rendición por tipo de juego y fecha de sorteo.
    tipo_juego: 'bingo', 'combinado' o 'rifa'
    fecha_sorteo: Formato YYYY-MM-DD (ej: 2024-01-15)
    """
    
    # 1. Validar que el tipo de juego sea permitido (Seguridad)
    tipos_validos = ["bingo", "combinado", "rifa"]
    if tipo_juego not in tipos_validos:
        return {"error": f"Tipo de juego no válido. Use uno de: {', '.join(tipos_validos)}"}

    # 2. Seleccionar la consulta SQL según el tipo de juego
    if tipo_juego == "bingo":
        query = """
            SELECT 
                ope.numero_operacion, 
                ped.nombre || ' ' || ped.apellido AS distribuidor, 
                CASE WHEN ope.rendido=true THEN 'SI' ELSE 'NO' END AS rendido, 
                COALESCE(ret.cantidad,0) AS retirado, 
                COALESCE(dev.cantidad,0) AS devuelto, 
                CASE WHEN ope.rendido=true THEN COALESCE(ret.cantidad,0) - COALESCE(dev.cantidad,0) ELSE 0 END AS vendido, 
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
            LEFT JOIN (SELECT id_operacion, COUNT(*) AS cantidad FROM operacion_bingo_detalle_retiro GROUP BY id_operacion) AS ret ON ret.id_operacion = ope.id 
            LEFT JOIN (SELECT id_operacion, COUNT(*) AS cantidad FROM operacion_bingo_detalle_devolucion GROUP BY id_operacion) AS dev ON dev.id_operacion = ope.id 
            LEFT JOIN (SELECT id_operacion, SUM(monto) AS monto FROM operacion_bingo_detalle_cobro WHERE id_estado=464 AND id_tipo_valor=450 GROUP BY id_operacion) AS cobef ON cobef.id_operacion = ope.id 
            LEFT JOIN (SELECT id_operacion, SUM(monto) AS monto FROM operacion_bingo_detalle_cobro WHERE id_estado=464 AND id_tipo_valor=456 GROUP BY id_operacion) AS cobcr ON cobcr.id_operacion = ope.id 
            LEFT JOIN (SELECT id_operacion, SUM(monto) AS monto FROM operacion_bingo_detalle_cobro WHERE id_estado=464 AND id_tipo_valor=455 GROUP BY id_operacion) AS cobgi ON cobgi.id_operacion = ope.id 
            LEFT JOIN (SELECT id_operacion, SUM(monto) AS monto FROM operacion_bingo_detalle_cobro WHERE id_estado=464 AND id_tipo_valor=454 GROUP BY id_operacion) AS cobot ON cobot.id_operacion = ope.id 
            WHERE ope.id_juego = (SELECT id FROM juego WHERE fecha_sorteo = %s) 
            AND ope.id_estado = 437 
            ORDER BY ped.nombre, ped.apellido
        """
    
    elif tipo_juego == "combinado":
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
            FROM operacion_binrifa ope
            LEFT JOIN juego_binrifa ju ON ope.id_juego = ju.id
            LEFT JOIN distribuidor di ON ope.id_distribuidor = di.id
            LEFT JOIN persona ped ON di.id_persona = ped.id
            LEFT JOIN (
                SELECT id_operacion, COUNT(*) AS cantidad
                FROM operacion_binrifa_detalle_retiro
                GROUP BY id_operacion
            ) AS ret ON ret.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, COUNT(*) AS cantidad
                FROM operacion_binrifa_detalle_devolucion
                GROUP BY id_operacion
            ) AS dev ON dev.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, SUM(monto) AS monto
                FROM operacion_binrifa_detalle_cobro
                WHERE id_estado=464 AND id_tipo_valor=450
                GROUP BY id_operacion
            ) AS cobef ON cobef.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, SUM(monto) AS monto
                FROM operacion_binrifa_detalle_cobro
                WHERE id_estado=464 AND id_tipo_valor=456
                GROUP BY id_operacion
            ) AS cobcr ON cobcr.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, SUM(monto) AS monto
                FROM operacion_binrifa_detalle_cobro
                WHERE id_estado=464 AND id_tipo_valor=455
                GROUP BY id_operacion
            ) AS cobgi ON cobgi.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, SUM(monto) AS monto
                FROM operacion_binrifa_detalle_cobro
                WHERE id_estado=464 AND id_tipo_valor=454
                GROUP BY id_operacion
            ) AS cobot ON cobot.id_operacion = ope.id
            WHERE ope.id_juego = (SELECT id FROM juego_binrifa WHERE fecha_sorteo = %s) 
            AND ope.id_estado = 437
            ORDER BY ped.nombre, ped.apellido
        """
    
    else: # tipo_juego == "rifa"
        return {"error": "El reporte de 'rifa' está en desarrollo. Próximamente disponible."}

    # 3. Ejecutar la consulta seleccionada
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Ejecutamos con el parámetro fecha_sorteo
        cur.execute(query, (fecha_sorteo,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # 4. Formatear la respuesta a JSON
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
    
# ============================================
# Endpoint 5: Arqueo Caja (Fecha Inicio y Fin / Caja / Tipo Valor / Tipo Juego / Fecha Sorteo Inicio y Fin / Tipo Movimiento / Tipo Operación / Concepto general)
# ============================================
@router.get("/arqueo-caja")
def arqueo_caja(
    fecha_inicio: str = Query(..., description="Fecha inicio operación (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin operación (YYYY-MM-DD)"),
    id_caja: Optional[int] = Query(None, description="ID de caja específica"),
    tipo_valor: Optional[str] = Query(None, description="Buscar en tipo_valor (LIKE)"),
    tipo_juego: Optional[str] = Query(None, description="Filtrar por: bingo, combinado, rifa, super5, super10, animalitos"),
    fecha_sorteo_inicio: Optional[str] = Query(None, description="Inicio rango fecha sorteo (YYYY-MM-DD)"),
    fecha_sorteo_fin: Optional[str] = Query(None, description="Fin rango fecha sorteo (YYYY-MM-DD)"),
    tipo_movimiento: Optional[str] = Query(None, description="INGRESO o EGRESO"),
    tipo_operacion: Optional[str] = Query(None, description="Buscar en tipo_operacion (LIKE)"),
    concepto_general: Optional[str] = Query(None, description="Buscar en concepto (LIKE)")
):
    # 1. Validaciones básicas
    tipos_validos = ["bingo", "combinado", "rifa", "super5", "super10", "animalitos"]
    if tipo_juego and tipo_juego.lower() not in tipos_validos:
        return {"error": f"tipo_juego debe ser uno de: {tipos_validos}"}

    # 2. Construcción dinámica de filtros de juego/sorteo
    game_filter_sql = ""
    params = {}

    # CASO A: Solo filtro por tipo de juego (sin fechas de sorteo)
    # Usamos LIKE sobre det.juego como en tu consulta original
    if tipo_juego and not fecha_sorteo_inicio and not fecha_sorteo_fin:
        game_filter_sql = f" AND UPPER(det.juego) LIKE UPPER(%(tj)s)"
        params["tj"] = f"{tipo_juego.upper()}%"

    # CASO B: Filtro por fechas de sorteo (con o sin tipo de juego específico)
    elif fecha_sorteo_inicio or fecha_sorteo_fin:
        conditions = []
        tablas_juego = {
            "bingo": ["juego"],
            "combinado": ["juego_binrifa"],
            "rifa": ["juego_rifa"],
            "super5": ["juego_bingo5"],
            "super10": ["juego_bingo10"],
            "animalitos": ["juego_bingo25"]
        }

        # Determinar qué tablas buscar
        if tipo_juego:
            tablas_a_buscar = tablas_juego.get(tipo_juego.lower(), [])
        else:
            tablas_a_buscar = list(set().union(*tablas_juego.values()))

        for tbl in tablas_a_buscar:
            cond = f"EXISTS (SELECT 1 FROM {tbl} j WHERE j.id = det.id_juego"
            
            if fecha_sorteo_inicio and fecha_sorteo_fin:
                cond += " AND j.fecha_sorteo BETWEEN %(fsi)s AND %(fsf)s"
            elif fecha_sorteo_inicio:
                cond += " AND j.fecha_sorteo >= %(fsi)s"
            elif fecha_sorteo_fin:
                cond += " AND j.fecha_sorteo <= %(fsf)s"
                
            cond += ")"
            conditions.append(cond)

        if conditions:
            game_filter_sql = " AND (" + " OR ".join(conditions) + ")"
            
            if fecha_sorteo_inicio: params["fsi"] = fecha_sorteo_inicio
            if fecha_sorteo_fin: params["fsf"] = fecha_sorteo_fin
                        
    # 3. Filtros adicionales seguros con LIKE
    extra_filters = []
    
    if id_caja is not None:
        extra_filters.append("caj.id = %(id_caja)s")
        params["id_caja"] = id_caja
        
    if tipo_valor:
        extra_filters.append("UPPER(det.tipo_valor) LIKE UPPER(%(tv)s)")
        params["tv"] = f"%{tipo_valor}%"
        
    if tipo_movimiento:
        extra_filters.append("UPPER(det.tipo_movimiento) = UPPER(%(tm)s)")
        params["tm"] = tipo_movimiento
        
    if tipo_operacion:
        extra_filters.append("UPPER(det.tipo_operacion) LIKE UPPER(%(to)s)")
        params["to"] = f"%{tipo_operacion}%"
        
    if concepto_general:
        extra_filters.append("UPPER(det.concepto_general) LIKE UPPER(%(con)s)")
        params["con"] = f"%{concepto_general}%"

    where_extra = "".join([f" AND {f}" for f in extra_filters])

    # 4. Consulta Base Optimizada
    base_query = f"""
        SELECT 
            ROW_NUMBER() OVER (ORDER BY caj.denominacion, det.fecha, det.hora, det.numero_tipo_movimiento, det.numero_tipo_operacion) AS item,
            det.*
        FROM (
            -- BLOQUE 1: Ventas Directas
            SELECT 
                ope.id_caja, caj.numero_arqueo, caj.denominacion AS caja, 
                ope.id_funcionario, COALESCE(pef.nombre || ' ' || pef.apellido, '') AS funcionario,
                '1' AS numero_tipo_movimiento, 'INGRESO' AS tipo_movimiento,
                '2' AS numero_tipo_operacion, 'INGRESO VENTA DIRECTA' AS tipo_operacion,
                'Venta de cartón: Rendición' AS concepto, 'CONTADO VENTA' AS concepto_general,
                per.id AS id_persona, COALESCE(per.nombre || ' ' || per.apellido, '') AS persona,
                ope.numero_operacion, ope.fecha, ope.hora, tva.denominacion AS tipo_valor,
                ope.tipo_juego || ' ' || to_char(ope.fecha_sorteo, 'DD/MM/YY') AS juego,
                ope.monto, 0.0 AS diferencia, ope.id_juego, ope.tipo_juego_raw
            FROM ( 
                SELECT id_caja, id_funcionario, 'Combinado' AS tipo_juego, 'COMBINADO' AS tipo_juego_raw, ope.numero_operacion, ope.id_distribuidor, cob.fecha, cob.hora, cob.id_tipo_valor, jue.fecha_sorteo, cob.monto, cob.id_estado, ope.id_juego
                FROM operacion_binrifa_detalle_cobro cob LEFT JOIN operacion_binrifa ope ON cob.id_operacion = ope.id LEFT JOIN juego_binrifa jue ON ope.id_juego = jue.id WHERE cob.id_estado = 464 AND cob.id_tipo_valor = 450
                UNION ALL 
                SELECT id_caja, id_funcionario, 'Bingo' AS tipo_juego, 'BINGO' AS tipo_juego_raw, ope.numero_operacion, ope.id_distribuidor, cob.fecha, cob.hora, cob.id_tipo_valor, jue.fecha_sorteo, cob.monto, cob.id_estado, ope.id_juego
                FROM operacion_bingo_detalle_cobro cob LEFT JOIN operacion_bingo ope ON cob.id_operacion = ope.id LEFT JOIN juego jue ON ope.id_juego = jue.id WHERE cob.id_estado = 464 AND cob.id_tipo_valor = 450
                UNION ALL 
                SELECT id_caja, id_funcionario, 'Rifa' AS tipo_juego, 'RIFA' AS tipo_juego_raw, ope.numero_operacion, ope.id_distribuidor, cob.fecha, cob.hora, cob.id_tipo_valor, jue.fecha_sorteo, cob.monto, cob.id_estado, ope.id_juego
                FROM operacion_rifa_detalle_cobro cob LEFT JOIN operacion_rifa ope ON cob.id_operacion = ope.id LEFT JOIN juego_rifa jue ON ope.id_juego = jue.id WHERE cob.id_estado = 464 AND cob.id_tipo_valor = 450
            ) AS ope 
            LEFT JOIN caja caj ON ope.id_caja = caj.id 
            LEFT JOIN funcionario fun ON ope.id_funcionario = fun.id 
            LEFT JOIN persona pef ON fun.id_persona = pef.id 
            LEFT JOIN distribuidor dis ON ope.id_distribuidor = dis.id 
            LEFT JOIN persona per ON dis.id_persona = per.id 
            LEFT JOIN tipo_detalle_subtipo tva ON ope.id_tipo_valor = tva.id 

            UNION ALL

            -- BLOQUE 2: Cobros
            SELECT 
                cob.id_caja, caj.numero_arqueo, caj.denominacion AS caja, cob.id_funcionario, 
                COALESCE(pef.nombre || ' ' || pef.apellido, '') AS funcionario, 
                '1' AS numero_tipo_movimiento, 'INGRESO' AS tipo_movimiento, 
                CASE WHEN cre.id IS NULL AND con.denominacion = 'APERTURA' THEN '1' ELSE '5' END AS numero_tipo_operacion,
                CASE WHEN cre.id IS NULL AND con.denominacion = 'APERTURA' THEN 'APERTURA' ELSE 'INGRESOS VARIOS' END AS tipo_operacion,
                CASE WHEN cre.id IS NULL THEN con.denominacion || ' - ' || cob.observacion ELSE 'Cobro Créd.Nº ' || cre.numero_credito END AS concepto,
                con.denominacion AS concepto_general, per.id AS id_persona, 
                COALESCE(per.nombre || ' ' || per.apellido, '') AS persona, 
                cob.numero_operacion, cob.fecha, cob.hora, tva.denominacion AS tipo_valor,
                '---' AS juego, cob.monto, 0.0 AS diferencia, NULL AS id_juego, NULL AS tipo_juego_raw
            FROM cobro cob
            LEFT JOIN caja caj ON cob.id_caja = caj.id 
            LEFT JOIN funcionario fun ON cob.id_funcionario = fun.id 
            LEFT JOIN persona pef ON fun.id_persona = pef.id 
            LEFT JOIN tipo_detalle_subtipo tva ON cob.id_tipo_valor = tva.id 
            LEFT JOIN tipo_detalle_subtipo con ON cob.id_concepto = con.id 
            LEFT JOIN persona per ON cob.id_persona = per.id 
            LEFT JOIN credito_cobro cre ON cob.id_credito = cre.id
            WHERE cob.id_estado = 464

            UNION ALL

            -- BLOQUE 3: Pagos
            SELECT 
                pag.id_caja, caj.numero_arqueo, caj.denominacion AS caja, pag.id_funcionario, 
                COALESCE(pef.nombre || ' ' || pef.apellido, '') AS funcionario, 
                '2' AS numero_tipo_movimiento, 'EGRESO' AS tipo_movimiento, 
                CASE WHEN cre.id IS NULL AND con.denominacion = 'RENDICION' THEN '4' ELSE '3' END AS numero_tipo_operacion,
                CASE WHEN cre.id IS NULL AND con.denominacion = 'RENDICION' THEN 'RENDICION' ELSE 'EGRESOS VARIOS' END AS tipo_operacion,
                CASE WHEN cre.id IS NULL THEN 'Pago: ' || con.denominacion || ' - ' || pag.referencia ELSE 'Pago Créd.Nº ' || cre.numero_credito END AS concepto,
                con.denominacion AS concepto_general, per.id AS id_persona, 
                COALESCE(per.nombre || ' ' || per.apellido, '') AS persona, 
                pag.numero_operacion, pag.fecha, pag.hora, tva.denominacion AS tipo_valor,
                '---' AS juego, COALESCE(det_pag.monto, pag.monto) AS monto, 0.0 AS diferencia, NULL AS id_juego, NULL AS tipo_juego_raw
            FROM pago pag
            LEFT JOIN (SELECT id_pago, SUM(monto) AS monto FROM pago_detalle GROUP BY id_pago) AS det_pag ON det_pag.id_pago = pag.id
            LEFT JOIN caja caj ON pag.id_caja = caj.id 
            LEFT JOIN funcionario fun ON pag.id_funcionario = fun.id 
            LEFT JOIN persona pef ON fun.id_persona = pef.id 
            LEFT JOIN persona per ON pag.id_persona = per.id 
            LEFT JOIN tipo_detalle_subtipo tva ON pag.id_tipo_valor = tva.id 
            LEFT JOIN tipo_detalle_subtipo con ON pag.id_concepto = con.id 
            LEFT JOIN credito_pago cre ON pag.id_credito = cre.id
            WHERE pag.id_estado = 489
        ) AS det
        LEFT JOIN caja caj ON det.id_caja = caj.id
        WHERE 1=1
          AND det.fecha BETWEEN %(fi)s AND %(ff)s
          {game_filter_sql}
          {where_extra}
        ORDER BY caj.denominacion, det.fecha, det.hora, det.numero_tipo_movimiento, det.numero_tipo_operacion
    """

    # Parámetros obligatorios
    params["fi"] = fecha_inicio
    params["ff"] = fecha_fin

    # 5. Ejecución segura
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(base_query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Limpieza de datos para JSON
        result = []
        for row in rows:
            clean_row = {}
            for k, v in dict(row).items():
                if hasattr(v, '__float__'):
                    clean_row[k] = float(v)
                else:
                    clean_row[k] = v
            result.append(clean_row)
            
        return result
        
    except Exception as e:
        if conn: conn.close()
        return {"error": str(e)}
    
# ============================================
# Endpoint 6: Estadística Venta (Fecha Inicio y Fin / Tipo Juego)
# ============================================   
@router.get("/estadistica-venta")
def estadistica_venta(
    fecha_sorteo_inicio: str = Query(..., description="Fecha inicio sorteo (YYYY-MM-DD)"),
    fecha_sorteo_fin: str = Query(..., description="Fecha fin sorteo (YYYY-MM-DD)"),
    tipo_juego: Optional[str] = Query(None, description="Filtrar por: bingo, combinado, rifa, super5, super10, animalitos")
):
    # 1. Validación de tipos de juego permitidos
    tipos_validos = ["bingo", "combinado", "rifa", "super5", "super10", "animalitos"]
    if tipo_juego and tipo_juego.lower() not in tipos_validos:
        return {"error": f"tipo_juego debe ser uno de: {tipos_validos}"}

    # 2. Construcción dinámica del UNION según el tipo de juego solicitado
    union_blocks = []
    
    # Mapeo exacto de tipos a sus tablas y nombres literales
    config_juegos = {
        "bingo": ("operacion_bingo", "juego", "'Bingo'"),
        "combinado": ("operacion_binrifa", "juego_binrifa", "'Combinado'"),
        "rifa": ("operacion_rifa", "juego_rifa", "'Rifa'"),
        "super5": ("operacion_bingo5", "juego_bingo5", "'Super 5'"),
        "super10": ("operacion_bingo10", "juego_bingo10", "'Super 10'"),
        "animalitos": ("operacion_bingo25", "juego_bingo25", "'Animalitos'")
    }

    # Determinar qué bloques incluir en el UNION ALL
    juegos_a_consultar = [tipo_juego.lower()] if tipo_juego else list(config_juegos.keys())

    for j_type in juegos_a_consultar:
        if j_type in config_juegos:
            op_table, jue_table, name_literal = config_juegos[j_type]
            block = f"""
                SELECT 
                    ope.id_distribuidor, {name_literal} AS juego, ju.fecha_sorteo, 
                    COALESCE(ret.cantidad, 0) AS retirado, COALESCE(dev.cantidad, 0) AS devuelto, 
                    ju.precio_carton, ope.comision,
                    ROUND((COALESCE(ret.cantidad, 0.0) - COALESCE(dev.cantidad, 0.0)) * ope.comision, 3) AS monto_comision,
                    ROUND((COALESCE(ret.cantidad, 0.0) - COALESCE(dev.cantidad, 0.0)) * (ju.precio_carton - ope.comision), 3) AS monto_a_rendir
                FROM {op_table} ope
                LEFT JOIN {jue_table} ju ON ope.id_juego = ju.id
                LEFT JOIN (SELECT id_operacion, COUNT(*) AS cantidad FROM {op_table}_detalle_retiro GROUP BY id_operacion) ret ON ret.id_operacion = ope.id
                LEFT JOIN (SELECT id_operacion, COUNT(*) AS cantidad FROM {op_table}_detalle_devolucion GROUP BY id_operacion) dev ON dev.id_operacion = ope.id
                WHERE ju.fecha_sorteo BETWEEN %(fsi)s AND %(fsf)s 
                  AND ope.id_estado = 437 
                  AND ope.rendido = true
            """
            union_blocks.append(block)

    if not union_blocks:
        return {"error": "Tipo de juego no reconocido"}

    base_union = "\nUNION ALL\n".join(union_blocks)

    # 3. Consulta Principal (Estructura idéntica a tu SQL original)
    final_query = f"""
        SELECT 
            j.juego || ' ' || to_char(j.fecha_sorteo, 'DD/MM/YYYY') AS juego,
            j.fecha_sorteo,
            ROW_NUMBER() OVER (
                PARTITION BY j.fecha_sorteo 
                ORDER BY ped.nombre, ped.apellido
            ) AS item,
            ped.nombre || ' ' || ped.apellido AS distribuidor,
            j.retirado,
            j.devuelto,
            j.retirado - j.devuelto AS vendido,
            j.precio_carton,
            j.comision,
            j.monto_comision,
            j.monto_a_rendir
        FROM (
            {base_union}
        ) AS j
        LEFT JOIN distribuidor di ON j.id_distribuidor = di.id
        LEFT JOIN persona ped ON di.id_persona = ped.id
        ORDER BY 
            j.fecha_sorteo, 
            j.juego, 
            ped.nombre, 
            ped.apellido
    """

    params = {"fsi": fecha_sorteo_inicio, "fsf": fecha_sorteo_fin}

    # 4. Ejecución segura
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(final_query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Limpieza de datos para JSON (Decimal -> float)
        result = []
        for row in rows:
            clean_row = {}
            for k, v in dict(row).items():
                if hasattr(v, '__float__'):
                    clean_row[k] = float(v)
                else:
                    clean_row[k] = v
            result.append(clean_row)
            
        return result
        
    except Exception as e:
        if conn: conn.close()
        return {"error": str(e)}