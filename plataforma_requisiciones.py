
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Load the Excel file
excel_file = "Requisición de Materiales.xlsm"

# Read all sheet names
xls = pd.ExcelFile(excel_file, engine="openpyxl")
sheet_names = xls.sheet_names

# Define user roles
st.sidebar.title("Acceso")
role = st.sidebar.selectbox("Selecciona tu rol", ["Producción", "Almacén"])
linea = None
if role == "Producción":
    linea = st.sidebar.selectbox("Selecciona tu línea de producción", [s for s in sheet_names if s not in ["Raw", "Almacén"]])

# Define motivos y estados
motivos = ["Proceso", "Extra", "Scrap", "Navajas", "Tooling"]
estados = ["En proceso", "Entregado", "Cancelado", "No encontrado"]

# Producción: formulario de solicitud
if role == "Producción" and linea:
    st.title(f"Solicitud de Componentes - Línea {linea}")
    with st.form("form_solicitud"):
        work_order = st.text_input("Work Order")
        numero_parte = st.text_input("Número de Parte")
        lote = st.text_input("Número de Lote")
        cantidad = st.number_input("Cantidad", min_value=1)
        motivo = st.selectbox("Motivo", motivos)
        submit = st.form_submit_button("Enviar solicitud")

    if submit:
        nueva_solicitud = {
            "Fecha": datetime.now().strftime("%Y-%m-%d"),
            "Hora": datetime.now().strftime("%H:%M:%S"),
            "Work Order": work_order,
            "Número de Parte": numero_parte,
            "Lote": lote,
            "Cantidad": cantidad,
            "Motivo": motivo,
            "Línea": linea,
            "Estado": "En proceso",
            "Surtidor": ""
        }
        df_linea = pd.read_excel(excel_file, sheet_name=linea, engine="openpyxl")
        df_linea = pd.concat([df_linea, pd.DataFrame([nueva_solicitud])], ignore_index=True)
        with pd.ExcelWriter(excel_file, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_linea.to_excel(writer, sheet_name=linea, index=False)
        st.success("Solicitud enviada correctamente.")

# Almacén: panel de control
elif role == "Almacén":
    st.title("Panel de Almacén")
    df_almacen = pd.read_excel(excel_file, sheet_name="Almacén", engine="openpyxl")
    df_almacen["Retraso"] = False

    # Calcular retrasos
    now = datetime.now()
    for i, row in df_almacen.iterrows():
        try:
            hora_ingreso = datetime.strptime(str(row["Hora"]), "%H:%M:%S")
            if now - hora_ingreso > timedelta(minutes=20):
                df_almacen.at[i, "Retraso"] = True
        except:
            continue

    # Mostrar tabla con colores
    def color_estado(val):
        if val == "En proceso":
            return "background-color: yellow"
        elif val == "Entregado":
            return "background-color: lightgreen"
        elif val == "No encontrado":
            return "background-color: red"
        return ""

    def color_retraso(val):
        return "background-color: red" if val else ""

    st.dataframe(df_almacen.style.applymap(color_estado, subset=["Estado"]).applymap(color_retraso, subset=["Retraso"]))

    # Actualizar estado
    st.subheader("Actualizar solicitud")
    index = st.number_input("Índice de solicitud", min_value=0, max_value=len(df_almacen)-1)
    nuevo_estado = st.selectbox("Nuevo estado", estados)
    surtidor = st.text_input("Nombre del surtidor")
    actualizar = st.button("Actualizar")

    if actualizar:
        df_almacen.at[index, "Estado"] = nuevo_estado
        df_almacen.at[index, "Surtidor"] = surtidor
        with pd.ExcelWriter(excel_file, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df_almacen.to_excel(writer, sheet_name="Almacén", index=False)
        st.success("Solicitud actualizada correctamente.")
