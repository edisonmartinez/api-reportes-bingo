from fastapi import APIRouter, HTTPException
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

# ============================================
# Endpoint 4: ListadoRendicion (TIPO JUEGO / FECHA SORTEO)
# ============================================
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
    
    elif tipo_juego == "rifa":
        query = """
            SELECT
                ope.numero_operacion,
                ped.nombre||' '||ped.apellido AS distribuidor,
                CASE WHEN ope.rendido=true THEN 'SI' ELSE 'NO' END AS rendido,
                COALESCE(ret.cantidad,0) AS retirado,
                COALESCE(dev.cantidad,0) AS devuelto,
                CASE
                    WHEN ope.rendido=true THEN COALESCE(ret.cantidad,0)-COALESCE(dev.cantidad,0)
                    ELSE 0
                END AS vendido,
                ju.precio_carton,
                ope.comision,
                (COALESCE(ret.cantidad,0.0)-COALESCE(dev.cantidad,0.0))*ope.comision AS monto_comision,
                (COALESCE(ret.cantidad,0.0)-COALESCE(dev.cantidad,0.0))*(ju.precio_carton-ope.comision) AS monto_a_rendir,
                COALESCE(cobef.monto,0.0) AS monto_efectivo,
                COALESCE(cobcr.monto,0.0) AS monto_credito,
                COALESCE(cobgi.monto,0.0) AS monto_telefonia,
                COALESCE(cobot.monto,0.0) AS monto_otro
            FROM operacion_rifa ope
            LEFT JOIN juego_rifa ju ON ope.id_juego = ju.id
            LEFT JOIN distribuidor di ON ope.id_distribuidor = di.id
            LEFT JOIN persona ped ON di.id_persona = ped.id
            LEFT JOIN (
                SELECT id_operacion, COUNT(*) AS cantidad
                FROM operacion_rifa_detalle_retiro
                GROUP BY id_operacion
            ) AS ret ON ret.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, COUNT(*) AS cantidad
                FROM operacion_rifa_detalle_devolucion
                GROUP BY id_operacion
            ) AS dev ON dev.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, SUM(monto) AS monto
                FROM operacion_rifa_detalle_cobro
                WHERE id_estado=464 AND id_tipo_valor=450
                GROUP BY id_operacion
            ) AS cobef ON cobef.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, SUM(monto) AS monto
                FROM operacion_rifa_detalle_cobro
                WHERE id_estado=464 AND id_tipo_valor=456
                GROUP BY id_operacion
            ) AS cobcr ON cobcr.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, SUM(monto) AS monto
                FROM operacion_rifa_detalle_cobro
                WHERE id_estado=464 AND id_tipo_valor=455
                GROUP BY id_operacion
            ) AS cobgi ON cobgi.id_operacion = ope.id
            LEFT JOIN (
                SELECT id_operacion, SUM(monto) AS monto
                FROM operacion_rifa_detalle_cobro
                WHERE id_estado=464 AND id_tipo_valor=454
                GROUP BY id_operacion
            ) AS cobot ON cobot.id_operacion = ope.id
            WHERE ope.id_juego = (SELECT id FROM juego_rifa WHERE fecha_sorteo = %s) 
            AND ope.id_estado=437
            ORDER BY ped.nombre, ped.apellido;
        """

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
# Endpoint 5: MovimientoCaja (FECHA INICIO, FECHA FIN)
# ============================================
@router.get("/arqueo-caja")
def arqueo_caja(
    fecha_inicio: str = Query(..., description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(..., description="Fecha fin (YYYY-MM-DD)"),
    tipo_juego: Optional[str] = Query(None, description="Filtrar por: bingo, combinado o rifa"),
    fecha_sorteo_inicio: Optional[str] = Query(None, description="Inicio rango sorteo (YYYY-MM-DD)"),
    fecha_sorteo_fin: Optional[str] = Query(None, description="Fin rango sorteo (YYYY-MM-DD)"),
    tipo_valor: Optional[str] = Query(None, description="Texto para buscar en tipo_valor (LIKE)"),
    tipo_movimiento: Optional[str] = Query(None, description="INGRESO o EGRESO"),
    tipo_operacion: Optional[str] = Query(None, description="Ej: PREMIO, VARIOS, CREDITO NORMAL, CREDITO VENTA, VENTA DIRECTA"),
    concepto: Optional[str] = Query(None, description="Texto para buscar en concepto (LIKE)")
):
    
    # 1. Validaciones básicas
    tipos_validos = ["bingo", "combinado", "rifa"]
    if tipo_juego and tipo_juego.lower() not in tipos_validos:
        return {"error": f"tipo_juego debe ser uno de: {tipos_validos}"}

    # 2. Construcción dinámica del WHERE según el tipo de juego seleccionado
    # Esto permite filtrar por las tablas nativas sin parsear texto
    game_filter_sql = ""
    params = {}

    if tipo_juego == "bingo":
        game_filter_sql = """
            AND EXISTS (SELECT 1 FROM juego j WHERE j.id = ope.id_juego AND j.fecha_sorteo BETWEEN :fsi AND :fsf)
        """
    elif tipo_juego == "combinado":
        game_filter_sql = """
            AND EXISTS (SELECT 1 FROM juego_binrifa j WHERE j.id = ope.id_juego AND j.fecha_sorteo BETWEEN :fsi AND :fsf)
        """
    elif tipo_juego == "rifa":
        game_filter_sql = """
            AND EXISTS (SELECT 1 FROM juego_rifa j WHERE j.id = ope.id_juego AND j.fecha_sorteo BETWEEN :fsi AND :fsf)
        """
    
    # Si no hay filtro de juego pero sí fechas de sorteo, buscamos en todas las tablas
    elif not tipo_juego and (fecha_sorteo_inicio or fecha_sorteo_fin):
        game_filter_sql = """
            AND (
                EXISTS (SELECT 1 FROM juego j WHERE j.id = ope.id_juego AND j.fecha_sorteo BETWEEN :fsi AND :fsf) OR
                EXISTS (SELECT 1 FROM juego_binrifa j WHERE j.id = ope.id_juego AND j.fecha_sorteo BETWEEN :fsi AND :fsf) OR
                EXISTS (SELECT 1 FROM juego_rifa j WHERE j.id = ope.id_juego AND j.fecha_sorteo BETWEEN :fsi AND :fsf)
            )
        """

    # Parámetros de fechas de sorteo (si se usan)
    if fecha_sorteo_inicio: params["fsi"] = fecha_sorteo_inicio
    if fecha_sorteo_fin: params["fsf"] = fecha_sorteo_fin
    
    # Ajuste de LIKE para tipo_valor, concepto y tipo_operacion
    like_clauses = []
    if tipo_valor:
        like_clauses.append("UPPER(tva.denominacion) LIKE UPPER(:tv)")
        params["tv"] = f"%{tipo_valor}%"
    if tipo_movimiento:
        like_clauses.append("UPPER(det.tipo_movimiento) = UPPER(:tm)")
        params["tm"] = tipo_movimiento
    if tipo_operacion:
        like_clauses.append("UPPER(det.tipo_operacion) LIKE UPPER(:to)")
        params["to"] = f"%{tipo_operacion}%"
    if concepto:
        like_clauses.append("UPPER(det.concepto) LIKE UPPER(:con)")
        params["con"] = f"%{concepto}%"

    extra_filters = " AND ".join(like_clauses)
    if extra_filters:
        extra_filters = f" AND {extra_filters}"

    # 3. Consulta Base con UNION y numeración correlativa ITEM
    base_query = f"""
        SELECT 
            ROW_NUMBER() OVER (ORDER BY det.caja, det.fecha, det.hora, det.numero_tipo_movimiento, det.numero_tipo_operacion) AS item,
            det.*
        FROM (
            -- BLOQUE 1: Ventas Directas (UNION de todos los juegos)
            SELECT 
                ope.id_caja, caj.numero_arqueo, caj.denominacion AS caja, 
                ope.id_funcionario, COALESCE(pef.nombre || ' ' || pef.apellido, '') AS funcionario,
                '1' AS numero_tipo_movimiento, 'INGRESO' AS tipo_movimiento,
                '2' AS numero_tipo_operacion, 'INGRESO VENTA DIRECTA' AS tipo_operacion,
                'Venta de cartón: Rendición' AS concepto, 'CONTADO VENTA' AS concepto_general,
                per.id AS id_persona, COALESCE(per.nombre || ' ' || per.apellido, '') AS persona,
                ope.numero_operacion, cob.fecha, cob.hora, tva.denominacion AS tipo_valor,
                ope.tipo_juego || ' ' || to_char(jue.fecha_sorteo, 'DD/MM/YY') AS juego,
                cob.monto
            FROM (
                SELECT id_caja, id_funcionario, 'Combinado' AS tipo_juego, ope.numero_operacion, ope.id_distribuidor, cob.fecha, cob.hora, cob.id_tipo_valor, jue.fecha_sorteo, cob.monto, cob.id_estado, ope.id_juego
                FROM operacion_binrifa_detalle_cobro cob LEFT JOIN operacion_binrifa ope ON cob.id_operacion = ope.id LEFT JOIN juego_binrifa jue ON ope.id_juego = jue.id
                UNION ALL
                SELECT id_caja, id_funcionario, 'Bingo' AS tipo_juego, ope.numero_operacion, ope.id_distribuidor, cob.fecha, cob.hora, cob.id_tipo_valor, jue.fecha_sorteo, cob.monto, cob.id_estado, ope.id_juego
                FROM operacion_bingo_detalle_cobro cob LEFT JOIN operacion_bingo ope ON cob.id_operacion = ope.id LEFT JOIN juego jue ON ope.id_juego = jue.id
                UNION ALL
                SELECT id_caja, id_funcionario, 'Rifa' AS tipo_juego, ope.numero_operacion, ope.id_distribuidor, cob.fecha, cob.hora, cob.id_tipo_valor, jue.fecha_sorteo, cob.monto, cob.id_estado, ope.id_juego
                FROM operacion_rifa_detalle_cobro cob LEFT JOIN operacion_rifa ope ON cob.id_operacion = ope.id LEFT JOIN juego_rifa jue ON ope.id_juego = jue.id
            ) AS ope
            LEFT JOIN caja caj ON ope.id_caja = caj.id
            LEFT JOIN funcionario fun ON ope.id_funcionario = fun.id
            LEFT JOIN persona pef ON fun.id_persona = pef.id
            LEFT JOIN distribuidor dis ON ope.id_distribuidor = dis.id
            LEFT JOIN persona per ON dis.id_persona = per.id
            LEFT JOIN tipo_detalle_subtipo tva ON ope.id_tipo_valor = tva.id
            WHERE ope.id_estado = 464 AND ope.id_tipo_valor = 450
              AND cob.fecha BETWEEN :fi AND :ff
              {game_filter_sql}

            UNION ALL

            -- BLOQUE 2: Cobros
            SELECT 
                cob.id_caja, caj.numero_arqueo, caj.denominacion AS caja,
                cob.id_funcionario, COALESCE(pef.nombre || ' ' || pef.apellido, '') AS funcionario,
                '1' AS numero_tipo_movimiento, 'INGRESO' AS tipo_movimiento,
                CASE WHEN cre.id IS NULL AND con.denominacion = 'APERTURA' THEN '1' ELSE '5' END AS numero_tipo_operacion,
                CASE WHEN cre.id IS NULL AND con.denominacion = 'APERTURA' THEN 'APERTURA' ELSE 'INGRESOS VARIOS' END AS tipo_operacion,
                CASE WHEN cre.id IS NULL THEN con.denominacion || ' - ' || cob.observacion ELSE 'Cobro Créd.Nº ' || cre.numero_credito END AS concepto,
                con.denominacion AS concepto_general,
                per.id AS id_persona, COALESCE(per.nombre || ' ' || per.apellido, '') AS persona,
                cob.numero_operacion, cob.fecha, cob.hora, tva.denominacion AS tipo_valor,
                '---' AS juego, cob.monto
            FROM cobro cob
            LEFT JOIN caja caj ON cob.id_caja = caj.id
            LEFT JOIN funcionario fun ON cob.id_funcionario = fun.id
            LEFT JOIN persona pef ON fun.id_persona = pef.id
            LEFT JOIN tipo_detalle_subtipo tva ON cob.id_tipo_valor = tva.id
            LEFT JOIN tipo_detalle_subtipo con ON cob.id_concepto = con.id
            LEFT JOIN persona per ON cob.id_persona = per.id
            LEFT JOIN credito_cobro cre ON cob.id_credito = cre.id
            WHERE cob.id_estado = 464
              AND cob.fecha BETWEEN :fi AND :ff
              {game_filter_sql}

            UNION ALL

            -- BLOQUE 3: Pagos
            SELECT 
                pag.id_caja, caj.numero_arqueo, caj.denominacion AS caja,
                pag.id_funcionario, COALESCE(pef.nombre || ' ' || pef.apellido, '') AS funcionario,
                '2' AS numero_tipo_movimiento, 'EGRESO' AS tipo_movimiento,
                CASE WHEN cre.id IS NULL AND con.denominacion = 'RENDICION' THEN '4' ELSE '3' END AS numero_tipo_operacion,
                CASE WHEN cre.id IS NULL AND con.denominacion = 'RENDICION' THEN 'RENDICION' ELSE 'EGRESOS VARIOS' END AS tipo_operacion,
                CASE WHEN cre.id IS NULL THEN 'Pago: ' || con.denominacion || ' - ' || pag.referencia ELSE 'Pago Créd.Nº ' || cre.numero_credito END AS concepto,
                con.denominacion AS concepto_general,
                per.id AS id_persona, COALESCE(per.nombre || ' ' || per.apellido, '') AS persona,
                pag.numero_operacion, pag.fecha, pag.hora, tva.denominacion AS tipo_valor,
                '---' AS juego, pag.monto
            FROM pago pag
            LEFT JOIN caja caj ON pag.id_caja = caj.id
            LEFT JOIN funcionario fun ON pag.id_funcionario = fun.id
            LEFT JOIN persona pef ON fun.id_persona = pef.id
            LEFT JOIN persona per ON pag.id_persona = per.id
            LEFT JOIN tipo_detalle_subtipo tva ON pag.id_tipo_valor = tva.id
            LEFT JOIN tipo_detalle_subtipo con ON pag.id_concepto = con.id
            LEFT JOIN credito_pago cre ON pag.id_credito = cre.id
            WHERE pag.id_estado = 489
              AND pag.fecha BETWEEN :fi AND :ff
              {game_filter_sql}
              
        ) AS det
        WHERE 1=1 {extra_filters}
        ORDER BY det.caja, det.fecha, det.hora, det.numero_tipo_movimiento, det.numero_tipo_operacion
    """

    # Agregar parámetros obligatorios de fecha general
    params["fi"] = fecha_inicio
    params["ff"] = fecha_fin

    # 4. Ejecución segura
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(base_query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convertir Decimal a float para JSON nativo
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
    