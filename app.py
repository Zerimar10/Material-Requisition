import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import os
import uuid
import time
from dotenv import load_dotenv

# ==============================
# CONFIGURACIÓN INICIAL
# ==============================
st.set_page_config(
    page_title="Nordson Warehouse System",
    page_icon="nordson_logo.png",
    layout="wide"
)

# --- Encabezado corporativo ---
from PIL import Image

logo = Image.open("nordson_logo.png")
c1, c2 = st.columns([1, 5], vertical_alignment="center")
with c1:
    st.image(logo, width=110)
with c2:
    st.markdown(
        """
        <h1 style='color:#0072CE; font-weight:700; margin-bottom:4px;'>
            Nordson Warehouse System
        </h1>
        <h5 style='color:#5F6C7B; margin-top:0;'>
            Sistema de requisiciones de almacén
        </h5>
        """,
        unsafe_allow_html=True
    )

# --- Estilos finos y línea divisoria ---
st.markdown(
    """
    <style>
      /* Línea divisoria */
      hr {margin: 0.8rem 0; border: 1px solid #E0E6EE;}
      
      /* Botones más “corporativos” */
      .stButton>button {
        border-radius: 10px !important;
        padding: 0.55rem 1rem !important;
        font-weight: 600 !important;
        background-color: #0072CE !important;
        color: white !important;
        border: none !important;
      }
      .stButton>button:hover {
        background-color: #0059A6 !important;
      }

      /* Inputs redondeados */
      .stTextInput>div>div>input,
      .stNumberInput input,
      .stSelectbox>div>div>div {
        border-radius: 8px !important;
      }

      /* Encabezados de secciones */
      h2, h3 { color:#0A2540 !important; }

      /* Compactar editor y tablas */
      [data-testid="stDataFrame"] div[role="gridcell"],
      [data-testid="stDataFrame"] div[role="columnheader"] {
          font-size: 0.92rem !important;
      }
    </style>
    <hr>
    """,
    unsafe_allow_html=True
)

# Cargar variables del archivo .env
load_dotenv()
CLAVE_ALMACEN = os.getenv("CLAVE_ALMACEN", "almacen2025")

CSV_FILE = "requisiciones.csv"

