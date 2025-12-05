import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import smartsheet
import re

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
    try:
        client = smartsheet.Smartsheet(st.secrets["SMARTSHEET_TOKEN"])
        response = client.Sheets.get_sheet(SHEET_ID)
        sheet = response # asegurar que sheet es realmente la hoja
        
        rows_data = []

        # Si sheet.rows NO existe, mostrar error útil
        if not hasattr(sheet, "rows"):
            st.error("❌ Error: Smartsheet no devolvió 'rows'. ¿Filtro activo en la hoja?")
            st.stop()

        for row in sheet.rows:
            data = {}
            data["row_id"] = row.id

            for cell in row.cells:
                cid = cell.column_id
                val = cell.value

                for key, col_id in COL_ID.items():
                    if cid == col_id:
                        data[key] = val

            if "ID" in data:
                rows_data.append(data)

        df = pd.DataFrame(rows_data)

        df = df.fillna("")

        df["fecha_hora_dt"] = pd.to_datetime(df["fecha_hora"], errors="coerce")

        return df

    except Exception as e:
        st.error(f"❌ Error cargando Smartsheet: {e}")
        st.stop()

# ============================================================
# FUNCIÓN → GENERAR ID CONSECUTIVO DESDE SMARTSHEET
# ============================================================

def generar_id_desde_smartsheet():
    client = smartsheet.Smartsheet(st.secrets["SMARTSHEET_TOKEN"])
    sheet = client.Sheets.get_sheet(SHEET_ID)

    ids = []

    for row in sheet.rows:
        for cell in row.cells:
            if cell.column_id == COL_ID["ID"]:
                val = str(cell.value) if cell.value is not None else ""
                if val.startswith("REQ-"):
                    try:
                        num = int(val.replace("REQ-", ""))
                        ids.append(num)
                    except:
                        pass

    # Si no hay ningún ID todavía
    if not ids:
        return "REQ-0001"

    nuevo_num = max(ids) + 1
    return f"REQ-{nuevo_num:04d}"

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
        ID = generar_id_desde_smartsheet()

        # Calcular hora local (UTC-7)
        from datetime import datetime, timedelta
        hora_local = datetime.utcnow() - timedelta(hours=7)

        nueva_fila = {
            "ID": ID,
            "fecha_hora": hora_local.strftime("%Y-%m-%d %H:%M:%S"),
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

            def add_cell(colname, val):
                cell = smartsheet.models.Cell()
                cell.column_id = COL_ID[colname]
                cell.value = val
                new_row.cells.append(cell)

            add_cell("ID", nueva_fila["ID"])
            add_cell("fecha_hora", nueva_fila["fecha_hora"])
            add_cell("cuarto", nueva_fila["cuarto"])
            add_cell("work_order", nueva_fila["work_order"])
            add_cell("numero_parte", nueva_fila["numero_parte"])
            add_cell("numero_lote", nueva_fila["numero_lote"])
            add_cell("cantidad", nueva_fila["cantidad"])
            add_cell("motivo", nueva_fila["motivo"])
            add_cell("status", nueva_fila["status"])
            add_cell("almacenista", "")
            add_cell("issue", False)
            add_cell("minuto_final", "")
            
            # Enviar la fila
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

    if "min_final" not in df.columns: df["min_final"] = None

    # ============================================================
    # CALCULAR MINUTOS + CONGELAMIENTO
    # ============================================================

    # Normalizar columna min_final (None o número)
    df["min_final"] = df["min_final"].apply(
        lambda x: None if str(x).strip().lower() in ["", "none", "nan"] else int(float(x))
    )

    # Convertir fecha a datetime
    df["fecha_hora_dt"] = pd.to_datetime(df["fecha_hora"], errors="coerce")

    # Estados donde los minutos deben congelarse
    estados_finales = ["Entregado", "Cancelado", "No encontrado"]

    from datetime import datetime, timedelta

    def calcular_minutos(row):
        # Si la fecha no es válida → 0
        if pd.isna(row["fecha_hora_dt"]):
            return 0

        # Si ya está congelado → regresar ese valor
        if row["min_final"] is not None:
            try:
                return int(row["min_final"])
            except:
                pass

        # Hora local correcta (UTC-7)
        ahora = datetime.utcnow() - timedelta(hours=7)

        # Si el status es final → congelar una sola vez
        if row["status"] in estados_finales:
            diff = (ahora - row["fecha_hora_dt"]).total_seconds() / 60
            return int(diff)

        # Caso normal (contador vivo)
        diff = (ahora - row["fecha_hora_dt"]).total_seconds() / 60
        return int(diff)

    # Aplicar cálculo
    df["minutos"] = df.apply(calcular_minutos, axis=1)

    # Semáforo
    def semaforo(m):
        if m >= 120:
            return "🔴"
        if m >= 60:
            return "🟡"
        return "🟢"

    df["semaforo"] = df["minutos"].apply(semaforo)

    # Ordenar por fecha desc
    df = df.sort_values(by="fecha_hora_dt", ascending=False)

    columnas_internas = ["min_final", "row_id", "fecha_hora_dt"]

    df = df.copy()
    for col in columnas_internas:
        if col in df.columns:
            df[col] = df[col]

    # -------------------------------------------
    # FILTROS
    # -------------------------------------------

    # 1) Inicializar estado de filtros
    if "filtro_cuarto" not in st.session_state:
        st.session_state.filtro_cuarto = []

    if "filtro_status" not in st.session_state:
        st.session_state.filtro_status = []

    if "filtro_issue" not in st.session_state:
        # Por defecto: mostrar todos (opción lógica, no filtro)
        st.session_state.filtro_issue = ["Todos"]

    # Opciones del filtro de issue
    opciones_issue = ["Todos", "Sí", "No"]

    # 2) Controles visuales
    colA, colB, colC = st.columns(3)

    with colA:
        st.session_state.filtro_cuarto = st.multiselect(
            "Filtrar por cuarto",
            df["cuarto"].unique(),
            default=st.session_state.filtro_cuarto,
        )

    with colB:
        st.session_state.filtro_status = st.multiselect(
            "Filtrar por status",
            df["status"].unique(),
            default=st.session_state.filtro_status,
        )

    with colC:
        st.session_state.filtro_issue = st.multiselect(
            "Filtrar por issue",
            opciones_issue,
            default=st.session_state.filtro_issue,
        )

    # 3) Aplicar filtros
    df_filtrado = df.copy()

    # Filtrar por cuarto
    if st.session_state.filtro_cuarto:
        df_filtrado = df_filtrado[
            df_filtrado["cuarto"].isin(st.session_state.filtro_cuarto)
        ]

    # Filtrar por status
    if st.session_state.filtro_status:
        df_filtrado = df_filtrado[
            df_filtrado["status"].isin(st.session_state.filtro_status)
        ]

    # Filtrar por issue
    f_issue = st.session_state.filtro_issue

    # Si incluye "Todos" --> no filtramos nada por issue
    if "Todos" not in f_issue:
        # Sólo "Sí"
        if "Sí" in f_issue and "No" not in f_issue:
            df_filtrado = df_filtrado[df_filtrado["issue"] == True]
        # Sólo "No"
        elif "No" in f_issue and "Sí" not in f_issue:
            df_filtrado = df_filtrado[df_filtrado["issue"] == False]
        # Si marca "Sí" y "No" sin "Todos" -> equivale a mostrar todo, no se aplica filtro extra
    
    # -------------------------------------------
    # TABLA PRINCIPAL
    # -------------------------------------------

    st.markdown('<div id="pos_tabla"></div>', unsafe_allow_html=True)
       
    st.markdown("<div class='subtitulo-seccion'>Requisiciones registradas</div>", unsafe_allow_html=True)

    tabla_container = st.empty()

    # Autorefresco solamente del contenedor
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()

    # Cada 15 segundos refrescar SOLO la tabla
    if time.time() - st.session_state.last_refresh > 15:
        st.session_state.last_refresh = time.time()
        st.session_state.refresh_flag = True
    else:
        st.session_state.refresh_flag = False

    # Columnas internas que no deben verse
    columnas_ocultas = ["fecha_hora_dt","min_final", "row_id"]

    # Asegurar que min_final sea entero (sin decimales)
    df_filtrado["min_final"] = pd.to_numeric(
        df_filtrado["min_final"],
        errors="coerce"
    ).astype("Int64")

    # Ocultar columnas internas DESPUÉS de filtrar y convertir
    df_visible = df_filtrado.drop(columns=columnas_ocultas, errors="ignore")

    if st.session_state.refresh_flag:
        tabla_container.dataframe(df_visible, hide_index=True, use_container_width=True)
    else:
        tabla_container.dataframe(df_visible, hide_index=True, use_container_width=True)

    # ---------------------------------------------------------
    # FORMULARIO DE EDICIÓN (NO DEBE ESTAR ARRIBA DE LA TABLA)
    # ---------------------------------------------------------
    st.markdown("<div id='form_anchor'></div>", unsafe_allow_html=True)

    # Variable de control para mostrar/ocultar formulario
    if "mostrar_edicion" not in st.session_state:
        st.session_state.mostrar_edicion = False

    if st.button("✏️ Editar una requisición"):
        st.session_state.mostrar_edicion = not st.session_state.mostrar_edicion

    form_container = st.container()

    if st.session_state.mostrar_edicion:
        with form_container:
        
            st.markdown("<script>location.href='#form_anchor';</script>", unsafe_allow_html=True)

            lista_ids = df["ID"].unique().tolist()
            lista_ids_con_vacio = ["-- Seleccione --"] + lista_ids

            id_editar = st.selectbox("Seleccione ID a editar:", lista_ids_con_vacio)

            if id_editar != "-- Seleccione --":
                fila = df[df["ID"] == id_editar].iloc[0]

                nuevo_status = st.selectbox(
                    "Nuevo status:",
                    ["Pendiente","En proceso","Entregado","Cancelado","No encontrado"],
                    index=["Pendiente","En proceso","Entregado","Cancelado","No encontrado"].index(fila["status"])
                )

                nuevo_almacenista = st.text_input("Almacenista:", fila["almacenista"])
                nuevo_issue = st.checkbox("Issue", value=(fila["issue"] == True))

                if st.button("Guardar cambios"):
                    # ... tu lógica para guardar
                    pass
    
                try:
                    client = smartsheet.Smartsheet(st.secrets["SMARTSHEET_TOKEN"])

                    # Obtener row_id real
                    row_id = int(fila["row_id"])

                    # ---------------------------------
                    # LÓGICA DE CONGELAR MINUTOS
                    # ---------------------------------
                    nuevo_min_final = None

                    # Si el nuevo status es FINAL → queremos congelar
                    if nuevo_status in estados_finales:
                        # 1) Si ya estaba congelado, lo respetamos
                        valor_actual = fila.get("min_final", None)
                        if pd.notna(valor_actual) and str(valor_actual).strip().lower() not in ["", "none", "nan"]:
                            try:
                                nuevo_min_final = int(valor_actual)
                            except:
                                nuevo_min_final = None
                        else:
                            # 2) Si no estaba congelado, usamos los minutos calculados ahora
                            minutos_actuales = fila.get("minutos", None)
                            try:
                                nuevo_min_final = int(minutos_actuales)
                            except:
                                nuevo_min_final = None
                    else:
                        # Si el status NO es final, limpiamos min_final para que siga contando
                        nuevo_min_final = ""

                    # ---------------------------------
                    # Construir la fila a actualizar
                    # ---------------------------------       
                    update_cells = [
                        {"column_id": COL_ID["status"], "value": nuevo_status},
                        {"column_id": COL_ID["almacenista"], "value": nuevo_almacenista},
                        {"column_id": COL_ID["issue"], "value": nuevo_issue},
                        {"column_id": COL_ID["minuto_final"], "value": nuevo_min_final},
                    ]

                    #Crear objeto Row para Smartsheet
                    update_row = smartsheet.models.Row()
                    update_row.id = row_id
                    update_row.cells = update_cells

                    # Enviar actualización a Smartsheet
                    client.Sheets.update_rows(SHEET_ID, [update_row])

                    st.success("Cambios guardados correctamente.")

                    # Ocultar formulario después de guardar
                    st.session_state.mostrar_edicion = False

                    #Marcar que debemos regresar a la tabla
                    st.markdown("""
                    <script>
                    sessionStorage.setItem("volver_a_tabla",
                    "1");
                    </script>
                    """, unsafe_allow_html=True)

                    st.rerun()

                except Exception as e:
                    st.error("❌ Error al guardar cambios en Smartsheet.")
                    st.write(e)

    st.markdown("""
    <script>
    document.addEventListener("DOMContentLoaded", function() {

        // Restaurar scroll a la tabla si venimos de un rerun
        let destino = sessionStorage.getItem("volver_a_tabla");

        if(destino === "1"){
            const anchor = document.getElementById("pos_tabla");
            if(anchor){
                anchor.scrollIntoView({behavior: "instant", block: "start"});
            }
            sessionStorage.setItem("volver_a_tabla", "0");
        }

    });

    // Registrar cambios que deben volver a la tabla
    document.addEventListener("click", function(){
        sessionStorage.setItem("scrollPos", window.scrollY);
    });
    </script>
    """, unsafe_allow_html=True)



