import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import io
import os
import uuid
from pandas.errors import ParserError
from filelock import FileLock
import glob

st.set_page_config(page_title="Sistema de Requisiciones", layout="wide")

def df_to_csv_bytes(df):
    return df.to_csv(index=False, encoding="utf-8-sig").encode()

ALMACEN_PASSWORD = st.secrets["ALMACEN_PASSWORD"]

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

CSV_PATH = "data/requisiciones.csv"
LOCK_PATH = CSV_PATH + ".lock"
BACKUP_DIR = "data/backups"

# ==========================
# CSV LOCAL (FUENTE DE VERDAD)
# ==========================

COLUMNAS_BASE = [
    "ID", "uuid", "fecha_hora", "cuarto", "work_order", "numero_parte", "numero_lote",
    "cantidad", "motivo", "status", "almacenista", "issue", "min_final"
]

def asegurar_directorio_csv():
    carpeta = os.path.dirname(CSV_PATH)
    if carpeta and not os.path.exists(carpeta):
        os.makedirs(carpeta, exist_ok=True)

def crear_backup_csv(motivo="auto"):
    if not os.path.exists(CSV_PATH):
        return

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_path = f"{BACKUP_DIR}/requisiciones_backup_{timestamp}_{motivo}.csv"

    try:
        import shutil
        shutil.copy2(CSV_PATH, backup_path)
    except Exception as e:
        st.warning(f"⚠️ No se pudo crear respaldo del CSV: {e}")

def _read_csv_seguro():
    """
    Lee CSV con fallback si hay líneas dañadas.
    No usa lock; el lock se maneja fuera cuando se necesita.
    """
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=COLUMNAS_BASE)

    try:
        df = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8-sig").fillna("")
        return df
    except ParserError:
        crear_backup_csv("corrupto")

        df = pd.read_csv(
            CSV_PATH,
            dtype=str,
            encoding="utf-8-sig",
            engine="python",
            on_bad_lines="skip"
        ).fillna("")

        st.warning(
            "⚠️ El archivo de requisiciones estaba dañado. "
            "Se creó un respaldo automático y se omitieron líneas inválidas."
        )
        return df

def cargar_desde_csv():
    """
    Lee con lock para no leer a mitad de una escritura.
    """
    asegurar_directorio_csv()

    # Si no existe aún, regresa estructura vacía
    if not os.path.exists(CSV_PATH):
        return pd.DataFrame(columns=COLUMNAS_BASE)

    with FileLock(LOCK_PATH, timeout=10):
        df = _read_csv_seguro()

    # Normalizaciones
    if "issue" in df.columns:
        df["issue"] = df["issue"].astype(str).str.lower().isin(["true", "1", "yes", "si", "sí"])

    if "cantidad" in df.columns:
        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)

    # fecha_hora_dt para orden y cálculo
    df["fecha_hora_dt"] = pd.to_datetime(df.get("fecha_hora", ""), errors="coerce")

    # Garantizar columnas
    for c in COLUMNAS_BASE:
        if c not in df.columns:
            df[c] = "" if c not in ["issue"] else False

    return df

def guardar_a_csv(df):
    """
    Escritura atómica: escribe a .tmp y luego reemplaza.
    Usa lock para evitar corrupción.
    """
    asegurar_directorio_csv()
    df_out = df.copy()

    # Evitar guardar columnas internas
    df_out = df_out.drop(columns=["fecha_hora_dt"], errors="ignore")

    # Asegurar orden de columnas (si faltan, se crean)
    for c in COLUMNAS_BASE:
        if c not in df_out.columns:
            df_out[c] = "" if c not in ["issue"] else False
    df_out = df_out[COLUMNAS_BASE]

    with FileLock(LOCK_PATH, timeout=10):
        crear_backup_csv("pre_guardado")
        
        tmp_path = CSV_PATH + ".tmp"
        df_out.to_csv(tmp_path, index=False, encoding="utf-8-sig")
        os.replace(tmp_path, CSV_PATH)

def siguiente_id(df):
    # REQ-00001...
    ids = df["ID"].astype(str).tolist() if "ID" in df.columns else []
    nums = []
    for v in ids:
        if v.startswith("REQ-"):
            try:
                nums.append(int(v.replace("REQ-", "")))
            except:
                pass
    nuevo = (max(nums) + 1) if nums else 1
    return f"REQ-{nuevo:05d}"

def ya_existe_uuid(df, u):
    if "uuid" not in df.columns:
        return False
    return (df["uuid"].astype(str) == str(u)).any()

