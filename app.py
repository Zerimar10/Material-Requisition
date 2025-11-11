import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

# ==========================
# 🔐 CARGAR VARIABLES SECRETAS
# ==========================
CLAVE_ALMACEN = os.getenv("CLAVE_ALMACEN", "almacen2025")
SMARTSHEET_TOKEN = os.getenv("SMARTSHEET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CSV_FILE = "requisiciones.csv"

# ==========================
# 📦 CONFIGURAR CABECERAS API
# ==========================
headers = {
    "Authorization": f"Bearer {SMARTSHEET_TOKEN}",
    "Content-Type": "application/json"
}

# ==========================
# 🧭 FUNCIÓN: OBTENER COLUMNAS
# ==========================
def obtener_columnas():
    try:
        url = f"https://api.smartsheet.com/2.0/sheets/{SHEET_ID}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        columnas = {col["title"]: col["id"] for col in data["columns"]}
        return columnas
    except requests.exceptions.HTTPError as e:
        st.error(f"⚠️ Error HTTP al conectar con Smartsheet: {e}")
    except Exception as e:
        st.error(f"❌ Error inesperado al obtener columnas: {e}")
    return None

# ==========================
# ✍️ FUNCIÓN: GUARDAR EN SMARTSHEET
# ==========================
def guardar_requisicion_smartsheet(area, fecha, work_order, num_parte, cantidad, motivo, status, almacenista, issue):
    columnas = obtener_columnas()
    if not columnas:
        return False

    try:
        row = {
            "toTop": True,
            "cells": [
                {"columnId": columnas["Area"], "value": area},
                {"columnId": columnas["Fecha/Hora"], "value": fecha},
                {"columnId": columnas["Work Order"], "value": work_order},
                {"columnId": columnas["Número de Parte"], "value": num_parte},
                {"columnId": columnas["Cantidad"], "value": cantidad},
                {"columnId": columnas["Motivo"], "value": motivo},
                {"columnId": columnas["Status"], "value": status},
                {"columnId": columnas["Almacenista"], "value": almacenista},
                {"columnId": columnas["Issue"], "value": issue},
            ]
        }

        url = f"https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows"
        response = requests.post(url, headers=headers, json={"rows": [row]})
        response.raise_for_status()
        st.success("✅ Requisición guardada correctamente en Smartsheet.")
        return True

    except requests.exceptions.HTTPError as e:
        st.error(f"⚠️ Error al guardar en Smartsheet: {e}")
        if response.text:
            st.code(response.text, language="json")
    except Exception as e:
        st.error(f"❌ Error inesperado al guardar la requisición: {e}")
    return False

# ==========================
# 📖 FUNCIÓN: LEER REQUISICIONES
# ==========================
def leer_requisiciones_smartsheet():
    try:
        url = f"https://api.smartsheet.com/2.0/sheets/{SHEET_ID}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        columnas = {col["id"]: col["title"] for col in data["columns"]}
        registros = []

        for row in data["rows"]:
            registro = {}
            for cell in row["cells"]:
                col_name = columnas.get(cell["columnId"], None)
                if col_name:
                    registro[col_name] = cell.get("displayValue", "")
            registros.append(registro)

        return pd.DataFrame(registros)

    except requests.exceptions.HTTPError as e:
        st.error(f"⚠️ Error al leer datos desde Smartsheet: {e}")
    except Exception as e:
        st.error(f"❌ Error inesperado al leer requisiciones: {e}")
    return pd.DataFrame()

# ==========================
# 🎨 INTERFAZ DE STREAMLIT
# ==========================
st.set_page_config(page_title="Sistema de Requisiciones de Almacén", layout="wide")

# Logo Nordson
st.image(
    "https://upload.wikimedia.org/wikipedia/commons/4/4b/Nordson_logo.svg",
    width=200,
)
st.title("📦 Sistema de Requisiciones de Almacén")

# Pestañas principales
tab1, tab2 = st.tabs(["➕ Nueva Requisición", "📋 Lista de Requisiciones"])

# ==========================
# 🧾 TAB 1 – NUEVA REQUISICIÓN
# ==========================
with tab1:
    st.subheader("Registrar nueva requisición")

    area = st.text_input("Área")
    work_order = st.text_input("Work Order")
    num_parte = st.text_input("Número de Parte")
    cantidad = st.number_input("Cantidad", min_value=1, step=1)
    motivo = st.text_input("Motivo")
    status = st.selectbox("Status inicial", ["Pendiente", "Entregado", "Proceso"])
    almacenista = st.text_input("Almacenista")
    issue = st.checkbox("Issue", value=False)

    if st.button("Enviar requisición"):
        fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        if guardar_requisicion_smartsheet(
            area, fecha, work_order, num_parte, cantidad, motivo, status, almacenista, str(issue)
        ):
            st.success("✅ Requisición registrada correctamente.")
        else:
            st.warning("⚠️ No se pudo guardar la requisición en Smartsheet.")

# ==========================
# 📋 TAB 2 – LISTA DE REQUISICIONES
# ==========================
with tab2:
    st.subheader("Lista de Requisiciones Registradas")

    df = leer_requisiciones_smartsheet()

    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            area_filtro = st.multiselect("Área(s)", sorted(df["Area"].dropna().unique()))
        with col2:
            status_filtro = st.multiselect("Status", sorted(df["Status"].dropna().unique()))
        with col3:
            busqueda = st.text_input("Buscar (Work Order / Número de Parte / Motivo)")

        # Aplicar filtros
        df_filtrado = df.copy()
        if area_filtro:
            df_filtrado = df_filtrado[df_filtrado["Area"].isin(area_filtro)]
        if status_filtro:
            df_filtrado = df_filtrado[df_filtrado["Status"].isin(status_filtro)]
        if busqueda:
            df_filtrado = df_filtrado[df_filtrado.apply(lambda x: busqueda.lower() in str(x).lower(), axis=1)]

        st.dataframe(df_filtrado, use_container_width=True)
    else:
        st.warning("⚠️ No se pudieron cargar las requisiciones desde Smartsheet.")
