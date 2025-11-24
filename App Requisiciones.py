import streamlit as st
import pandas as pd
from datetime import datetime
import time

ALMACEN_PASSWORD = st.secrets["ALMACEN_PASSWORD"]


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

CSV_PATH = "data/requisiciones.csv"

st.set_page_config(page_title="Sistema de Requisiciones", layout="wide")

# =============================
# ENCABEZADO CORPORATIVO
# =============================

st.markdown("""
    <style>
        .encabezado-container {
            width: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 25px 0 20px 0;
            margin-bottom: -10px;
        }
        .titulo-nordson {
            font-size: 38px;
            font-weight: 600;
            color: #0072CE; /* Azul Nordson */
            font-family: Arial, Helvetica, sans-serif;
            letter-spacing: 1px;
        }
        .subtitulo-nordson {
            font-size: 20px;
            font-weight: 400;
            color: #555555;
            font-family: Arial, Helvetica, sans-serif;
            margin-top: -8px;
            letter-spacing: 0.5px;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="encabezado-container">
    <div class="titulo-nordson">NORDSON MEDICAL</div>
    <div class="subtitulo-nordson">Sistema de Requisiciones</div>
</div>
""", unsafe_allow_html=True)

# ============================================================
# FUNCIONES DE DATOS
# ============================================================

def cargar_datos():
    return pd.read_csv(CSV_PATH)

def guardar_datos(df):
    df.to_csv(CSV_PATH, index=False)

def generar_id():
    df = cargar_datos()

    if "ID" not in df.columns or df.empty:
        return "REQ-0001"

    # Extraer solo el número
    numeros = df["ID"].str.replace("REQ-", "").astype(int)

    nuevo_num = numeros.max() + 1

    return f"REQ-{nuevo_num:04d}"


# ============================================================
# ESTILOS VISUALES - MODO CLARO
# ============================================================