def agregar_requisicion_csv(nueva_fila):
    """
    Inserta arriba y guarda.
    Anti-duplicado: si uuid ya existe, no inserta.

    OJO IMPORTANTE: se hace TODO dentro de lock (leer -> checar -> insertar -> guardar)
    para evitar que 2 usuarios se pisen y se pierdan registros.
    """
    asegurar_directorio_csv()

    with FileLock(LOCK_PATH, timeout=10):
        df = _read_csv_seguro()

        # Garantizar columnas mínimas si CSV venía vacío/dañado
        for c in COLUMNAS_BASE:
            if c not in df.columns:
                df[c] = "" if c not in ["issue"] else False

        # Normalizaciones básicas para comparar uuid
        if "uuid" not in df.columns:
            df["uuid"] = ""

        if ya_existe_uuid(df, nueva_fila["uuid"]):
            return cargar_desde_csv(), False

        df_nueva = pd.DataFrame([nueva_fila])
        df = pd.concat([df_nueva, df], ignore_index=True)

        # Orden por fecha desc
        df["fecha_hora_dt"] = pd.to_datetime(df.get("fecha_hora", ""), errors="coerce")
        df = df.sort_values(by="fecha_hora_dt", ascending=False)

        # Guardado atómico (sin salir del lock)
        df_out = df.drop(columns=["fecha_hora_dt"], errors="ignore")
        for c in COLUMNAS_BASE:
            if c not in df_out.columns:
                df_out[c] = "" if c not in ["issue"] else False
        df_out = df_out[COLUMNAS_BASE]

        tmp_path = CSV_PATH + ".tmp"
        df_out.to_csv(tmp_path, index=False, encoding="utf-8-sig")
        os.replace(tmp_path, CSV_PATH)

    # Devuelve el df ya normalizado con fecha_hora_dt
    return cargar_desde_csv(), True

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
            color: #0072CE;
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

    # Si viene de un guardado anterior, limpiar antes de crear widgets
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
        "MM MOLD","MMFP","MIXING","RESORTES"
    ]
    lista_motivos = ["Proceso","Extra","Scrap","Navajas","Tooling"]

    # -----------------------------
    # 2. Formulario
    # -----------------------------
    col1, col2 = st.columns(2)

    with col1:
        st.selectbox("Cuarto", lista_cuartos, key="form_cuarto")
        st.text_input("Work Order", key="form_work")
        st.text_input("Número de Parte", key="form_parte")

    with col2:
        st.text_input("Número de Lote", key="form_lote")
        st.number_input("Cantidad", min_value=1, step=1, key="form_cantidad")
        st.selectbox("Motivo", lista_motivos, key="form_motivo")

    # -----------------------------
    # 3. Mensaje de éxito
    # -----------------------------
    if st.session_state.msg_ok:
        if "msg_timestamp" not in st.session_state:
            st.session_state.msg_timestamp = time.time()

        folio = st.session_state.get("ultimo_id", "???")
        st.success(f"✔ Requisición {folio} enviada correctamente.")

        if time.time() - st.session_state.msg_timestamp > 4:
            st.session_state.msg_ok = False
            del st.session_state.msg_timestamp
            st.rerun()

    # -----------------------------
    # 4. Guardar requisición (botón con texto dinámico)
    # -----------------------------
    if "guardando" not in st.session_state:
        st.session_state.guardando = False

    def iniciar_guardado():
        st.session_state.guardando = True

    texto_boton = "⏳ Guardando..." if st.session_state.guardando else "Guardar Requisicion"

    st.button(
        texto_boton,
        disabled=st.session_state.guardando,
        on_click=iniciar_guardado
    )

    if st.session_state.guardando:

        # Generar ID local (sin internet)
        df_actual = cargar_desde_csv()
        ID = siguiente_id(df_actual)
        st.session_state.ultimo_id = ID

        # Hora local (UTC-7)
        hora_local = datetime.utcnow() - timedelta(hours=7)

        # Anti-duplicado fuerte: uuid por intento
        if "pending_uuid" not in st.session_state:
            st.session_state.pending_uuid = str(uuid.uuid4())

        nueva_fila = {
            "ID": ID,
            "uuid": st.session_state.pending_uuid,
            "fecha_hora": hora_local.strftime("%Y-%m-%d %H:%M:%S"),
            "cuarto": st.session_state.form_cuarto,
            "work_order": st.session_state.form_work,
            "numero_parte": st.session_state.form_parte,
            "numero_lote": st.session_state.form_lote,
            "cantidad": int(st.session_state.form_cantidad),
            "motivo": st.session_state.form_motivo,
            "status": "Pendiente",
            "almacenista": "",
            "issue": False,
            "min_final": "",
        }

        # Guardar en CSV (con lock)
        try:
            _, inserted = agregar_requisicion_csv(nueva_fila)
            if not inserted:
                st.warning("⚠️ Esta requisición ya estaba registrada (evité duplicado).")
        except Exception as e:
            st.error("❌ Error al guardar en CSV.")
            st.write(e)

        # Limpiar bandera de intento
        st.session_state.pop("pending_uuid", None)

        # Fin
        st.session_state.guardando = False
        st.session_state.msg_ok = True
        st.session_state.reset_form = True
        st.rerun()

