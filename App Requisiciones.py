import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ================================
# CONFIGURACIÓN INICIAL
# ================================
st.set_page_config(page_title="Sistema de Requisiciones", layout="wide")

if "msg_ok" not in st.session_state:
    st.session_state.msg_ok = False

if "reset_form" not in st.session_state:
    st.session_state.reset_form = False

if "guardando" not in st.session_state:
    st.session_state.guardando = False

# ================================
# FUNCIONES PARA CSV
# ================================
def cargar_datos():
    ruta = "data/requisiciones.csv"
    if not os.path.exists(ruta):
        df = pd.DataFrame(columns=[
            "ID","fecha_hora","cuarto","work_order","numero_parte","numero_lote",
            "cantidad","motivo","status","almacenista","issue"
        ])
        df.to_csv(ruta, index=False)
    return pd.read_csv(ruta)

def guardar_datos(df):
    df.to_csv("data/requisiciones.csv", index=False)

# ================================
# GENERAR ID
# ================================
def generar_id():
    df = cargar_datos()
    if df.empty:
        return "REQ-0001"
    ultimo = df["ID"].str.replace("REQ-", "").astype(int).max()
    return f"REQ-{ultimo+1:04d}"

# ================================
# INTERFAZ — PESTAÑAS
# ================================
tab1, tab2 = st.tabs(["➕ Registrar Requisición", "📦 Almacén"])


# ============================================================
# TAB 1 — REGISTRAR
# ============================================================
with tab1:

    st.markdown("<h2>Registrar Requisición</h2>", unsafe_allow_html=True)

    # FORMULARIO
    col1, col2 = st.columns(2)

    with col1:
        st.session_state.form_cuarto = st.selectbox("Cuarto", ["INTRODUCER"])
        st.session_state.form_work = st.text_input("Work Order")
        st.session_state.form_parte = st.text_input("Número de Parte")

    with col2:
        st.session_state.form_lote = st.text_input("Número de Lote")
        st.session_state.form_cantidad = st.number_input("Cantidad", min_value=1)
        st.session_state.form_motivo = st.selectbox("Motivo", ["Proceso"])

    # BOTÓN GUARDAR
    if st.button("Guardar Requisición"):

        # Anti doble click
        if st.session_state.get("guardando", False):
            st.warning("⌛ Procesando… por favor espere.")
            st.stop()

        st.session_state.guardando = True

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

        # Guardar en CSV
        df = pd.concat([df, pd.DataFrame([nueva_fila])], ignore_index=True)
        guardar_datos(df)

        # ================================================
        # ENVIAR TAMBIÉN A SMARTSHEET
        # ================================================
        try:
            import smartsheet
            token = st.secrets["SMARTSHEET_TOKEN"]
            sheet_id = int(st.secrets["SHEET_ID"])
            client = smartsheet.Smartsheet(token)

            new_row = smartsheet.models.Row()
            new_row.to_top = True

            new_row.cells = [
                {"column_id": 675059519648644, "value": nueva_fila["ID"]},
                {"column_id": 612161207095172, "value": nueva_fila["fecha_hora"]},
                {"column_id": 511576083446566, "value": nueva_fila["cuarto"]},
                {"column_id": 286396102278042, "value": nueva_fila["work_order"]},
                {"column_id": 736756064815916, "value": nueva_fila["numero_parte"]},
                {"column_id": 173860111393776, "value": nueva_fila["numero_lote"]},
                {"column_id": 602471630472892, "value": nueva_fila["cantidad"]},
                {"column_id": 398986027672304, "value": nueva_fila["motivo"]},
                {"column_id": 849360455493530, "value": nueva_fila["status"]},
                {"column_id": 330662302384516, "value": nueva_fila["almacenista"]},
                {"column_id": 484328658775501, "value": bool(nueva_fila["issue"])},
            ]

            response = client.Sheets.add_rows(sheet_id, [new_row])

            if response.message != "SUCCESS":
                st.error(f"❌ Error Smartsheet: {response.message}")

        except Exception as e:
            st.error("❌ Error al enviar a Smartsheet")
            st.write(e)

        # FIN DEL PROCESO
        st.session_state.guardando = False
        st.session_state.msg_ok = True
        st.session_state.reset_form = True

        st.rerun()


# ============================================================
# TAB 2 — PANEL ALMACÉN
# ============================================================
with tab2:

    st.markdown("<h2>Panel de Almacén</h2>", unsafe_allow_html=True)

    pwd = st.text_input("Ingrese contraseña", type="password")
    if pwd != st.secrets["ALMACEN_PASSWORD"]:
        st.warning("🔒 Acceso restringido.")
        st.stop()

    df = cargar_datos()

    st.dataframe(df, use_container_width=True)

    # EDITAR REQUISICIÓN
    st.markdown("### Editar requisición")
    lista_ids = list(df["ID"])
    seleccion = st.selectbox("Seleccionar ID", [""] + lista_ids)

    if seleccion:
        fila = df[df["ID"] == seleccion].iloc[0]
        idx = df[df["ID"] == seleccion].index[0]

        col1, col2 = st.columns(2)

        with col1:
            nuevo_status = st.selectbox(
                "Status",
                ["Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"],
                index=["Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"].index(fila["status"])
            )

            nuevo_almacenista = st.text_input("Almacenista", fila["almacenista"])

        with col2:
            nuevo_issue = st.checkbox("Issue", value=bool(fila["issue"]))

        if st.button("Guardar cambios"):

            df.at[idx, "status"] = nuevo_status
            df.at[idx, "almacenista"] = nuevo_almacenista
            df.at[idx, "issue"] = nuevo_issue

            guardar_datos(df)

            st.success("✔ Requisición actualizada.")
            st.rerun()
