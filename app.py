import streamlit as st
import pandas as pd
import requests
import os
import uuid
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="Sistema de Requisiciones de Almacén", layout="wide")

# --- VARIABLES DE ENTORNO ---
CLAVE_ALMACEN = os.getenv("CLAVE_ALMACEN", "almacen2025")
SMARTSHEET_TOKEN = os.getenv("SMARTSHEET_TOKEN")
SHEET_ID = os.getenv("SHEET_ID")
CSV_FILE = "requisiciones.csv"

# --- LOGO CORPORATIVO ---
st.image("https://upload.wikimedia.org/wikipedia/commons/4/4b/Nordson_Corporation_logo.svg", width=220)
st.title("Sistema de Requisiciones de Almacén")

# --- FUNCIÓN PARA LEER CSV LOCAL ---
def cargar_requisiciones():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        return df
    else:
        columnas = ["ID", "Fecha/Hora", "Area", "Work Order", "Número de Parte", "Cantidad", "Motivo", "Status", "Almacenista", "Issue"]
        return pd.DataFrame(columns=columnas)

# --- FUNCIÓN PARA GUARDAR EN CSV LOCAL ---
def guardar_requisiciones(df):
    df.to_csv(CSV_FILE, index=False)

# --- FUNCIÓN PARA GUARDAR EN SMARTSHEET ---
def guardar_en_smartsheet(nueva_requisicion):
    if not SMARTSHEET_TOKEN or not SHEET_ID:
        st.warning("No se ha configurado la conexión con Smartsheet.")
        return False

    headers = {
        "Authorization": f"Bearer {SMARTSHEET_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        # Mapea las columnas según sus IDs (revisadas previamente con ver_columnas.py)
        columnas = {
            "Area": 6750559196486644,
            "Fecha/Hora": 5178655547019140,
            "Work Order": 2926855733333892,
            "Número de Parte": 7340353607038818,
            "Cantidad": 4366064339131476,
            "Motivo": 8810820958979772,
            "Status": 2252171512191694,
            "Almacenista": 4366064339131476,
            "Issue": 2477016964878212
        }

        data = {
            "toTop": True,
            "rows": [
                {"cells": [
                    {"columnId": columnas["Area"], "value": nueva_requisicion["Area"]},
                    {"columnId": columnas["Fecha/Hora"], "value": nueva_requisicion["Fecha/Hora"]},
                    {"columnId": columnas["Work Order"], "value": nueva_requisicion["Work Order"]},
                    {"columnId": columnas["Número de Parte"], "value": nueva_requisicion["Número de Parte"]},
                    {"columnId": columnas["Cantidad"], "value": nueva_requisicion["Cantidad"]},
                    {"columnId": columnas["Motivo"], "value": nueva_requisicion["Motivo"]},
                    {"columnId": columnas["Status"], "value": nueva_requisicion["Status"]},
                    {"columnId": columnas["Almacenista"], "value": nueva_requisicion["Almacenista"]},
                    {"columnId": columnas["Issue"], "value": nueva_requisicion["Issue"]}
                ]}
            ]
        }

        url = f"https://api.smartsheet.com/2.0/sheets/{SHEET_ID}/rows"
        resp = requests.post(url, headers=headers, json=data, verify=False)

        if resp.status_code == 200:
            st.success("✅ Requisición guardada también en Smartsheet.")
            return True
        else:
            st.error(f"⚠️ Error al guardar en Smartsheet: {resp.status_code} - {resp.text}")
            return False

    except Exception as e:
        st.error(f"❌ Error inesperado al conectar con Smartsheet: {e}")
        return False


# --- INTERFAZ PRINCIPAL ---
with st.form("form_requisicion"):
    area = st.text_input("Area")
    work_order = st.text_input("Work Order")
    numero_parte = st.text_input("Número de Parte")
    cantidad = st.number_input("Cantidad", min_value=1, step=1)
    motivo = st.text_input("Motivo")
    status = st.selectbox("Status inicial", ["Pendiente", "Proceso", "Entregado"])
    almacenista = st.text_input("Almacenista", value="")
    issue = st.text_input("Issue", value="")

    submitted = st.form_submit_button("Enviar requisición")

    if submitted:
        nueva_requisicion = {
            "ID": str(uuid.uuid4()),
            "Fecha/Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Area": area,
            "Work Order": work_order,
            "Número de Parte": numero_parte,
            "Cantidad": cantidad,
            "Motivo": motivo,
            "Status": status,
            "Almacenista": almacenista,
            "Issue": issue
        }

        df = cargar_requisiciones()
        df = pd.concat([df, pd.DataFrame([nueva_requisicion])], ignore_index=True)
        guardar_requisiciones(df)
        st.success("✅ Requisición registrada correctamente.")

        if guardar_en_smartsheet(nueva_requisicion):
            st.balloons()

# --- TABLA DE REQUISICIONES ---
st.header("📋 Lista de Requisiciones Registradas")
requisiciones = cargar_requisiciones()

if not requisiciones.empty:
    st.dataframe(requisiciones)
else:
    st.info("No hay requisiciones registradas todavía.")
