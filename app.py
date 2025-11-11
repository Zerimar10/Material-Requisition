import streamlit as st
import pandas as pd
from datetime import datetime
import os
import uuid
import requests
from dotenv import load_dotenv

# ======================================================
# CONFIGURACIÓN INICIAL
# ======================================================
st.set_page_config(page_title="Sistema de Requisiciones de Almacén", layout="wide")

# Cargar variables del archivo .env
load_dotenv()
CLAVE_ALMACEN = os.getenv("CLAVE_ALMACEN", "almacen2025")
SMARTSHEET_TOKEN = os.getenv("SMARTSHEET_TOKEN")
SHEET_ID = "9WVHx67PGhCqV7wvf469M888CCPJ5pwmm2V78hm1" # tu ID real de hoja
CSV_FILE = "requisiciones.csv"

# Encabezado corporativo
from PIL import Image
logo = Image.open("nordson_logo.png")
c1, c2 = st.columns([1, 5], vertical_alignment="center")
with c1:
    st.image(logo, width=110)
with c2:
    st.markdown(
        """
        <h1 style="color:#0072CE; font-weight:700; margin-bottom:4px;">Nordson Warehouse System</h1>
        <h5 style="color:#5F6C7B; margin-top:0;">Sistema de requisiciones de almacén</h5>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ======================================================
# FUNCIONES AUXILIARES
# ======================================================
def guardar_en_smartsheet(data):
    """Guarda una requisición nueva en Smartsheet."""
    try:
        headers = {
            "Authorization": f"Bearer {SMARTSHEET_TOKEN}",
            "Content-Type": "application/json"
        }

        columnas = {
            "Area": 6750550919648644,
            "Fecha/Hora": 5178655547101940,
            "Work Order": 292685573333892,
            "Número de Parte": 7340355360704388,
            "Cantidad": 4306064313497476,
            "Motivo": 8810230940867972,
            "Estatus": 2252171519129644,
            "Almacenista": 4728816778536460,
            "Issue": 2477016694878212
        }

        row = {
            "toBottom": True,
            "cells": [
                {"columnId": columnas["Area"], "value": data["Area"]},
                {"columnId": columnas["Fecha/Hora"], "value": data["Fecha/Hora"]},
                {"columnId": columnas["Work Order"], "value": data["Work Order"]},
                {"columnId": columnas["Número de Parte"], "value": data["Número de Parte"]},
                {"columnId": columnas["Cantidad"], "value": data["Cantidad"]},
                {"columnId": columnas["Motivo"], "value": data["Motivo"]},
                {"columnId": columnas["Estatus"], "value": data["Estatus"]},
                {"columnId": columnas["Almacenista"], "value": data["Almacenista"]},
                {"columnId": columnas["Issue"], "value": data["Issue"]}
            ]
        }

        url = f"https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows"
        r = requests.post(url, headers=headers, json={"rows": [row]})
        r.raise_for_status()
        return True

    except Exception as e:
        st.warning(f"No se pudo guardar en Smartsheet: {e}")
        return False


def leer_smartsheet():
    """Lee las requisiciones directamente desde Smartsheet."""
    try:
        headers = {"Authorization": f"Bearer {SMARTSHEET_TOKEN}"}
        url = f"https://api.smartsheet.com/2.0/sheets/{SHEET_ID}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        columnas = {col["id"]: col["title"] for col in data["columns"]}
        registros = []
        for row in data["rows"]:
            fila = {}
            for cell in row["cells"]:
                col_name = columnas.get(cell["columnId"], "Desconocido")
                fila[col_name] = cell.get("displayValue", "")
            registros.append(fila)
        return pd.DataFrame(registros)

    except Exception as e:
        st.warning(f"No se pudo leer desde Smartsheet: {e}")
        if os.path.exists(CSV_FILE):
            return pd.read_csv(CSV_FILE)
        return pd.DataFrame()

# ======================================================
# INTERFAZ PRINCIPAL
# ======================================================
tabs = st.tabs(["📦 Producción", "🏭 Almacén"])

# ------------------------------------------------------
# TAB 1: PRODUCCIÓN
# ------------------------------------------------------
with tabs[0]:
    st.subheader("Nueva Requisición")
    area = st.selectbox("Área", ["Introducer", "PU", "PVC", "USMCA", "Tecate"])
    work_order = st.text_input("Work Order")
    numero_parte = st.text_input("Número de Parte")
    cantidad = st.number_input("Cantidad", min_value=1, step=1)
    motivo = st.text_input("Motivo", "Proceso")
    estatus = "Pendiente"
    almacenista = ""
    issue = False

    if st.button("Enviar requisición"):
        nueva_req = {
            "ID": str(uuid.uuid4()),
            "Area": area,
            "Fecha/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Work Order": work_order,
            "Número de Parte": numero_parte,
            "Cantidad": cantidad,
            "Motivo": motivo,
            "Estatus": estatus,
            "Almacenista": almacenista,
            "Issue": issue
        }

        # Guardar localmente
        if os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            df = pd.concat([df, pd.DataFrame([nueva_req])], ignore_index=True)
        else:
            df = pd.DataFrame([nueva_req])
        df.to_csv(CSV_FILE, index=False)

        # Guardar en Smartsheet
        if guardar_en_smartsheet(nueva_req):
            st.success("✅ Requisición guardada también en Smartsheet.")
        st.success("✅ Requisición registrada correctamente.")
        st.rerun()

# ------------------------------------------------------
# TAB 2: ALMACÉN
# ------------------------------------------------------
with tabs[1]:
    st.subheader("Lista de Requisiciones Registradas")
    requisiciones = leer_smartsheet()

    if requisiciones is not None and not requisiciones.empty:
        area_filtro = st.multiselect("Área(s)", options=sorted(requisiciones["Area"].dropna().unique()))
        estatus_filtro = st.multiselect("Estatus", options=sorted(requisiciones["Estatus"].dropna().unique()))
        buscar = st.text_input("Buscar (Work Order / Número de parte / Número de lote)")

        df_filtrado = requisiciones.copy()
        if area_filtro:
            df_filtrado = df_filtrado[df_filtrado["Area"].isin(area_filtro)]
        if estatus_filtro:
            df_filtrado = df_filtrado[df_filtrado["Estatus"].isin(estatus_filtro)]
        if buscar:
            df_filtrado = df_filtrado[df_filtrado.apply(lambda row: buscar.lower() in str(row.values).lower(), axis=1)]

        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    else:
        st.info("No hay requisiciones registradas aún.")

