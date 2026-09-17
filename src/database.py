# src/database.py
import os
import sys
import sqlite3
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maestra_productos (
            codigo TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            unidad TEXT DEFAULT 'Unidad',
            precio REAL DEFAULT 0.0,
            ubicacion TEXT DEFAULT 'Bodega Central',
            stock_minimo INTEGER DEFAULT 5
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historial_movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_hora TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            codigo TEXT NOT NULL,
            tipo TEXT NOT NULL,
            cantidad INTEGER DEFAULT 1,
            FOREIGN KEY (codigo) REFERENCES maestra_productos (codigo)
        )
    ''')
    conn.commit()
    conn.close()

def obtener_maestra():
    conn = get_connection()
    query = '''
        SELECT 
            p.codigo AS "Código Barcode",
            p.nombre AS "Nombre Producto",
            p.categoria AS "Categoría",
            p.unidad AS "Unidad",
            p.ubicacion AS "Ubicación",
            p.precio AS "Precio ($)",
            p.stock_minimo AS "Stock Min",
            COALESCE(SUM(
                CASE 
                    WHEN h.tipo IN ('ENTRADA', 'AJUSTE_POSITIVO') THEN h.cantidad 
                    WHEN h.tipo IN ('SALIDA', 'AJUSTE_NEGATIVO') THEN -h.cantidad 
                    ELSE 0 
                END
            ), 0) AS "Stock Actual"
        FROM maestra_productos p
        LEFT JOIN historial_movimientos h ON p.codigo = h.codigo
        GROUP BY p.codigo
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def buscar_producto_por_codigo(codigo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, nombre, categoria, unidad, ubicacion FROM maestra_productos WHERE codigo = ?", (codigo.strip(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"codigo": row[0], "nombre": row[1], "categoria": row[2], "unidad": row[3], "ubicacion": row[4]}
    return None

def registrar_producto_maestra(codigo, nombre, categoria, unidad, precio, ubicacion, stock_minimo, stock_inicial=0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO maestra_productos (codigo, nombre, categoria, unidad, precio, ubicacion, stock_minimo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (codigo.strip(), nombre.strip(), categoria, unidad, precio, ubicacion.strip(), stock_minimo))
    
    if stock_inicial > 0:
        cursor.execute('''
            INSERT INTO historial_movimientos (codigo, tipo, cantidad)
            VALUES (?, 'ENTRADA', ?)
        ''', (codigo.strip(), stock_inicial))
        
    conn.commit()
    conn.close()

def actualizar_producto_maestra(codigo, nombre, categoria, unidad, precio, ubicacion, stock_minimo, nuevo_stock=None):
    """Actualiza datos del producto y registra un ajuste si cambia el stock."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE maestra_productos
        SET nombre = ?, categoria = ?, unidad = ?, precio = ?, ubicacion = ?, stock_minimo = ?
        WHERE codigo = ?
    ''', (nombre.strip(), categoria, unidad, precio, ubicacion.strip(), stock_minimo, codigo.strip()))
    
    if nuevo_stock is not None:
        cursor.execute('''
            SELECT COALESCE(SUM(
                CASE 
                    WHEN tipo IN ('ENTRADA', 'AJUSTE_POSITIVO') THEN cantidad 
                    WHEN tipo IN ('SALIDA', 'AJUSTE_NEGATIVO') THEN -cantidad 
                    ELSE 0 
                END
            ), 0)
            FROM historial_movimientos
            WHERE codigo = ?
        ''', (codigo.strip(),))
        
        stock_actual_bd = cursor.fetchone()[0] or 0
        diferencia = nuevo_stock - stock_actual_bd
        
        if diferencia != 0:
            tipo_ajuste = "AJUSTE_POSITIVO" if diferencia > 0 else "AJUSTE_NEGATIVO"
            cant_ajuste = abs(diferencia)
            cursor.execute('''
                INSERT INTO historial_movimientos (codigo, tipo, cantidad)
                VALUES (?, ?, ?)
            ''', (codigo.strip(), tipo_ajuste, cant_ajuste))

    conn.commit()
    conn.close()

def eliminar_producto_maestra(codigo):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historial_movimientos WHERE codigo = ?", (codigo.strip(),))
    cursor.execute("DELETE FROM maestra_productos WHERE codigo = ?", (codigo.strip(),))
    conn.commit()
    conn.close()

def registrar_disparo_escanner(codigo, tipo, cantidad=1):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO historial_movimientos (codigo, tipo, cantidad)
        VALUES (?, ?, ?)
    ''', (codigo.strip(), tipo, cantidad))
    conn.commit()
    conn.close()

def obtener_historial_completo(filtro_tipo="TODOS"):
    conn = get_connection()
    if filtro_tipo == "TODOS":
        query = '''
            SELECT 
                h.id AS "ID",
                h.fecha_hora AS "Fecha / Hora",
                h.codigo AS "Código Escaneado",
                COALESCE(p.nombre, 'PRODUCTO DESCONOCIDO') AS "Producto",
                COALESCE(p.unidad, '-') AS "Unidad",
                h.tipo AS "Tipo Movimiento",
                h.cantidad AS "Cantidad"
            FROM historial_movimientos h
            LEFT JOIN maestra_productos p ON h.codigo = p.codigo
            ORDER BY h.id DESC
        '''
        df = pd.read_sql_query(query, conn)
    else:
        query = '''
            SELECT 
                h.id AS "ID",
                h.fecha_hora AS "Fecha / Hora",
                h.codigo AS "Código Escaneado",
                COALESCE(p.nombre, 'PRODUCTO DESCONOCIDO') AS "Producto",
                COALESCE(p.unidad, '-') AS "Unidad",
                h.tipo AS "Tipo Movimiento",
                h.cantidad AS "Cantidad"
            FROM historial_movimientos h
            LEFT JOIN maestra_productos p ON h.codigo = p.codigo
            WHERE h.tipo = ?
            ORDER BY h.id DESC
        '''
        df = pd.read_sql_query(query, conn, params=(filtro_tipo,))
    conn.close()
    return df

def actualizar_movimiento_historial(id_movimiento, tipo, cantidad):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE historial_movimientos
        SET tipo = ?, cantidad = ?
        WHERE id = ?
    ''', (tipo, cantidad, id_movimiento))
    conn.commit()
    conn.close()

def eliminar_movimiento_historial(id_movimiento):
    """Elimina un único registro específico del historial."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM historial_movimientos WHERE id = ?", (id_movimiento,))
    conn.commit()
    conn.close()