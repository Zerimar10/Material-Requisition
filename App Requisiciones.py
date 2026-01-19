import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import re
import io
import os
import uuid

st.set_page_config(page_title="Sistema de Requisiciones", layout="wide")

def df_to_csv_bytes(df):  
    return df.to_csv(index=False, encoding="utf-8-sig").encode()

ALMACEN_PASSWORD = st.secrets["ALMACEN_PASSWORD"]

# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

CSV_PATH = "data/requisiciones.csv"

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

def cargar_desde_csv():
    asegurar_directorio_csv()

    if not os.path.exists(CSV_PATH):
        df = pd.DataFrame(columns=COLUMNAS_BASE)
        return df

    df = pd.read_csv(CSV_PATH, dtype=str, encoding="utf-8-sig").fillna("")

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
    asegurar_directorio_csv()
    df_out = df.copy()

    # Evitar guardar columnas internas
    if "fecha_hora_dt" in df_out.columns:
        df_out = df_out.drop(columns=["fecha_hora_dt"], errors="ignore")

    # Asegurar orden de columnas (si faltan, se crean)
    for c in COLUMNAS_BASE:
        if c not in df_out.columns:
            df_out[c] = "" if c not in ["issue"] else False
    df_out = df_out[COLUMNAS_BASE]

    df_out.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")

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
    """
    df = cargar_desde_csv()

    if ya_existe_uuid(df, nueva_fila["uuid"]):
        return df, False

    df_nueva = pd.DataFrame([nueva_fila])
    df = pd.concat([df_nueva, df], ignore_index=True)

    # Recalcular fecha_hora_dt y ordenar desc
    df["fecha_hora_dt"] = pd.to_datetime(df.get("fecha_hora", ""), errors="coerce")
    df = df.sort_values(by="fecha_hora_dt", ascending=False)

    guardar_a_csv(df)
    return df, True

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
        "MM MOLD","MMFP","MIXING","RESORTES"
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
    # 3. Mensaje de éxito (si aplica) — SIN BLOQUEO
    # -----------------------------
    if st.session_state.msg_ok:

        if "msg_timestamp" not in st.session_state:
            st.session_state.msg_timestamp = time.time()

        folio = st.session_state.get("ultimo_id", "???")
        st.success(f"✔ Requisición {folio} enviada correctamente.")

        # Ocultar mensaje después de 4 segundos (sin sleep)
        if time.time() - st.session_state.msg_timestamp > 4:
            st.session_state.msg_ok = False
            del st.session_state.msg_timestamp
            st.rerun()

    # -----------------------------
    # 4. Guardar requisición
    # -----------------------------
    if "guardando" not in st.session_state:
        st.session_state.guardando = False

    def iniciar_guardado():
        # Se ejecuta en el click, antes del rerun automático
        st.session_state.guardando = True

    # Texto dinámico del botón
    texto_boton = "⏳ Guardando..." if st.session_state.guardando else "Guardar Requisicion"

    st.button(
        "Guardar Requisicion",
        disabled=st.session_state.guardando,
        on_click=iniciar_guardado
    )

    if st.session_state.guardando:

        # Generar ID local (sin internet)
        df_actual = cargar_desde_csv()
        ID = siguiente_id(df_actual)
        st.session_state.ultimo_id = ID

        # Hora local (UTC-7) como tú lo usas
        hora_local = datetime.utcnow() - timedelta(hours=7)

        # Anti-duplicado fuerte: uuid por evento de guardado
        # (se crea UNA vez por intento)
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

        # Guardar en CSV
        try:
            _, inserted = agregar_requisicion_csv(nueva_fila)
            if not inserted:
                st.warning("⚠️ Esta requisición ya estaba registrada (evité duplicado).")
        except Exception as e:
            st.error("❌ Error al guardar en CSV.")
            st.write(e)

        # Limpiar bandera de intento
        st.session_state.pop("pending_uuid", None)

        # Fin del proceso (igual que ya lo tienes)
        st.session_state.guardando = False
        st.session_state.msg_ok = True
        st.session_state.reset_form = True
        st.rerun()

        
# ============================================================
# TAB 2 — PANEL DE ALMACÉN (OPTIMIZADO)
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

    colR1, colR2 = st.columns([1, 5])
    with colR1:
        if st.button("🔄 Refrescar", use_container_width=True):
            st.session_state.forzar_recarga = True
            st.rerun()

    # ============================================================
    # 🔥 OPTIMIZACIÓN — CACHE LOCAL DE DATOS DE SMARTSHEET
    # ============================================================

    # Inicializar cache si no existe
    if "df_cache" not in st.session_state:
        st.session_state.df_cache = None
        st.session_state.last_reload = 0 # timestamp

    # Cada cuántos segundos refrescar Smartsheet
    TTL = 15 # segundos

    def cargar_cache():
        """Carga y transforma datos desde Smartsheet solo si es necesario."""
        ahora = time.time()

        if (
            st.session_state.df_cache is None
            or (ahora - st.session_state.last_reload) > TTL
            or st.session_state.get("forzar_recarga", False)
        ):
            # 1) Carga cruda
            df_nuevo = cargar_desde_csv().fillna("")

            # 2) Garantizar columna min_final
            if "min_final" not in df_nuevo.columns:
                df_nuevo["min_final"] = None

            # 3) Normalizar min_final
            def normalizar_min_final(x):
                s = str(x).strip().lower()
                if s in ["", "none", "nan"]:
                    return None
                try:
                    return int(float(x))
                except:
                    return None

            df_nuevo["min_final"] = df_nuevo["min_final"].apply(normalizar_min_final)

            # 4) Convertir fecha a datetime
            df_nuevo["fecha_hora_dt"] = pd.to_datetime(
                df_nuevo["fecha_hora"], errors="coerce"
            )

            # 5) Calcular minutos (vectorizado)
            from datetime import datetime, timedelta
            ahora_local = datetime.utcnow() - timedelta(hours=7)

            minutos = pd.Series(0, index=df_nuevo.index, dtype="int64")
            mask_valid = df_nuevo["fecha_hora_dt"].notna()

            # Diferencia en minutos para filas con fecha válida
            diffs = (
                (ahora_local - df_nuevo.loc[mask_valid, "fecha_hora_dt"])
                .dt.total_seconds() / 60
            ).astype(int)
            minutos.loc[mask_valid] = diffs.values

            # Donde haya min_final, usamos ese valor (congelado)
            mask_frozen = df_nuevo["min_final"].notna()
            minutos.loc[mask_frozen] = df_nuevo.loc[mask_frozen, "min_final"].astype(int)

            df_nuevo["minutos"] = minutos

            # 6) Semáforo
            def semaforo(m):
                if m >= 35:
                    return "🔴"
                if m >= 20:
                    return "🟡"
                return "🟢"

            df_nuevo["semaforo"] = df_nuevo["minutos"].apply(semaforo)

            # 7) Ordenar por fecha desc
            df_nuevo = df_nuevo.sort_values(by="fecha_hora_dt", ascending=False)

            # Guardar en sesión
            st.session_state.df_cache = df_nuevo
            st.session_state.last_reload = ahora
            st.session_state.forzar_recarga = False

        # Regresar copia para evitar mutaciones
        return st.session_state.df_cache.copy()

    # 👉 NUEVA LÍNEA PRINCIPAL OPTIMIZADA
    df = cargar_cache()

    # Columnas internas que no deben verse
    columnas_internas = ["min_final", "fecha_hora_dt"]

    # -------------------------------------------
    # FILTROS
    # -------------------------------------------

    # 1) Inicializar estado de filtros
    if "filtro_cuarto" not in st.session_state:
        st.session_state.filtro_cuarto = []

    if "filtro_status" not in st.session_state:
        st.session_state.filtro_status = []

    if "filtro_issue" not in st.session_state:
        st.session_state.filtro_issue = ["Todos"] # lógica: por defecto no filtrar

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
    if "Todos" not in f_issue:
        if "Sí" in f_issue and "No" not in f_issue:
            df_filtrado = df_filtrado[df_filtrado["issue"] == True]
        elif "No" in f_issue and "Sí" not in f_issue:
            df_filtrado = df_filtrado[df_filtrado["issue"] == False]
        # Si marca "Sí" y "No" sin "Todos" → equivale a todo, no se filtra extra

    # -------------------------------------------
    # TABLA PRINCIPAL
    # -------------------------------------------

    st.markdown('<div id="pos_tabla"></div>', unsafe_allow_html=True)
    st.markdown("<div class='subtitulo-seccion'>Requisiciones registradas</div>", unsafe_allow_html=True)

    tabla_container = st.empty()

    # Asegurar que min_final sea entero (sin decimales) en el filtrado
    df_filtrado["min_final"] = pd.to_numeric(
        df_filtrado.get("min_final"),
        errors="coerce",
    ).astype("Int64")

    # ---------------------------------------------------------
    # DESCARGAR TABLA EN EXCEL (VERSIÓN FILTRADA)
    # ---------------------------------------------------------
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

    # Ocultar columnas internas DESPUÉS de filtrar y convertir
    columnas_ocultas = ["fecha_hora_dt", "min_final", "uuid"]
    df_visible = df_filtrado.drop(columns=columnas_ocultas, errors="ignore")

    tabla_container.dataframe(df_visible, hide_index=True, use_container_width=True)

    # ----------------------------------------------
    # FORMULARIO DE EDICIÓN (VERSIÓN FINAL)
    # ----------------------------------------------

    st.markdown("<a id='form_anchor'></a>", unsafe_allow_html=True)

    if "mostrar_edicion" not in st.session_state:
        st.session_state.mostrar_edicion = False

    if st.button("✏️ Editar una requisición"):
        st.session_state.mostrar_edicion = not st.session_state.mostrar_edicion

    form_container = st.container(height=600)

    st.markdown("""
    <style>
    div[direction="column"][height="600px"][data-testid="stVerticalBlock"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    div[direction="column"][height="600px"][data-testid="stVerticalBlock"] > div {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.mostrar_edicion:

        with form_container:

            st.markdown("""
            <style>
            .css-1d391kg {display: none;}
            .css-1cypcdb {display: none;}
            <style>
            """, unsafe_allow_html=True)

            # -----------------------
            # Selección de ID a editar
            # -----------------------
            lista_ids = df["ID"].unique().tolist()
            lista_ids_con_vacio = ["-- Seleccione --"] + lista_ids

            id_editar = st.selectbox("Seleccione ID a editar:", lista_ids_con_vacio)

            if id_editar != "-- Seleccione --":
                fila = df[df["ID"] == id_editar].iloc[0]

                # -----------------------
                # Campos editables
                # -----------------------
                nuevo_status = st.selectbox(
                    "Nuevo status:",
                    ["Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"],
                    index=[
                        "Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"
                    ].index(fila["status"]),
                )

                nuevo_almacenista = st.text_input("Almacenista:", fila["almacenista"])
                nuevo_issue = st.checkbox("Issue", value=(fila["issue"] is True))

                # -----------------------
                # Guardar cambios
                # -----------------------
                if st.button("Guardar cambios"):

                    df_all = cargar_desde_csv()

                    idx = df_all.index[df_all["ID"] == id_editar]
                    if len(idx) == 0:
                        st.error("No encontré ese ID en el CSV.")
                        st.stop()

                    i = idx[0]

                    estados_finales = ["Entregado", "Cancelado", "No encontrado"]

                    # Recalcular minutos para la fila (igual que tu lógica)
                    ahora_local = datetime.utcnow() - timedelta(hours=7)
                    fecha_dt = pd.to_datetime(df_all.loc[i, "fecha_hora"], errors="coerce")
                    minutos_actual = ""
                    if pd.notna(fecha_dt):
                        minutos_actual = int((ahora_local - fecha_dt).total_seconds() / 60)

                    # Si pasa a final, congelar min_final
                    min_final_actual = str(df_all.loc[i, "min_final"]).strip()
                    if nuevo_status in estados_finales:
                        if min_final_actual not in ["", "None", "nan"]:
                            nuevo_min_final = min_final_actual
                        else:
                            nuevo_min_final = str(minutos_actual)
                    else:
                        nuevo_min_final = ""

                    df_all.loc[i, "status"] = nuevo_status
                    df_all.loc[i, "almacenista"] = nuevo_almacenista
                    df_all.loc[i, "issue"] = bool(nuevo_issue)
                    df_all.loc[i, "min_final"] = nuevo_min_final

                    guardar_a_csv(df_all)

                    st.success("Cambios guardados correctamente.")

                    st.session_state.mostrar_edicion = False
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























































