import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import os
import json
import requests
from dotenv import load_dotenv
from PIL import Image

# =====================================
# CONFIGURACIÓN INICIAL
# =====================================
st.set_page_config(page_title="Sistema de Requisiciones de Almacén", layout="wide")

# Cargar variables del archivo .env (si existe)
load_dotenv()
SMARTSHEET_TOKEN = os.getenv("SMARTSHEET_TOKEN") or "TU_TOKEN_DE_API"
SHEET_ID = "9WVHx67PGhCqV7wvf469M888CCPJ5pwmm2V78hm1" # tu hoja real
CSV_FILE = "requisiciones.csv"

# =====================================
# ENCABEZADO CORPORATIVO
# =====================================
try:
    logo = Image.open("nordson_logo.png")
    col1, col2 = st.columns([1, 5], vertical_alignment="center")
    with col1:
        st.image(logo, width=110)
    with col2:
        st.markdown(
            """
            <h1 style='color:#004C97; font-weight:700; margin-bottom:5px;'>Nordson Warehouse System</h1>
            <h5 style='color:#5F6B7B; margin-top:0;'>Sistema de Requisiciones de Almacén</h5>
            """,
            unsafe_allow_html=True
        )
except:
    st.warning("⚠️ No se encontró el archivo 'nordson_logo.png'. El logo no se mostrará.")

st.markdown("<hr style='margin-top:-10px;'>", unsafe_allow_html=True)

# =====================================
# FUNCIONES AUXILIARES
# =====================================
def cargar_requisiciones():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        columnas = ["ID", "Area", "Fecha/Hora", "Work Order", "Número de Parte",
                    "Cantidad", "Motivo", "Status", "Almacenista", "Issue"]
        return pd.DataFrame(columns=columnas)

def guardar_requisiciones(df):
    df.to_csv(CSV_FILE, index=False)

# Enviar una nueva requisición a Smartsheet
def guardar_en_smartsheet(datos):
    columnas = {
        "Area": 6750550919648644,
        "Fecha/Hora": 5178655547019140,
        "Work Order": 2926855733333892,
        "Número de Parte": 7340355360704388,
        "Cantidad": 4306604313497476,
        "Motivo": 8810203940867972,
        "Status": 2252171519129694,
        "Almacenista": 4728816778534660,
        "Issue": 2477016946878212,
    }

    row = {
        "toBottom": True,
        "cells": [
            {"columnId": columnas["Area"], "value": datos["Area"]},
            {"columnId": columnas["Fecha/Hora"], "value": datos["Fecha/Hora"]},
            {"columnId": columnas["Work Order"], "value": datos["Work Order"]},
            {"columnId": columnas["Número de Parte"], "value": datos["Número de Parte"]},
            {"columnId": columnas["Cantidad"], "value": datos["Cantidad"]},
            {"columnId": columnas["Motivo"], "value": datos["Motivo"]},
            {"columnId": columnas["Status"], "value": datos["Status"]},
            {"columnId": columnas["Almacenista"], "value": datos["Almacenista"]},
            {"columnId": columnas["Issue"], "value": datos["Issue"]},
        ],
    }

    url = f"https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows"
    headers = {
        "Authorization": f"Bearer {SMARTSHEET_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps({"rows": [row]}), verify=False)
        response.raise_for_status()
        st.success("✅ Requisición guardada también en Smartsheet.")
    except Exception as e:
        st.warning(f"⚠️ No se pudo guardar en Smartsheet: {e}")

# =====================================
# INTERFAZ PRINCIPAL
# =====================================
tabs = st.tabs(["📦 Producción", "🏭 Almacén"])

# =====================================
# TAB DE PRODUCCIÓN
# =====================================
with tabs[0]:
    st.subheader("Nueva Requisición")

    # Cargar data existente
    requisiciones = cargar_requisiciones()

    with st.form("form_requisicion"):
        area = st.selectbox("Area", ["Introducer", "PU1", "PU2", "PU3", "PU4", "PVC1", "PVC2",
                                     "PVC3A", "PVC3B", "PVC6", "PVC7", "PVCS", "PAK1",
                                     "MM CL", "MM MOLD", "MM FP", "MIXING", "RESORTES"])
        work_order = st.text_input("Work Order")
        numero_parte = st.text_input("Número de Parte")
        cantidad = st.number_input("Cantidad", min_value=1, step=1)
        motivo = st.selectbox("Motivo", ["Proceso", "Prueba", "Retrabajo", "Muestra"])
        proceso = st.selectbox("Estatus inicial", ["Pendiente"])
        almacenista = ""
        issue = False

        submitted = st.form_submit_button("Enviar requisición")

        if submitted:
            nueva_requisicion = {
                "ID": str(uuid.uuid4())[:8],
                "Area": area,
                "Fecha/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Work Order": work_order,
                "Número de Parte": numero_parte,
                "Cantidad": cantidad,
                "Motivo": motivo,
                "Status": proceso,
                "Almacenista": almacenista,
                "Issue": issue,
            }

            requisiciones = pd.concat([pd.DataFrame([nueva_requisicion]), requisiciones], ignore_index=True)
            guardar_requisiciones(requisiciones)
            guardar_en_smartsheet(nueva_requisicion)
            st.success("✅ Requisición registrada correctamente.")
            st.rerun()

# =====================================
# TAB DE ALMACÉN
# =====================================
with tabs[1]:
    st.subheader("Lista de Requisiciones Registradas")
    requisiciones = cargar_requisiciones()

    # Filtros
    with st.expander("🔎 Filtros"):
        area_filtro = st.multiselect("Area(s)", options=sorted(requisiciones["Area"].unique()))
        estatus_filtro = st.multiselect("Status", options=["Pendiente", "En proceso", "Entregado", "Cancelado", "No encontrado"])
        rango_fecha = st.date_input("Rango de fechas")

    # Aplicar filtros
    df_filtrado = requisiciones.copy()
    if area_filtro:
        df_filtrado = df_filtrado[df_filtrado["Area"].isin(area_filtro)]
    if estatus_filtro:
        df_filtrado = df_filtrado[df_filtrado["Status"].isin(estatus_filtro)]

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)











