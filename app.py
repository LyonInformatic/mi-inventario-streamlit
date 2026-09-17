# app.py
import streamlit as st
import config
from src.database import (
    init_db,
    obtener_maestra,
    buscar_producto_por_codigo,
    registrar_producto_maestra,
    actualizar_producto_maestra,
    eliminar_producto_maestra,
    registrar_disparo_escanner,
    obtener_historial_completo,
    actualizar_movimiento_historial,
    eliminar_movimiento_historial
)

st.set_page_config(page_title="Pistola Scanner & Inventario", page_icon="📦", layout="wide")

# Inicialización de la Base de Datos
init_db()

st.title("📦 Sistema de Gestión por Lectura Barcode")

# Pestañas Principales
tab_escanner, tab_maestra, tab_historial = st.tabs([
    "🔫 Lectura / Pistola",
    "🗂️ Maestra de Productos",
    "📜 Historial de Movimientos"
])

# ---------------------------------------------------------
# VISTA 1: OPERACIÓN CON PISTOLA LECTORA
# ---------------------------------------------------------
with tab_escanner:
    st.subheader("Entradas y Salidas con Escáner")
    
    col_modo, col_cant = st.columns([2, 1])
    tipo_movimiento = col_modo.radio("Seleccionar Operación:", ["ENTRADA", "SALIDA"], horizontal=True)
    cantidad_unidades = col_cant.number_input("Cantidad por lectura", min_value=1, value=1, step=1)
    
    st.info("💡 Coloca el cursor en la casilla inferior y dispara la pistola lectora.")
    
    with st.form("form_escanner", clear_on_submit=True):
        codigo_escaneado = st.text_input("Código de Barras (EAN / SKU):", key="barcode_input", autocomplete="off")
        submit_scan = st.form_submit_button("⚡ Registrar Lectura")
        
        if submit_scan and codigo_escaneado.strip():
            codigo_clean = codigo_escaneado.strip()
            prod = buscar_producto_por_codigo(codigo_clean)
            
            if prod:
                registrar_disparo_escanner(codigo_clean, tipo_movimiento, cantidad_unidades)
                st.success(f"✅ {tipo_movimiento} REGISTRADA: **{prod['nombre']}** ({cantidad_unidades} {prod['unidad']})")
                st.toast(f"{tipo_movimiento}: {prod['nombre']}", icon="✅")
                if "codigo_pendiente" in st.session_state:
                    del st.session_state["codigo_pendiente"]
            else:
                st.session_state["codigo_pendiente"] = codigo_clean
                st.session_state["tipo_pendiente"] = tipo_movimiento
                st.session_state["cant_pendiente"] = cantidad_unidades

    # Alta Rápida si el código no existe en el flujo del escáner
    if "codigo_pendiente" in st.session_state:
        cod_pend = st.session_state["codigo_pendiente"]
        tipo_pend = st.session_state["tipo_pendiente"]
        cant_pend = st.session_state["cant_pendiente"]
        
        st.warning(f"⚠️ El código **{cod_pend}** no existe en la Maestra de Productos.")
        st.markdown(f"### 📝 Alta Rápida de Producto para el Código: `{cod_pend}`")
        
        with st.form("form_alta_rapida", clear_on_submit=True):
            col1, col2, col3 = st.columns([2, 1, 1])
            nombre_rapido = col1.text_input("Nombre del Producto *")
            cat_rapida = col2.selectbox("Categoría", config.CATEGORIAS)
            unidad_rapida = col3.selectbox("Unidad de Medida", config.UNIDADES_MEDIDA)
            
            col4, col5, col6 = st.columns(3)
            prec_rapido = col4.number_input("Precio ($)", min_value=0.0, step=0.5)
            ubi_rapida = col5.text_input("Ubicación", value="Bodega Central")
            min_rapido = col6.number_input("Stock Mínimo Alerta", min_value=1, value=5)
            
            sub_rapido = st.form_submit_button("💾 Guardar en Maestra y Procesar Movimiento")
            
            if sub_rapido:
                if nombre_rapido.strip():
                    try:
                        registrar_producto_maestra(
                            cod_pend, nombre_rapido.strip(), cat_rapida, 
                            unidad_rapida, prec_rapido, ubi_rapida.strip(), min_rapido, cant_pend
                        )
                        st.success(f"🎉 Producto '{nombre_rapido}' creado ({unidad_rapida}) con Stock de {cant_pend} unidades.")
                        del st.session_state["codigo_pendiente"]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                else:
                    st.error("El nombre del producto es obligatorio.")

