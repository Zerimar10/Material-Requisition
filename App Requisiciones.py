import streamlit as st
import pandas as pd
from datetime import datetime
import time
import smartsheet

ALMACEN_PASSWORD = st.secrets["ALMACEN_PASSWORD"]

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

CSV_PATH = "data/requisiciones.csv"

# ============================================================
# CONSTANTES SMARTSHEET
# ============================================================
SHEET_ID = 2854951320506244

COL_ID = {
    "ID": 675055919648644,
    "fecha_hora": 612161207095172,
    "cuarto": 5115760834465668,
    "work_order": 2863961020780420,
    "numero_parte": 7367560648150916,
    "numero_lote": 1738061113937796,
    "cantidad": 6241660741308292,
    "motivo": 3989860927623044,
    "status": 8493460554993540,
    "almacenista": 330686230384516,
    "issue": 4834285857755012,
    "minuto_final": 64199137644420,
}

# ============================================================
# FUNCIÓN → CARGAR DATOS DESDE SMARTSHEET
# ============================================================

def cargar_desde_smartsheet():
    client = smartsheet.Smartsheet(st.secrets["SMARTSHEET_TOKEN"])
    sheet = client.Sheets.get_sheet(SHEET_ID)
    rows_data = []

    for row in sheet.rows:
        data = {"row_id": row.id}

        for cell in row.cells:
            cid = cell.column_id
            val = cell.value

            if cid == COL_ID["ID"]:
                data["ID"] = val
            elif cid == COL_ID["fecha_hora"]:
                data["fecha_hora"] = val
            elif cid == COL_ID["cuarto"]:
                data["cuarto"] = val
            elif cid == COL_ID["work_order"]:
                data["work_order"] = val
            elif cid == COL_ID["numero_parte"]:
                data["numero_parte"] = val
            elif cid == COL_ID["numero_lote"]:
                data["numero_lote"] = val
            elif cid == COL_ID["cantidad"]:
                data["cantidad"] = val
            elif cid == COL_ID["motivo"]:
                data["motivo"] = val
            elif cid == COL_ID["status"]:
                data["status"] = val
            elif cid == COL_ID["almacenista"]:
                data["almacenista"] = val
            elif cid == COL_ID["issue"]:
                data["issue"] = bool(val) if val is not None else False
            elif cid == COL_ID["minuto_final"]:
                data["min_final"] = val

        if "ID" in data:
            rows_data.append(data)

    df = pd.DataFrame(rows_data)

    columnas = [
        "ID", "fecha_hora", "cuarto", "work_order", "numero_parte",
        "numero_lote", "cantidad", "motivo", "status",
        "almacenista", "issue", "min_final", "row_id"
    ]

    return df[columnas]

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

        # Generar ID único
        ID = f"REQ-{int(datetime.now().timestamp())}"

        nueva_fila = {
            "ID": ID,
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
            "min_final": None,
        }

        # -----------------------------
        # ENVIAR DIRECTO A SMARTSHEET
        # -----------------------------
        try:
            client = smartsheet.Smartsheet(st.secrets["SMARTSHEET_TOKEN"])

            new_row = smartsheet.models.Row()
            new_row.to_top = True

            new_row.cells = [
                {"column_id": COL_ID["ID"], "value": nueva_fila["ID"]},
                {"column_id": COL_ID["fecha_hora"], "value": nueva_fila["fecha_hora"]},
                {"column_id": COL_ID["cuarto"], "value": nueva_fila["cuarto"]},
                {"column_id": COL_ID["work_order"], "value": nueva_fila["work_order"]},
                {"column_id": COL_ID["numero_parte"], "value": nueva_fila["numero_parte"]},
                {"column_id": COL_ID["numero_lote"], "value": nueva_fila["numero_lote"]},
                {"column_id": COL_ID["cantidad"], "value": nueva_fila["cantidad"]},
                {"column_id": COL_ID["motivo"], "value": nueva_fila["motivo"]},
                {"column_id": COL_ID["status"], "value": nueva_fila["status"]},
                {"column_id": COL_ID["almacenista"], "value": ""},
                {"column_id": COL_ID["issue"], "value": False},
                {"column_id": COL_ID["minuto_final"], "value": None},
            ]

            client.Sheets.add_rows(SHEET_ID, [new_row])

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

