import matplotlib

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# CORRECCIÓN CRÍTICA: Esto evita que el servidor se cierre en Windows
matplotlib.use('Agg') 

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.wsgi import WSGIMiddleware
from flask import Flask 
import json

import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, dash_table
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pydantic import BaseModel
from typing import List, Dict, Any

# IMPORTACIÓN DE TU MÓDULOS
from recibo_satisfaccion import procesar_recibo, DatosContrato
from cv_generator import crear_docx_cv 

app = FastAPI()

origins = [
    "http://localhost:4200",    # Puerto por defecto de Angular
    "http://127.0.0.1:4200",
    "*"                         # (Opcional) Permite a todo el mundo (útil para desarrollo)
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# **********************************
# ============ CARGAR Y PREPARAR DATOS DASH ================
# Crear servidor Flask para Dash
CSV_FILE_PATH = "Violencia.csv"
flask_server = Flask(__name__)

# Carga de datos con manejo de errores (para que no falle si falta el CSV)
try:
    if os.path.exists(CSV_FILE_PATH):
        df = pd.read_csv(CSV_FILE_PATH, sep=",")
        df.columns = df.columns.str.strip()
    else:
        print(f"Advertencia: El archivo {CSV_FILE_PATH} no se encuentra. Se usará un DataFrame vacío.")
        df = pd.DataFrame(columns=["Sexo de la victima", "Pertenencia Étnica", "Presunto Agresor"])
except Exception as e:
    print(f"Error leyendo el CSV: {e}")
    df = pd.DataFrame(columns=["Sexo de la victima", "Pertenencia Étnica", "Presunto Agresor"])

# Preparar figuras para Dash
if not df.empty:
    df_sexo = df['Sexo de la victima'].value_counts().reset_index()
    df_sexo.columns = ['Sexo de la victima', 'Conteo']
    fig1 = px.line(df_sexo, x="Sexo de la victima", y="Conteo", title="Conteo total por Sexo de la Víctima")

    if 'Pertenencia Étnica' in df.columns:
        df_etnica = df.groupby(['Sexo de la victima', 'Pertenencia Étnica']).size().reset_index(name='conteo')
        fig2 = px.line(df_etnica, x="Sexo de la victima", y="conteo", color="Pertenencia Étnica",
                       title="Sexo de la Víctima por Pertenencia Étnica")
    else:
        fig2 = px.line(title="Datos insuficientes para gráfica étnica")
else:
    fig1 = px.line(title="Sin datos disponibles")
    fig2 = px.line(title="Sin datos disponibles")

# Crear la app Dash sobre Flask
dash_app = Dash(
    __name__,
    server=flask_server,
    routes_pathname_prefix="/dashboard1/",
    requests_pathname_prefix="/dashboard1/"
)

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

# Montar Dash sobre FastAPI
app.mount("/dashboard1", WSGIMiddleware(flask_server))


# **********************************
# ============ ENDPOINTS DE LA API ================

# 1. Endpoint para Generar Recibos (NUEVO)
@app.post("/generar-recibo")
async def generar_recibo_endpoint(data: DatosContrato):
    try:
        # Invocamos la lógica del otro archivo
        archivo_stream = procesar_recibo(data)

        # Definimos el nombre del archivo
        nombre_archivo = f"Recibo_{data.proveedor.replace(' ', '_')}_Cuota{data.numero_cuota}.docx"
        
        # Devolvemos el archivo Word
        return StreamingResponse(
            archivo_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'}
        )

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Error generando recibo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 2. Endpoint de Gráfica de Prueba (EXISTENTE)
@app.get("/graficaPrueba")
async def variables():
    try:
        plt.figure(figsize=(10, 6))
        
        if not df.empty and "Presunto Agresor" in df.columns:
            frec = df["Presunto Agresor"].value_counts()
            frec.plot(kind="bar", color="skyblue", edgecolor="black")
            plt.title("Frecuencia de Presuntos Agresores")
            plt.xlabel("Presunto Agresor")
            plt.ylabel("Cantidad")
            plt.xticks(rotation=75)
            plt.tight_layout()
        else:
            plt.text(0.5, 0.5, 'Sin datos para graficar', ha='center')

        # Asegurar que la carpeta existe
        if not os.path.exists("graficos"):
            os.makedirs("graficos")

        ruta = "graficos/grafico_barras.png"
        plt.savefig(ruta)
        plt.close()

        return FileResponse(path=ruta, media_type="image/png", filename="grafico_barras.png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

# 3. Raíz
@app.get("/", response_class=HTMLResponse)
async def root():
     return """
     <html>
        <head><title>API UMAYOR</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>Bienvenido a la API de UMAYOR</h1>
            <ul>
                <li><a href="/dashboard1/">📊 Ver Dashboard de Violencia</a></li>
                <li><a href="/graficaPrueba">📉 Descargar Gráfica PNG</a></li>
                <li><a href="/docs">📄 Documentación API (Swagger)</a></li>
            </ul>
            <p><i>Endpoint disponible: POST /generar-recibo (Usar desde Excel)</i></p>
        </body>
     </html>
     """


# Definimos el modelo de datos para validación (opcional pero recomendado)
class ResumeData(BaseModel):
    personal: Dict[str, Any]
    formacion: List[Dict[str, Any]]
    experiencia: List[Dict[str, Any]]
    skills: List[str]
    diplomas: List[str]

@app.post("/generate-cv")
async def generate_cv_endpoint(
    data: str = Form(...),        # Recibe el JSON como texto
    foto: UploadFile = File(None) # Recibe el archivo (opcional)
):
    try:
        # 1. Parsear el JSON que viene de Angular
        data_dict = json.loads(data)
        
        # 2. (Opcional) Aquí procesaríamos la foto más adelante
        if foto:
            print(f"Recibida foto: {foto.filename}")
            # content = await foto.read()
            # data_dict['foto_bytes'] = content 

        # 3. Generar el Word
        file_stream = crear_docx_cv(data_dict)
        
        # 4. Preparar nombre del archivo
        nombre_archivo = data_dict['personal'].get('nombre', 'Curriculum').replace(" ", "_")
        filename = f"HV_{nombre_archivo}.docx"
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        return StreamingResponse(
            file_stream, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers=headers
        )
        
    except Exception as e:
        # ESTO ES LO QUE NECESITAMOS VER SI FALLA
        print(f"🔥 ERROR EN EL SERVIDOR: {str(e)}") 
        raise HTTPException(status_code=500, detail=str(e))