# ============================================================
# TAB 2 — PANEL DE ALMACÉN
# ============================================================

with tab2:

    st.markdown("<div class='titulo-seccion'>Panel de Almacén</div>", unsafe_allow_html=True)

    if "almacen_autenticando" not in st.session_state:
        st.session_state.almacen_autenticando = False

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

    st.success("🔓 Acceso concedido.")

    # ==========================
    # 🔐 ADMIN: DESCARGA BACKUPS (oculto)
    # ==========================

    with st.expander("🛠️ Admin (Backups)", expanded=False):
        # Lista de backups disponibles
        backups = sorted(
            glob.glob(f"{BACKUP_DIR}/requisiciones_backup_*.csv"),
            reverse=True
        )

        if not backups:
            st.info("No hay respaldos todavía.")
        else:
            st.caption(f"Respaldos encontrados: {len(backups)}")

            # Descargar el más reciente
            ultimo = backups[0]
            with open(ultimo, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar respaldo MÁS RECIENTE",
                    data=f.read(),
                    file_name=os.path.basename(ultimo),
                    mime="text/csv",
                    use_container_width=True
                )

            # (Opcional) elegir uno específico
            st.markdown("**O elegir un respaldo específico:**")
            seleccionado = st.selectbox(
                "Selecciona un respaldo",
                backups,
                format_func=lambda p: os.path.basename(p)
            )

            with open(seleccionado, "rb") as f:
                st.download_button(
                    label="⬇️ Descargar respaldo seleccionado",
                    data=f.read(),
                    file_name=os.path.basename(seleccionado),
                    mime="text/csv",
                    use_container_width=True
                )

    st.markdown("""
    <style>
    input[type="password"] {display:none;}
    label[for="pwd_input"] {display:none;}
    </style>
    """, unsafe_allow_html=True)

    # Botón refresh
    colR1, colR2 = st.columns([1, 5])
    with colR1:
        if st.button("🔄 Refrescar", use_container_width=True):
            st.session_state.forzar_recarga = True
            st.rerun()
    with colR2:
        st.caption("Actualiza la tabla sin recargar toda la página.")

    # Cache
    if "df_cache" not in st.session_state:
        st.session_state.df_cache = None
        st.session_state.last_reload = 0

    TTL = 15

    def cargar_cache():
        ahora = time.time()

        if (
            st.session_state.df_cache is None
            or (ahora - st.session_state.last_reload) > TTL
            or st.session_state.get("forzar_recarga", False)
        ):
            df_nuevo = cargar_desde_csv().fillna("")

            if "min_final" not in df_nuevo.columns:
                df_nuevo["min_final"] = None

            def normalizar_min_final(x):
                s = str(x).strip().lower()
                if s in ["", "none", "nan"]:
                    return None
                try:
                    return int(float(x))
                except:
                    return None

            df_nuevo["min_final"] = df_nuevo["min_final"].apply(normalizar_min_final)

            df_nuevo["fecha_hora_dt"] = pd.to_datetime(df_nuevo["fecha_hora"], errors="coerce")

            ahora_local = datetime.utcnow() - timedelta(hours=7)

            minutos = pd.Series(0, index=df_nuevo.index, dtype="int64")
            mask_valid = df_nuevo["fecha_hora_dt"].notna()

            diffs = ((ahora_local - df_nuevo.loc[mask_valid, "fecha_hora_dt"]).dt.total_seconds() / 60).astype(int)
            minutos.loc[mask_valid] = diffs.values

            mask_frozen = df_nuevo["min_final"].notna()
            minutos.loc[mask_frozen] = df_nuevo.loc[mask_frozen, "min_final"].astype(int)

            df_nuevo["minutos"] = minutos

            def semaforo(m):
                if m >= 35:
                    return "🔴"
                if m >= 20:
                    return "🟡"
                return "🟢"

            df_nuevo["semaforo"] = df_nuevo["minutos"].apply(semaforo)

            df_nuevo = df_nuevo.sort_values(by="fecha_hora_dt", ascending=False)

            st.session_state.df_cache = df_nuevo
            st.session_state.last_reload = ahora
            st.session_state.forzar_recarga = False

        return st.session_state.df_cache.copy()

    df = cargar_cache()

    # -------------------------------------------
    # FILTROS
    # -------------------------------------------

    if "filtro_cuarto" not in st.session_state:
        st.session_state.filtro_cuarto = []
    if "filtro_status" not in st.session_state:
        st.session_state.filtro_status = []
    if "filtro_issue" not in st.session_state:
        st.session_state.filtro_issue = ["Todos"]

    opciones_issue = ["Todos", "Sí", "No"]

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

    df_filtrado = df.copy()

    if st.session_state.filtro_cuarto:
        df_filtrado = df_filtrado[df_filtrado["cuarto"].isin(st.session_state.filtro_cuarto)]

    if st.session_state.filtro_status:
        df_filtrado = df_filtrado[df_filtrado["status"].isin(st.session_state.filtro_status)]

    f_issue = st.session_state.filtro_issue
    if "Todos" not in f_issue:
        if "Sí" in f_issue and "No" not in f_issue:
            df_filtrado = df_filtrado[df_filtrado["issue"] == True]
        elif "No" in f_issue and "Sí" not in f_issue:
            df_filtrado = df_filtrado[df_filtrado["issue"] == False]

    # -------------------------------------------
    # TABLA PRINCIPAL
    # -------------------------------------------

    st.markdown("<div class='subtitulo-seccion'>Requisiciones registradas</div>", unsafe_allow_html=True)
    tabla_container = st.empty()

    df_filtrado["min_final"] = pd.to_numeric(df_filtrado.get("min_final"), errors="coerce").astype("Int64")

    # Descargar CSV filtrado
    df_export = df_filtrado.copy()
    if "min_final" in df_export.columns:
        df_export["min_final"] = pd.to_numeric(df_export["min_final"], errors="coerce").round(0).astype("Int64")

    csv_bytes = df_to_csv_bytes(df_export)

    st.download_button(
        label="📥 Descargar Excel",
        data=csv_bytes,
        file_name=f"requisiciones_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv",
        mime="text/csv",
    )

    # Ocultar internas + uuid
    columnas_ocultas = ["fecha_hora_dt", "min_final", "uuid"]
    df_visible = df_filtrado.drop(columns=columnas_ocultas, errors="ignore")

    # ==========================
    # TABLA EDITABLE (solo 3 campos)
    # ==========================

    # Columnas que se pueden editar
    EDITABLE_COLS = ["almacenista", "status", "issue"]

    # Opciones de status
    STATUS_OPCIONES = ["Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"]

    # Ocultar internas + uuid (si quieres ocultarlo al usuario)
    columnas_ocultas = ["fecha_hora_dt", "min_final", "uuid"]
    df_visible = df_filtrado.drop(columns=columnas_ocultas, errors="ignore").copy()

    # Para guardar correctamente necesitamos una llave (ideal: uuid; si no, ID)
    # Como ocultamos uuid, la conservamos aparte para mapear filas.
    # Creamos un df "trabajo" que sí trae uuid pero no se muestra.
    df_trabajo = df_filtrado.copy()

    # Orden igual que la vista
    df_trabajo = df_trabajo.reset_index(drop=True)
    df_visible = df_visible.reset_index(drop=True)

    # Configuración de columnas editables
    column_config = {
        "almacenista": st.column_config.TextColumn(
            "Almacenista",
            help="Escribe tu nombre",
            max_chars=40
        ),
        "status": st.column_config.SelectboxColumn(
            "Status",
            help="Selecciona el status",
            options=STATUS_OPCIONES,
            required=True
        ),
        "issue": st.column_config.CheckboxColumn(
            "Issue",
            help="Marca si hubo issue",
            default=False
        ),
    }

    # OJO: st.data_editor necesita que las columnas existan
    for c in EDITABLE_COLS:
        if c not in df_visible.columns:
            # crea columnas si faltan
            df_visible[c] = "" if c != "issue" else False

    editado = st.data_editor(
        df_visible,
        hide_index=True,
        use_container_width=True,
        disabled=[c for c in df_visible.columns if c not in EDITABLE_COLS],
        column_config=column_config,
        key="editor_requisiciones",
    )

    # Botón para aplicar cambios
    if st.button("💾 Guardar cambios de la tabla", use_container_width=True):
        # Comparar cambios SOLO en columnas editables
        cambios = []

        # Convertimos a algo comparable
        antes = df_visible.copy()
        despues = editado.copy()

        # Normalizar issue por si viene como object
        if "issue" in antes.columns:
            antes["issue"] = antes["issue"].astype(bool)
        if "issue" in despues.columns:
            despues["issue"] = despues["issue"].astype(bool)

        for i in range(len(despues)):
            for col in EDITABLE_COLS:
                v_old = antes.at[i, col] if col in antes.columns else None
                v_new = despues.at[i, col] if col in despues.columns else None
                if pd.isna(v_old): v_old = ""
                if pd.isna(v_new): v_new = ""
                if v_old != v_new:
                    cambios.append((i, col, v_new))

        if not cambios:
            st.info("No se detectaron cambios.")
        else:
            # Aplicar cambios al CSV completo con LOCK (anti corrupción)
            with FileLock(LOCK_PATH, timeout=10):
                df_all = _read_csv_seguro()

                # Garantizar columnas base si faltan
                for c in COLUMNAS_BASE:
                    if c not in df_all.columns:
                        df_all[c] = "" if c != "issue" else False

                # Normalizar issue en df_all
                df_all["issue"] = df_all["issue"].astype(str).str.lower().isin(["true", "1", "yes", "si", "sí"])

                # Para mapear: usamos uuid si existe; si no, ID
                # df_trabajo sí tiene uuid (aunque esté oculto)
                for (i, col, v_new) in cambios:
                    uuid_val = str(df_trabajo.at[i, "uuid"]) if "uuid" in df_trabajo.columns else ""
                    id_val = str(df_trabajo.at[i, "ID"]) if "ID" in df_trabajo.columns else ""

                    if uuid_val and "uuid" in df_all.columns:
                        idx = df_all.index[df_all["uuid"].astype(str) == uuid_val]
                    else:
                        idx = df_all.index[df_all["ID"].astype(str) == id_val]

                    if len(idx) == 0:
                        continue

                    j = idx[0]

                    if col == "status":
                        # Si pasa a final, congelar min_final (tu lógica)
                        estados_finales = ["Entregado", "Cancelado", "No encontrado"]
                        df_all.loc[j, "status"] = str(v_new)

                        if str(v_new) in estados_finales:
                            min_final_actual = str(df_all.loc[j, "min_final"]).strip()
                            if min_final_actual in ["", "None", "nan"]:
                                fecha_dt = pd.to_datetime(df_all.loc[j, "fecha_hora"], errors="coerce")
                                if pd.notna(fecha_dt):
                                    ahora_local = datetime.utcnow() - timedelta(hours=7)
                                    df_all.loc[j, "min_final"] = str(int((ahora_local - fecha_dt).total_seconds() / 60))
                        else:
                            df_all.loc[j, "min_final"] = ""

                    elif col == "almacenista":
                        df_all.loc[j, "almacenista"] = str(v_new).strip()

                    elif col == "issue":
                        df_all.loc[j, "issue"] = bool(v_new)

                # Guardado atómico
                tmp_path = CSV_PATH + ".tmp"
                df_all.to_csv(tmp_path, index=False, encoding="utf-8-sig")
                os.replace(tmp_path, CSV_PATH)

            st.success("✅ Cambios guardados.")
            st.session_state.forzar_recarga = True
            st.rerun()

# ============================================
# 🔒 EVITAR QUE STREAMLIT SUBA EL SCROLL AL EDITAR
# ============================================

st.markdown("""
<script>
window.addEventListener('scroll', function() {
    sessionStorage.setItem('scrollPos', window.scrollY);
});

function restoreScroll() {
    const y = sessionStorage.getItem('scrollPos');
    if (y !== null) {
        window.scrollTo(0, parseInt(y));
    }
}

const observer = new MutationObserver((mutations) => {
    restoreScroll();
    setTimeout(restoreScroll, 30);
    setTimeout(restoreScroll, 80);
    setTimeout(restoreScroll, 150);
    setTimeout(restoreScroll, 300);
});

observer.observe(document.body, { childList: true, subtree: true });
window.addEventListener('load', restoreScroll);
</script>
""", unsafe_allow_html=True)