# ---------------------------------------------------------
# VISTA 2: MAESTRA DE PRODUCTOS
# ---------------------------------------------------------
with tab_maestra:
    st.subheader("Catálogo Maestro y Control de Stock")
    df_m = obtener_maestra()
    
    if not df_m.empty:
        st.dataframe(df_m, use_container_width=True)
    else:
        st.info("La Maestra está vacía.")
        
    st.divider()
    
    subtab_alta, subtab_edit, subtab_baja = st.tabs([
        "➕ Registrar Nuevo", 
        "✏️ Editar Producto", 
        "🗑️ Eliminar Producto"
    ])
    
    # --- SUB-TAB: REGISTRAR NUEVO (CON ESCÁNER Y STOCK INICIAL) ---
    with subtab_alta:
        st.markdown("### ➕ Registrar Producto Manual o por Escáner")
        st.caption("💡 Puedes usar la pistola lectora directamente sobre la casilla 'Código EAN / SKU / Barcode'.")
        
        with st.form("form_alta_maestra", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cod_new = c1.text_input("Código EAN / SKU / Barcode *", key="input_alta_barcode", autocomplete="off")
            nom_new = c2.text_input("Nombre del Producto *")
            
            c3, c4, c5 = st.columns(3)
            cat_new = c3.selectbox("Categoría", config.CATEGORIAS)
            uni_new = c4.selectbox("Unidad de Medida", config.UNIDADES_MEDIDA)
            prec_new = c5.number_input("Precio ($)", min_value=0.0, step=0.5)
            
            c6, c7, c8 = st.columns(3)
            ubi_new = c6.text_input("Ubicación", value="Estante A1")
            stock_ini = c7.number_input("Stock Inicial (Cantidad)", min_value=0, value=0, step=1)
            stock_min = c8.number_input("Stock Mínimo Alerta", min_value=1, value=5)
            
            if st.form_submit_button("💾 Guardar en Maestra"):
                if cod_new.strip() and nom_new.strip():
                    try:
                        registrar_producto_maestra(
                            cod_new, nom_new, cat_new, uni_new, prec_new, ubi_new, stock_min, stock_ini
                        )
                        st.success(f"✅ Producto '{nom_new}' ({uni_new}) guardado con Stock Inicial: {stock_ini}")
                        st.rerun()
                    except Exception:
                        st.error("El código ya existe en la Maestra.")
                else:
                    st.error("El Código de Barras y el Nombre son obligatorios.")

    # --- SUB-TAB: EDITAR PRODUCTO ---
    with subtab_edit:
        st.markdown("### ✏️ Modificar Producto Existente")
        if not df_m.empty:
            codigos_lista = df_m["Código Barcode"].tolist()
            cod_sel = st.selectbox("Selecciona el Código de Barras a Modificar:", codigos_lista)
            
            row_edit = df_m[df_m["Código Barcode"] == cod_sel].iloc[0]
            stock_actual = int(row_edit["Stock Actual"])
            
            with st.form("form_edit_maestra"):
                st.caption(f"Editando producto con Código: **{cod_sel}**")
                
                c1, c2 = st.columns(2)
                nom_edit = c1.text_input("Nombre del Producto", value=str(row_edit["Nombre Producto"]))
                
                cat_idx = config.CATEGORIAS.index(row_edit["Categoría"]) if row_edit["Categoría"] in config.CATEGORIAS else 0
                uni_idx = config.UNIDADES_MEDIDA.index(row_edit["Unidad"]) if row_edit["Unidad"] in config.UNIDADES_MEDIDA else 0
                
                cat_edit = c2.selectbox("Categoría", config.CATEGORIAS, index=cat_idx)
                
                c3, c4 = st.columns(2)
                uni_edit = c3.selectbox("Unidad de Medida", config.UNIDADES_MEDIDA, index=uni_idx)
                prec_edit = c4.number_input("Precio ($)", min_value=0.0, value=float(row_edit["Precio ($)"]), step=0.5)
                
                c5, c6, c7 = st.columns(3)
                ubi_edit = c5.text_input("Ubicación", value=str(row_edit["Ubicación"]))
                stock_edit = c6.number_input("Stock Actual", min_value=0, value=stock_actual, step=1)
                stock_min_edit = c7.number_input("Stock Mínimo Alerta", min_value=1, value=int(row_edit["Stock Min"]))
                
                if st.form_submit_button("💾 Actualizar Producto"):
                    if nom_edit.strip():
                        # Se pasa stock_edit directamente a la función
                        actualizar_producto_maestra(
                            cod_sel, nom_edit, cat_edit, uni_edit, prec_edit, ubi_edit, stock_min_edit, stock_edit
                        )
                        st.success(f"✅ Producto **{cod_sel}** actualizado correctamente.")
                        st.rerun()
                    else:
                        st.error("El nombre del producto no puede estar vacío.")
        else:
            st.info("No hay productos en la Maestra para modificar.")

    # --- SUB-TAB: ELIMINAR PRODUCTO ---
    with subtab_baja:
        st.markdown("### 🗑️ Eliminar Producto")
        if not df_m.empty:
            cod_eliminar = st.selectbox("Selecciona Código a Eliminar", df_m["Código Barcode"].tolist(), key="select_elim")
            if st.button("Confirmar Eliminación", type="primary"):
                eliminar_producto_maestra(cod_eliminar)
                st.success(f"Código {cod_eliminar} eliminado.")
                st.rerun()

# ---------------------------------------------------------
# VISTA 3: HISTORIAL Y GESTIÓN DE REGISTROS
# ---------------------------------------------------------
with tab_historial:
    st.subheader("Historial Completo de Movimientos")
    
    filtro = st.selectbox("Filtrar por Tipo:", ["TODOS", "ENTRADA", "SALIDA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO"])
    df_h = obtener_historial_completo(filtro)
    
    if not df_h.empty:
        st.dataframe(df_h, use_container_width=True)
        st.divider()
        
        subhist_edit, subhist_del = st.tabs([
            "✏️ Modificar Registro por ID", 
            "🗑️ Eliminar Registro Erróneo por ID"
        ])
        
        # --- MODIFICAR REGISTRO ---
        with subhist_edit:
            st.markdown("### ✏️ Corregir Datos de un Registro")
            list_ids = df_h["ID"].tolist()
            id_sel = st.selectbox("Selecciona el ID del Movimiento a corregir:", list_ids)
            
            row_h = df_h[df_h["ID"] == id_sel].iloc[0]
            st.caption(f"Editando ID `{id_sel}` — Producto: **{row_h['Producto']}** (`{row_h['Código Escaneado']}`)")
            
            with st.form("form_edit_historial"):
                col1, col2 = st.columns(2)
                tipos_opciones = ["ENTRADA", "SALIDA", "AJUSTE_POSITIVO", "AJUSTE_NEGATIVO"]
                idx_tipo = tipos_opciones.index(row_h["Tipo Movimiento"]) if row_h["Tipo Movimiento"] in tipos_opciones else 0
                
                tipo_nuevo = col1.selectbox("Tipo de Movimiento Correcto:", tipos_opciones, index=idx_tipo)
                cant_nueva = col2.number_input("Cantidad Correcta:", min_value=1, value=int(row_h["Cantidad"]), step=1)
                
                if st.form_submit_button("💾 Guardar Corrección"):
                    actualizar_movimiento_historial(id_sel, tipo_nuevo, cant_nueva)
                    st.success(f"✅ Registro ID {id_sel} corregido.")
                    st.rerun()
                    
        # --- ELIMINAR REGISTRO ---
        with subhist_del:
            st.markdown("### 🗑️ Eliminar Registro del Historial")
            st.warning("⚠️ Al borrar este registro, el Stock Actual del producto se recalculará automáticamente.")
            
            id_del = st.selectbox("Selecciona el ID del Registro a Eliminar:", df_h["ID"].tolist(), key="select_del_hist")
            row_del = df_h[df_h["ID"] == id_del].iloc[0]
            st.caption(f"Registro a borrar: ID `{id_del}` — **{row_del['Producto']}** | Tipo: **{row_del['Tipo Movimiento']}** | Cantidad: **{row_del['Cantidad']}**")
            
            if st.button("Confirmar Eliminación del Registro", type="primary"):
                eliminar_movimiento_historial(id_del)
                st.success(f"✅ Registro ID {id_del} eliminado del historial.")
                st.rerun()
                
    else:
        st.info("No hay registros en el historial.")