st.markdown(
    """
    <style>
        body, .stApp { background-color: #f4f4f4 !important; }

        .stButton>button {
            background-color: #004A99;
            color: white;
            border-radius: 6px;
            padding: 8px 15px;
        }
        .stButton>button:hover {
            background-color: #003A77;
        }

        .success-message {
            padding: 12px;
            background-color: #d8ffd8;
            border-left: 5px solid #2ecc71;
            border-radius: 5px;
            color: #256d2a;
            font-weight: bold;
            font-size: 16px;
        }

        .titulo-seccion {
            font-size: 30px;
            font-weight: bold;
            margin-top: 10px;
            color: #222;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TABS
# ============================================================

tab1, tab2 = st.tabs(["➕ Registrar Requisición", "📦 Almacén"])

# ==========================================================
# TAB 1 → Registrar Requisición
# ==========================================================
with tab1:
    st.header("Registrar Requisición")

    # -----------------------------
    # 1. Inicializar estado
    # -----------------------------
    if "form_cuarto" not in st.session_state:
        st.session_state.form_cuarto = ""
        st.session_state.form_work = ""
        st.session_state.form_parte = ""
        st.session_state.form_lote = ""
        st.session_state.form_cantidad = 1
        st.session_state.form_motivo = "Proceso"

    if "msg_ok" not in st.session_state:
        st.session_state.msg_ok = False

    if "reset_form" not in st.session_state:
        st.session_state.reset_form = False

    # Si viene de un guardado anterior, aquí sí limpiamos,
    # PERO ANTES de crear los widgets
    if st.session_state.reset_form:
        st.session_state.form_cuarto = ""
        st.session_state.form_work = ""
        st.session_state.form_parte = ""
        st.session_state.form_lote = ""
        st.session_state.form_cantidad = 1
        st.session_state.form_motivo = "Proceso"
        st.session_state.reset_form = False

    lista_cuartos = [
        "INTRODUCER","PU1","PU2","PU3","PU4","PVC1","PVC2","PVC3A","PVC3B",
        "PVC6","PVC7","PVC8","PVC9","PVCS","PAK1","MGLY","MASM1","MMCL",
        "MM MOLD","MMFP","MIXIN","RESORTES"
    ]
    lista_motivos = ["Proceso","Extra","Scrap","Navajas","Tooling"]

    # -----------------------------
    # 2. Formulario
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.selectbox(
            "Cuarto",
            lista_cuartos,
            key="form_cuarto"
        )

        st.text_input(
            "Work Order",
            key="form_work"
        )

        st.text_input(
            "Número de Parte",
            key="form_parte"
        )

    with col2:
        st.text_input(
            "Número de Lote",
            key="form_lote"
        )

        st.number_input(
            "Cantidad",
            min_value=1,
            step=1,
            key="form_cantidad"
        )

        st.selectbox(
            "Motivo",
            lista_motivos,
            key="form_motivo"
        )

    # -----------------------------
    # 3. Mensaje de éxito (si aplica)
    # -----------------------------
    if st.session_state.msg_ok:
        st.success("✔ Solicitud enviada correctamente.")

        # Esperar 3 segundos y ocultar
        time.sleep(3)
        st.session_state.msg_ok = False
        st.rerun()

    # -----------------------------
    # 4. Guardar requisición
    # -----------------------------
    if "guardando" not in st.session_state:
        st.session_state.guardando = False

    guardar = st.button("Guardar Requisicion",disabled=st.session_state.guardando)

    if guardar and not st.session_state.guardando:
        st.session_state.guardando = True
        st.rerun()

    if st.session_state.guardando:

        df = cargar_datos()

        nueva_fila = {
            "ID": generar_id(),
            "fecha_hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "cuarto": st.session_state.form_cuarto,
            "work_order": st.session_state.form_work,
            "numero_parte": st.session_state.form_parte,
            "numero_lote": st.session_state.form_lote,
            "cantidad": st.session_state.form_cantidad,
            "motivo": st.session_state.form_motivo,
            "status": "Pendiente",
            "almacenista": "",
            "issue": False,
        }

        df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
        guardar_datos(df)

        # ======================================================
        # ENVIAR TAMBIÉN LA REQUISICIÓN A SMARTSHEET (CORRECTO)
        # ======================================================
        try:
            import smartsheet

            token = st.secrets["SMARTSHEET_TOKEN"]
            sheet_id = int(st.secrets["SHEET_ID"])

            client = smartsheet.Smartsheet(token)

            new_row = smartsheet.models.Row()
            new_row.to_top = True

            new_row.cells = [
                {"column_id": 675055919648644, "value": nueva_fila["ID"]},
                {"column_id": 612161207095172, "value": nueva_fila["fecha_hora"]},
                {"column_id": 5115760834465668, "value": nueva_fila["cuarto"]},
                {"column_id": 2863961020780420, "value": nueva_fila["work_order"]},
                {"column_id": 7367560648150916, "value": nueva_fila["numero_parte"]},
                {"column_id": 1738061113937796, "value": nueva_fila["numero_lote"]},
                {"column_id": 6241660741308292, "value": nueva_fila["cantidad"]},
                {"column_id": 3989860927623044, "value": nueva_fila["motivo"]},
                {"column_id": 8493460554993540, "value": nueva_fila["status"]},
                {"column_id": 330686230384516, "value": nueva_fila["almacenista"]},
                {"column_id": 4834285857755012, "value": bool(nueva_fila["issue"])},
            ]

            response = client.Sheets.add_rows(sheet_id, [new_row])

            if response.message != "SUCCESS":
                st.error(f"❌ Error Smartsheet: {response.message}")

        except Exception as e:
            st.error("❌ Error al enviar a Smartsheet.")
            st.write(e)

        # Fin del proceso
        st.session_state.guardando = False
        st.session_state.msg_ok = True
        st.session_state.reset_form = True

        st.rerun()

# ============================================================
# TAB 2 — PANEL DE ALMACÉN
# ============================================================

# ============================================================
# TAB 2 — PANEL DE ALMACÉN
# ============================================================

with tab2:

    st.markdown("<div class='titulo-seccion'>Panel de Almacén</div>", unsafe_allow_html=True)

    # ---------------------------------------
    # 1) Inicializar el estado de autenticación
    # ---------------------------------------
    if "almacen_auth" not in st.session_state:
        st.session_state.almacen_auth = False

    # ---------------------------------------
    # 2) Si NO está autenticado → pedir contraseña
    # ---------------------------------------
    if not st.session_state.almacen_auth:

        pwd = st.text_input("Ingrese contraseña:", type="password", key="pwd_input")

        if pwd:
            if pwd == ALMACEN_PASSWORD:
                st.session_state.almacen_auth = True
                st.rerun()
                
            else:
                st.warning("🚫 Acceso restringido.")
                st.stop()

        st.stop()

    # ---------------------------------------
    # 3) SI YA ESTÁ AUTENTICADO → mostrar panel
    # ---------------------------------------
    st.success("🔓 Acceso concedido.")

    # Ocultar el input una vez autenticado (lo elimina del DOM)
    st.markdown("""
    <style>
    input[type="password"] {display:none;}
    label[for="pwd_input"] {display:none;}
    </style>
    """, unsafe_allow_html=True)

    # Ahora carga el panel normalmente
    df = cargar_datos().fillna("")


    # -------------------------------------------
    # COLUMNAS CALCULADAS
    # -------------------------------------------

    df["fecha_hora_dt"] = pd.to_datetime(df["fecha_hora"])
    estados_finales = ["Entregado", "Cancelado", "No encontrado"]

    def calcular_minutos(row):
        if row["status"] in estados_finales:
            # Mantener minutos ya calculados anteriormente (si existe)
            if "minutos" in row and pd.notna(row["minutos"]):
                return row["minutos"]
            else:
                # Calcular una sola vez
                return int((datetime.now() - row["fecha_hora_dt"]).total_seconds() // 60)
        else:
            # Seguir contando normalmente si no está finalizada
            return int((datetime.now() - row["fecha_hora_dt"]).total_seconds() // 60)

    df["minutos"] = df.apply(calcular_minutos, axis=1)

    def semaforo(x):
        if x >= 20: return "🔴"
        if x >= 10: return "🟠"
        return "🟢"

    df["semaforo"] = df["minutos"].apply(semaforo)

    df = df.sort_values(by="fecha_hora_dt", ascending=False)

    # -------------------------------------------
    # FILTROS
    # -------------------------------------------

    st.subheader("Filtrar información")

    colf1, colf2, colf3 = st.columns(3)

    with colf1:
        filtro_cuarto = st.selectbox("Filtrar por cuarto", [""] + sorted(df["cuarto"].unique()))

    with colf2:
        filtro_status = st.multiselect(
            "Filtrar por status",
            ["Pendiente","En proceso","Entregado","Cancelado","No encontrado"]
        )

    with colf3:
        filtro_issue = st.multiselect("Issue", ["True","False"])

    df_fil = df.copy()

    if filtro_cuarto:
        df_fil = df_fil[df_fil["cuarto"] == filtro_cuarto]

    if filtro_status:
        df_fil = df_fil[df_fil["status"].isin(filtro_status)]

    if filtro_issue:
        df_fil = df_fil[df_fil["issue"].astype(str).isin(filtro_issue)]

    # -------------------------------------------
    # TABLA PRINCIPAL
    # -------------------------------------------

    st.subheader("Requisiciones registradas")

    st.dataframe(
        df_fil[[
            "ID","fecha_hora","cuarto","work_order","numero_parte",
            "numero_lote","cantidad","motivo","almacenista",
            "status","issue","minutos","semaforo"
        ]],
        use_container_width=True,
        height=350
    )

    # -------------------------------------------
    # EDITAR REQUISICIÓN
    # -------------------------------------------

    st.subheader("Editar requisición")

    id_editar = st.selectbox("Seleccionar ID", [""] + list(df["ID"]))

    if id_editar:

        fila = df[df["ID"] == id_editar].iloc[0]
        idx = df[df["ID"] == id_editar].index[0]

        col1, col2 = st.columns(2)

        with col1:
            nuevo_status = st.selectbox(
                "Status",
                ["Pendiente","En proceso","Entregado","Cancelado","No encontrado"],
                index=["Pendiente","En proceso","Entregado","Cancelado","No encontrado"].index(fila["status"])
            )

            nuevo_almacenista = st.text_input("Almacenista", fila["almacenista"])

        with col2:
            nuevo_issue = st.checkbox("Issue", value=(str(fila["issue"])=="True"))

        if st.button("Guardar cambios"):

            # ============================================
            # 1) ACTUALIZAR EN EL CSV LOCAL
            # ============================================
            df.at[idx, "status"] = nuevo_status
            df.at[idx, "almacenista"] = nuevo_almacenista
            df.at[idx, "issue"] = str(nuevo_issue)

            guardar_datos(df)

            # ============================================
            # 2) ACTUALIZAR TAMBIÉN EN SMARTSHEET
            # ============================================
            try:
                import smartsheet

                token = st.secrets["SMARTSHEET_TOKEN"]
                sheet_id = int(st.secrets["SHEET_ID"])
                client = smartsheet.Smartsheet(token)

                # Descargar hoja actual
                sheet = client.Sheets.get_sheet(sheet_id)

                st.write("DEBUG: Hoja descargada correctamente.")

                row_id_smartsheet = None

                # Buscar coincidencia por columna ID
                for row in sheet.rows:
                    for cell in row.cells:
                        if cell.column_id == 675055919648644: # COLUMNA ID
                            if str(cell.value).strip() == str(id_editar).strip():
                                row_id_smartsheet = row.id
                                st.write(f"DEBUG: ID coincide con RowID {row_id_smartsheet}")
                                break

                if row_id_smartsheet is None:
                    st.warning("⚠️ No se encontró el ID exacto en Smartsheet.")
                else:
                    update_row = smartsheet.models.Row()
                    update_row.id = row_id_smartsheet

                    update_row.cells = [
                        {"column_id": 8493460554993540, "value": nuevo_status},
                        {"column_id": 330686230384516, "value": nuevo_almacenista},
                        {"column_id": 4834285857755012, "value": bool(nuevo_issue)},
                    ]

                    st.write("DEBUG: Enviando update_row a Smartsheet...")
                    response = client.Sheets.update_rows(sheet_id, [update_row])

                    st.write("DEBUG Response:", response)

                    if hasattr(response, "message"):
                        st.write("DEBUG response.message:", response.message)

            except Exception as e:
                st.error(f"❌ Error al actualizar Smartsheet: {e}")

            # Mensaje final
            st.success("✓ Requisición actualizada.")
            st.rerun() # <- Desactivado temporalmente para debug


    # ================================
    # EXPORTAR A CSV CON TIMESTAMP
    # ================================
    from datetime import datetime

    st.markdown("### 📤 Exportar datos")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Crear columnas para alinear a la derecha
    col_a, col_b, col_c = st.columns([5, 5, 2]) # Ajusta proporciones si quieres

    with col_c:
        # Exportar filtrado
        csv_filtrado = df_fil.to_csv(index=False).encode("utf-8")
        nombre_filtrado = f"requisiciones_filtradas_{timestamp}.csv"

        st.download_button(
            label="⬇️ Exportar requisiciones filtradas",
            data=csv_filtrado,
            file_name=nombre_filtrado,
            mime="text/csv",
            use_container_width=True
        )

        # Exportar base completa
        df_base_export = cargar_datos().fillna("")
        csv_completo = df_base_export.to_csv(index=False).encode("utf-8")
        nombre_completo = f"requisiciones_completas_{timestamp}.csv"

        st.download_button(
            label="⬇️ Exportar base completa",
            data=csv_completo,
            file_name=nombre_completo,
            mime="text/csv",
            use_container_width=True
        )




