with tab2:

    st.markdown("<div class='titulo-seccion'>Panel de Almacén</div>", unsafe_allow_html=True)

    # ---------------------------------------
    # 1) Inicializar el estado de autenticación
    # ---------------------------------------
    
    if "almacen_autenticando" not in st.session_state:
        st.session_state.almacen_autenticando = False

    # ---------------------------------------
    # 2) Si NO está autenticado → pedir contraseña
    # ---------------------------------------
    if not st.session_state.almacen_autenticando:

        pwd = st.text_input("Ingrese contraseña:", type="password", key="pwd_input")

        if pwd:
            if pwd == ALMACEN_PASSWORD:
                st.session_state.almacen_autenticando = True
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
    df = cargar_desde_smartsheet().fillna("")

    # ============================================================
    # CALCULAR MINUTOS + CONGELAMIENTO
    # ============================================================

    # Convertir fecha a datetime
    df["fecha_hora_dt"] = pd.to_datetime(df["fecha_hora"], errors="coerce")

    # Estados donde se congela el contador
    estados_finales = ["Entregado", "Cancelado", "No encontrado"]
    
    # Normalizar min_final
    if "min_final" not in df.columns:
        df["min_final"] = None
    else:
        df["min_final"] = df["min_final"].apply(
            lambda x: int(x) if pd.notna(x) and str(x).isdigit() else None
        )

    # Función para calcular minutos con congelamiento
    def calcular_minutos(row):

        # Si fecha inválida → 0
        if pd.isna(row["fecha_hora_dt"]):
            return 0

        # Si ya está congelado
        if row["min_final"] is not None:
            try:
                return int(row["min_final"])
            except:
                pass

        # Si status es final → congelar solo una vez
        if row["status"] in estados_finales:
            diff = (datetime.now() - row["fecha_hora_dt"]).total_seconds() // 60
            return int(diff)

        # Caso normal
        diff = (datetime.now() - row["fecha_hora_dt"]).total_seconds() // 60
        return int(diff)

    df["minutos"] = df.apply(calcular_minutos, axis=1)

    # Función semáforo
    def semaforo(m):
        if m >= 120:
            return "🔴"
        if m >= 60:
            return "🟡"
        return "🟢"

    df["semaforo"] = df["minutos"].apply(semaforo)

    # Orden correcto
    df = df.sort_values(by="fecha_hora_dt", ascending=False)

    # -------------------------------------------
    # FILTROS
    # -------------------------------------------

    st.markdown("<div class='subtitulo-seccion'>Filtrar información</div>", unsafe_allow_html=True)

    colA, colB = st.columns(2)

    with colA:
        filtro_cuarto = st.multiselect("Filtrar por cuarto", df["cuarto"].unique())

    with colB:
        filtro_status = st.multiselect("Filtrar por status", df["status"].unique())

    df_filtrado = df.copy()

    if filtro_cuarto:
        df_filtrado = df_filtrado[df_filtrado["cuarto"].isin(filtro_cuarto)]

    if filtro_status:
        df_filtrado = df_filtrado[df_filtrado["status"].isin(filtro_status)]

    # -------------------------------------------
    # TABLA PRINCIPAL
    # -------------------------------------------

    st.markdown("<div class='subtitulo-seccion'>Requisiciones registradas</div>", unsafe_allow_html=True)
    st.dataframe(df_filtrado, hide_index=True, use_container_width=True)

    # -------------------------------------------
    # EDITAR REQUISICIÓN
    # -------------------------------------------

    st.markdown("<div class='subtitulo-seccion'>Editar requisición</div>", unsafe_allow_html=True)

    lista_ids = df["ID"].tolist()
    id_editar = st.selectbox("Seleccione ID a editar:", lista_ids)

    if id_editar:

        row_edit = df[df["ID"] == id_editar].iloc[0]
        idx = df[df["ID"] == id_editar].index[0]

        nuevo_status = st.selectbox("Nuevo status:", df["status"].unique(), index=list(df["status"].unique()).index(row_edit["status"]))
        nuevo_almacenista = st.text_input("Almacenista:", value=row_edit["almacenista"])
        nuevo_issue = st.checkbox("Issue", value=row_edit["issue"])

        if st.button("Guardar cambios"):

            # Congelar minutos si llega a un estado final
            min_final_val = row_edit["minutos"] if nuevo_status in estados_finales else None

            # Actualizar en Smartsheet
            try:
                client = smartsheet.Smartsheet(st.secrets["SMARTSHEET_TOKEN"])

                update_row = smartsheet.models.Row()
                update_row.id = row_edit["row_id"]

                update_row.cells = [
                    {"column_id": COL_ID["status"], "value": nuevo_status},
                    {"column_id": COL_ID["almacenista"], "value": nuevo_almacenista},
                    {"column_id": COL_ID["issue"], "value": nuevo_issue},
                    {"column_id": COL_ID["minuto_final"], "value": min_final_val},
                ]

                client.Sheets.update_rows(SHEET_ID, [update_row])

                st.success("Cambios guardados correctamente.")
                st.experimental_rerun()

            except Exception as e:
                st.error("❌ Error al guardar cambios.")
                st.write(e)
                st.error("❌ Error al guardar cambios.")
                st.write(e)