# CSS: diseño compacto
st.markdown(
    """
    <style>
    .enter-to-submit { display: none !important; }
    [data-testid="stDataFrame"] div[role="gridcell"],
    [data-testid="stDataFrame"] div[role="columnheader"] {
        font-size: 0.90rem !important;
    }
    [data-testid="stDataFrame"] div[data-baseweb="checkbox"]:has(input:checked) {
        background-color: #90EE90 !important;
        border-radius: 5px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================
# FUNCIONES AUXILIARES
# ==============================
def ss_default(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

def guardar_csv(df: pd.DataFrame):
    out = df.copy()
    out["Fecha/Hora"] = pd.to_datetime(out["Fecha/Hora"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    out.to_csv(CSV_FILE, index=False)

def limpiar_none(v):
    return "" if (pd.isna(v) or str(v).strip().lower() == "none") else v

# ==============================
# VARIABLES DE SESIÓN
# ==============================
ss_default("page", "🏢 Almacén")
ss_default("almacen_autorizado", False)
ss_default("need_rerun", False)
ss_default("auto_refresh", False)
ss_default("filtros", {
    "areas": [],
    "estatus": ["Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"],
    "rango": None,
    "search": ""
})

# ==============================
# CARGAR O CREAR CSV
# ==============================
cols_base = [
    "ID", "Fecha/Hora", "Área", "Work Order", "Número de parte", "Número de lote",
    "Cantidad", "Motivo", "Estatus", "Almacenista", "Issue"
]

if os.path.exists(CSV_FILE):
    requisiciones = pd.read_csv(CSV_FILE)
else:
    requisiciones = pd.DataFrame(columns=cols_base)

# Asegurar columnas e ID
for c in cols_base:
    if c not in requisiciones.columns:
        requisiciones[c] = "" if c not in ["Cantidad", "Issue"] else (0 if c == "Cantidad" else False)

mask_id = requisiciones["ID"].isna() | (requisiciones["ID"] == "")
if mask_id.any():
    requisiciones.loc[mask_id, "ID"] = [str(uuid.uuid4()) for _ in range(mask_id.sum())]

requisiciones["Fecha/Hora"] = pd.to_datetime(requisiciones["Fecha/Hora"], errors="coerce")
requisiciones = requisiciones.sort_values("Fecha/Hora", ascending=False).reset_index(drop=True)

# ==============================
# MENÚ LATERAL Y CLAVE
# ==============================
st.sidebar.title("📦 Requisiciones")

if not st.session_state["almacen_autorizado"]:
    with st.sidebar.expander("🔐 Acceso para personal de Almacén"):
        clave_input = st.text_input("Clave de acceso", type="password")
        if st.button("Validar clave"):
            if clave_input == CLAVE_ALMACEN:
                st.session_state["almacen_autorizado"] = True
                st.success("✅ Acceso autorizado al módulo de Almacén.")
                time.sleep(1)
                st.session_state["page"] = "🏢 Almacén"
                st.rerun()
            else:
                st.error("❌ Clave incorrecta. Intenta nuevamente.")

menu_opciones = ["🏭 Producción"]
if st.session_state["almacen_autorizado"]:
    menu_opciones.append("🏢 Almacén")

page = st.sidebar.radio("Sección", menu_opciones, index=0 if not st.session_state["almacen_autorizado"] else 1)
st.session_state["page"] = page

# ==============================
# PRODUCCIÓN
# ==============================
if page == "🏭 Producción":
    st.title("🏭 Producción")
    st.header("Nueva Requisición")

    with st.form("nueva_requisicion", clear_on_submit=True):
        area = st.selectbox("Área", [
            "Introducer", "PU1", "PU2", "PU3", "PU4",
            "PVC1", "PVC2", "PVC3A", "PVC3B", "PVC6", "PVC7", "PVCS",
            "PAK1", "MM CL", "MM MOLD", "MM FP", "MIXING", "RESORTES"
        ])
        work_order = st.text_input("Work Order", placeholder="")
        numero_parte = st.text_input("Número de parte")
        numero_lote = st.text_input("Número de lote")
        cantidad = st.number_input("Cantidad", min_value=1, step=1)
        motivo = st.selectbox("Motivo", ["Proceso", "Extra", "Scrap", "Navajas", "Tooling"])
        enviar = st.form_submit_button("📨 Enviar requisición")

    if enviar:
        nueva = pd.DataFrame([{
            "ID": str(uuid.uuid4()),
            "Fecha/Hora": datetime.now(),
            "Área": area,
            "Work Order": work_order.strip(),
            "Número de parte": numero_parte.strip(),
            "Número de lote": numero_lote.strip(),
            "Cantidad": int(cantidad),
            "Motivo": motivo,
            "Estatus": "Pendiente",
            "Almacenista": "",
            "Issue": False
        }])
        requisiciones = pd.concat([nueva, requisiciones], ignore_index=True)
        requisiciones = requisiciones.sort_values("Fecha/Hora", ascending=False).reset_index(drop=True)
        guardar_csv(requisiciones)
        st.toast("✅ Requisición registrada exitosamente.")

# ==============================
# ALMACÉN
# ==============================
if page == "🏢 Almacén":
    st.title("🏢 Almacén")
    st.header("Lista de Requisiciones Registradas")

    if requisiciones.empty:
        st.info("Aún no hay requisiciones registradas.")
    else:
        requisiciones = requisiciones.applymap(limpiar_none)
        requisiciones["Fecha/Hora"] = pd.to_datetime(requisiciones["Fecha/Hora"], errors="coerce")

        # ---------- Filtros persistentes ----------
        areas_disponibles = sorted([a for a in requisiciones["Área"].dropna().unique() if a != ""])
        if not st.session_state["filtros"]["areas"]:
            st.session_state["filtros"]["areas"] = areas_disponibles
        if st.session_state["filtros"]["rango"] is None:
            mind = (requisiciones["Fecha/Hora"].min() or datetime.now()).date()
            maxd = (requisiciones["Fecha/Hora"].max() or datetime.now()).date()
            st.session_state["filtros"]["rango"] = (mind, maxd)

        with st.expander("🔎 Filtros", expanded=True):
            c1, c2, c3 = st.columns([1.2, 1.2, 2])
            sel_areas = c1.multiselect("Área(s)", options=areas_disponibles,
                                       default=st.session_state["filtros"]["areas"], key="areas_key")
            st.session_state["filtros"]["areas"] = sel_areas

            estatus_opciones = ["Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"]
            sel_estatus = c2.multiselect("Estatus", options=estatus_opciones,
                                         default=st.session_state["filtros"]["estatus"], key="estatus_key")
            st.session_state["filtros"]["estatus"] = sel_estatus

            rango = c3.date_input("Rango de fechas",
                                  value=st.session_state["filtros"]["rango"],
                                  key="rango_key")
            st.session_state["filtros"]["rango"] = rango

            search = st.text_input("Buscar (Work Order / Número de parte / Número de lote)",
                                   value=st.session_state["filtros"]["search"], key="search_key").strip().lower()
            st.session_state["filtros"]["search"] = search

            colr1, colr2 = st.columns([1,1])
            auto = colr1.toggle("Auto-actualizar cada 10s", value=st.session_state["auto_refresh"], key="auto_key")
            st.session_state["auto_refresh"] = auto
            if colr2.button("🔄 Actualizar ahora"):
                st.session_state["page"] = "🏢 Almacén"

        df_f = requisiciones.copy()

        # SLA/Alerta: >20 min sin entregar
        now = datetime.now()
        df_f["Min transcurridos"] = ((now - df_f["Fecha/Hora"]).dt.total_seconds() / 60).round().astype("Int64")
        df_f["Alerta"] = df_f.apply(
            lambda r: "⏰ >20m" if pd.notna(r["Min transcurridos"]) and r["Estatus"] != "Entregado" and r["Min transcurridos"] >= 20 else "",
            axis=1
        )

        # Filtros
        if st.session_state["filtros"]["areas"]:
            df_f = df_f[df_f["Área"].isin(st.session_state["filtros"]["areas"])]
        if st.session_state["filtros"]["estatus"]:
            df_f = df_f[df_f["Estatus"].isin(st.session_state["filtros"]["estatus"])]

        rf = st.session_state["filtros"]["rango"]
        if isinstance(rf, (list, tuple)) and len(rf) == 2:
            start_dt = datetime.combine(rf[0], datetime.min.time())
            end_dt = datetime.combine(rf[1], datetime.max.time())
            df_f = df_f[(df_f["Fecha/Hora"] >= start_dt) & (df_f["Fecha/Hora"] <= end_dt)]

        if st.session_state["filtros"]["search"]:
            s = st.session_state["filtros"]["search"]
            mask = (
                df_f["Work Order"].str.lower().str.contains(s, na=False) |
                df_f["Número de parte"].str.lower().str.contains(s, na=False) |
                df_f["Número de lote"].str.lower().str.contains(s, na=False)
            )
            df_f = df_f[mask]

        df_f = df_f.sort_values("Fecha/Hora", ascending=False).reset_index(drop=True)

        if df_f.empty:
            st.warning("No hay resultados con los filtros actuales.")
        else:
            st.session_state["mapa_ids"] = list(df_f["ID"])

            columnas_vista = [
                "Fecha/Hora", "Área", "Work Order", "Número de parte",
                "Número de lote", "Cantidad", "Motivo", "Alerta", "Min transcurridos",
                "Almacenista", "Estatus", "Issue"
            ]
            df_vista = df_f[columnas_vista].copy()
            df_vista["Issue"] = df_f["Issue"].fillna(False).astype(bool)

            def on_editor_change():
                state = st.session_state.get("editor_almacen", {})
                edited_rows = state.get("edited_rows", {})
                if not edited_rows:
                    return
                base = requisiciones.set_index("ID")
                mapa_ids = st.session_state.get("mapa_ids", [])
                for idx_str, changes in edited_rows.items():
                    idx = int(idx_str)
                    if idx < len(mapa_ids):
                        row_id = mapa_ids[idx]
                        for col, val in changes.items():
                            if col in ["Almacenista", "Estatus", "Issue"]:
                                base.at[row_id, col] = val
                actualizado = base.reset_index()
                guardar_csv(actualizado)
                st.session_state["need_rerun"] = True
                st.session_state["page"] = "🏢 Almacén"

            st.data_editor(
                df_vista,
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "Fecha/Hora": st.column_config.DatetimeColumn("Fecha/Hora", format="YYYY-MM-DD HH:mm:ss", disabled=True),
                    "Área": st.column_config.TextColumn("Área", disabled=True),
                    "Work Order": st.column_config.TextColumn("Work Order", disabled=True),
                    "Número de parte": st.column_config.TextColumn("Número de parte", disabled=True),
                    "Número de lote": st.column_config.TextColumn("Número de lote", disabled=True),
                    "Cantidad": st.column_config.NumberColumn("Cantidad", disabled=True),
                    "Motivo": st.column_config.TextColumn("Motivo", disabled=True),
                    "Alerta": st.column_config.TextColumn("Alerta", disabled=True),
                    "Min transcurridos": st.column_config.NumberColumn("Min", disabled=True),
                    "Almacenista": st.column_config.TextColumn("Almacenista"),
                    "Estatus": st.column_config.SelectboxColumn(
                        "Estatus",
                        options=["Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"]
                    ),
                    "Issue": st.column_config.CheckboxColumn(
                        "Issue",
                        help="Marca cuando el material ya fue descontado del sistema",
                        default=False
                    ),
                },
                disabled=["Fecha/Hora","Área","Work Order","Número de parte","Número de lote","Cantidad","Motivo","Alerta","Min transcurridos"],
                key="editor_almacen",
                on_change=on_editor_change
            )

        if st.session_state.get("need_rerun", False):
            st.session_state["need_rerun"] = False
            st.session_state["page"] = "🏢 Almacén"
            st.experimental_set_query_params(_=str(time.time()))
            st.rerun()

        if st.session_state["auto_refresh"]:
            time.sleep(10)
            st.session_state["page"] = "🏢 Almacén"
            st.rerun()