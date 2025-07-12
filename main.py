from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import HTMLResponse
from flask import Flask 

import pandas as pd
import plotly.express as px

from dash import Dash, html, dcc, dash_table
import dash


import matplotlib.pyplot as plt
import seaborn as sns

app = FastAPI()
CSV_FILE_PATH = "Violencia_clean.csv"


# **********************************
# ============ CARGAR Y PREPARAR DATOS ================
# Crear servidor Flask para Dash
# Leer CSV
CSV_FILE_PATH = "Violencia_clean.csv"
df = pd.read_csv(CSV_FILE_PATH, sep=",")
flask_server = Flask(__name__)
df.columns = df.columns.str.strip()

# Preparar datos
df_sexo = df['Sexo de la victima'].value_counts().reset_index()
df_sexo.columns = ['Sexo de la victima', 'Conteo']

fig1 = px.line(df_sexo, x="Sexo de la victima", y="Conteo", title="Conteo total por Sexo de la Víctima")

df_etnica = df.groupby(['Sexo de la victima', 'Pertenencia Étnica']).size().reset_index(name='conteo')

fig2 = px.line(df_etnica, x="Sexo de la victima", y="conteo", color="Pertenencia Étnica",
               title="Sexo de la Víctima por Pertenencia Étnica")

# Crear la app Dash sobre Flask
dash_app = Dash(
    __name__,
    server=flask_server,
    routes_pathname_prefix="/dashboard1/",  # ← importante terminar en "/"
    requests_pathname_prefix="/dashboard1/" # ← asegura carga correcta de assets
)
# Montar Dash sobre FastAPI usando WSGIMiddleware
app.mount("/", WSGIMiddleware(flask_server))

# Layout de Dash
dash_app.layout = html.Div([
    html.H1("Tablero de Violencia Intrafamiliar"),

    dcc.Graph(id='grafico1', figure=fig1),
    dcc.Graph(id='grafico2', figure=fig2),

    html.H2("Tabla de Datos Originales"),
    dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict("records"),
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_cell={'textAlign': 'left', 'padding': '5px'},
        style_header={'backgroundColor': 'lightgrey', 'fontWeight': 'bold'}
    )
])



# **********************************


# @app.get("/")
# def root():
#     return {
#         "message": "API en Render OK. en V1. Usa /variables para consultar datos del CSV remoto."
#     }

@app.get("/graficaPrueba")
async def variables():
    try:
        df = pd.read_csv(CSV_FILE_PATH, sep=",")
        # descripcion = df.describe().to_dict()

        # resumen = {
        #     "filas": df.shape[0],
        #     "columnas": df.shape[1],
        #     "columnas_info": df.dtypes.astype(str).to_dict(),
        # }


        # Gráfico de barras
        plt.figure(figsize=(10, 6))
        frec = df["Presunto Agresor"].value_counts()
        frec.plot(kind="bar", color="skyblue", edgecolor="black")
        plt.title("Frecuencia de Presuntos Agresores")
        plt.xlabel("Presunto Agresor")
        plt.ylabel("Cantidad")
        plt.xticks(rotation=75)
        plt.tight_layout()

        ruta = "graficos/grafico_barras.png"
        plt.savefig(ruta)
        plt.close()

        return FileResponse(path=ruta, media_type="image/png", filename="grafico_barras.png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    

@app.get("/", response_class=HTMLResponse)
async def root():
     return '<a href="/dashboard1/">Ir al Dashboard</a>'
