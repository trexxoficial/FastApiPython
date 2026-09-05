import matplotlib

from fastapi import FastAPI, Response, UploadFile, File, Form, HTTPException, Request
# CORRECCIÓN CRÍTICA: Esto evita que el servidor se cierre en Windows
matplotlib.use('Agg') 

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.wsgi import WSGIMiddleware
from flask import Flask 
import json
import traceback

import pandas as pd
import plotly.express as px
from dash import Dash, html, dcc, dash_table
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# IMPORTACIÓN DE TU MÓDULOS
from resolucion_contratos_umayor_generator import procesar_resolucion_contrato, normalizar_clave
from recibo_satisfaccion import procesar_recibo, DatosContrato

from cv_generator import crear_docx_cv 
import weasyprint
from jinja2 import Environment, FileSystemLoader

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

@app.post("/api/generar-cv")
async def generar_cv(data: str = Form(...), foto: UploadFile = File(None)):
    cv_data = json.loads(data)
    
    # Configurar Jinja2 para leer tu HTML
    env = Environment(loader=FileSystemLoader('graficos/plantillas'))
    template = env.get_template('/graficos/cv_template.html')
    
    # Si hay foto, puedes guardarla temporalmente y pasar la ruta, o convertirla a Base64 para inyectarla en el HTML
    foto_b64 = await convertir_a_base64(foto) if foto else None
    
    # Renderizar el HTML con los datos (incluyendo el colorTema que agregamos)
    html_out = template.render(
        personal=cv_data.get('personal', {}),
        experiencia=cv_data.get('experiencia', []),
        formacion=cv_data.get('formacion', []),
        skills=cv_data.get('skills', []),
        color_tema=cv_data.get('colorTema', '#5e72e4'),
        foto_base64=foto_b64
    )
    
    # Generar el PDF
    pdf_bytes = weasyprint.HTML(string=html_out).write_pdf()
    
    return Response(content=pdf_bytes, media_type="application/pdf")

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
    



@app.post("/generar-resolucion-contrato-umayor")
async def generar_resolucion_contrato_endpoint(request: Request):
    try:
        data = await request.json()
        
        # Generar el archivo
        archivo_stream = procesar_resolucion_contrato(data)

        # Extraer datos para el nombre del archivo usando la función normalizada
        # Esto evita errores si en el JSON viene "Nombre_Completo" o "nombre_completo"
        nro = data.get("numero_resolucion", data.get("Numero_Resolucion", "0"))
        nom = data.get("nombre_completo", data.get("Nombre_Completo", "Documento"))
        
        # Limpiamos el nombre para el archivo físico
        nombre_archivo = f"Resolucion_{nro}_{str(nom).replace(' ', '_')}.docx"
        
        return StreamingResponse(
            archivo_stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'}
        )
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    

@app.get("/descargar-plantilla-resolucion-excel")
def descargar_plantilla_excel():
    # Se agrega la carpeta 'plantillas/' a la ruta
    file_path = "plantillas/data_resoluciones.xlsx"
    
    # Validamos que el archivo exista en el servidor
    if not os.path.exists(file_path):
        return {"error": "El archivo de plantilla no se encuentra en el servidor."}
        
    return FileResponse(
        path=file_path,
        filename="data_resoluciones.xlsx",
        # Este es el tipo MIME exacto para archivos Excel con macros (.xlsm)
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12" 
    )



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
    data: str = Form(...), 
    foto: UploadFile = File(None)
):
    try:
        data_dict = json.loads(data)
        
        # 1. LEER BYTES DE FOTO
        foto_bytes = None
        if foto:
            print(f"📸 Recibida foto: {foto.filename}")
            foto_bytes = await foto.read() # <--- Leemos los bytes

        # 2. PASAR LOS BYTES A LA FUNCIÓN (¡Aquí estaba el error!)
        # Antes tenías: crear_docx_cv(data_dict)
        # Ahora pon:
        file_stream = crear_docx_cv(data_dict, foto_bytes) 
        
        # ... resto del código (nombre archivo, headers, return) ...
        nombre = data_dict.get('personal', {}).get('nombre', 'Curriculum')
        filename = f"HV_{nombre.replace(' ', '_')}.docx"
        
        return StreamingResponse(
            file_stream, 
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )

    except Exception as e:
        print("\n🔥 ERROR CRÍTICO DETALLADO:")
        traceback.print_exc()  # <--- Esto imprimirá el error real en la consola negra
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    



# Rúbrica para evaluar Recursos Educativos Digitales (RED)
class CriterioInput(BaseModel):
    nombre: str
    valor: float  # Valor decimal, ej: 0.15 para 15%
    peso_maximo: int  # 15, 10 o 5, para aplicar la escala correcta

class EvaluacionRequest(BaseModel):
    resultado_global: float  # Valor decimal, ej: 0.92 para 92%
    criterios: List[CriterioInput]
    evaluador: str = "Joaquin Lara Sierra"

class CriterioOutput(BaseModel):
    nombre: str
    nivel: str
    color_hex: str

class EvaluacionResponse(BaseModel):
    nivel_global: str
    mensaje_global: str
    color_global_hex: str
    criterios_evaluados: List[CriterioOutput]
    recomendaciones: List[str]
    texto_salida: str

# =========================
# LÓGICA DE NEGOCIO
# =========================

def obtener_nivel_global(resultado: float) -> tuple:
    if resultado >= 92:
        return "Excelente", "Excelente: Diseño pedagógico robusto, contextualizado e innovador.", "#00B0F0"
    elif resultado >= 87:
        return "Bueno", "Bueno: Cumple con los criterios, con oportunidades de mejora.", "#0070C0"
    elif resultado >= 74:
        return "Aceptable", "Aceptable: Base lograda, requiere fortalecimiento.", "#FFC000"
    elif resultado >= 61:
        return "Insuficiente", "Insuficiente: Debilidades importantes.", "#FF6600"
    else:
        return "Deficiente", "?? Deficiente: No cumple criterios mínimos.", "#FF0000"

def evaluar_criterio(valor: float, peso_maximo: int) -> tuple:
    nivel = "Deficiente"
    color = "#FFC7CE" # Deficiente por defecto
    
    if peso_maximo == 15:
        if valor >= 15: nivel = "Excelente"
        elif valor >= 13: nivel = "Bueno"
        elif valor >= 11: nivel = "Aceptable"
        elif valor >= 9: nivel = "Insuficiente"
    elif peso_maximo == 10:
        if valor >= 10: nivel = "Excelente"
        elif valor >= 9: nivel = "Bueno"
        elif valor >= 8: nivel = "Aceptable"
        elif valor >= 7: nivel = "Insuficiente"
    elif peso_maximo == 5:
        if valor >= 5: nivel = "Excelente"
        elif valor >= 4: nivel = "Bueno"
        elif valor >= 3: nivel = "Aceptable"
        elif valor >= 2: nivel = "Insuficiente"

    # Asignación de colores según nivel
    if nivel == "Excelente": color = "#C6EFCE"
    elif nivel == "Bueno": color = "#BDD7EE"
    elif nivel == "Aceptable": color = "#FFEB9C"
    elif nivel == "Insuficiente": color = "#FFC000"

    return nivel, color

def generar_recomendacion(criterio_nombre: str) -> Optional[str]:
    nombre_lower = criterio_nombre.lower()
    if "pertinencia" in nombre_lower:
        return "**Contextualizar mejor al entorno y necesidades del estudiante."
    if "contenido" in nombre_lower:
        return "**Mejorar profundidad conceptual y organización."
    if "alineación" in nombre_lower or "alineacion" in nombre_lower:
        return "**Alinear objetivos, actividades y evaluación."
    if "diseño" in nombre_lower or "diseno" in nombre_lower:
        return "**Fortalecer interacción y estrategias didácticas."
    if "usabilidad" in nombre_lower:
        return "**Simplificar navegación y experiencia de usuario."
    if "accesibilidad" in nombre_lower:
        return "**Incorporar principios de inclusión y accesibilidad."
    if "técnica" in nombre_lower or "tecnica" in nombre_lower or "multimedia" in nombre_lower:
        return "**Mejorar calidad técnica y recursos multimedia."
    if "evaluación" in nombre_lower or "evaluacion" in nombre_lower:
        return "**Fortalecer instrumentos de evaluación y feedback."
    if "reutilización" in nombre_lower or "reutilizacion" in nombre_lower:
        return "**Optimizar posibilidades de reutilización y actualización."
    return None

# =========================
# ENDPOINT
# =========================

@app.post("/api/v1/evaluar-red", response_model=EvaluacionResponse)
def evaluar_red(payload: EvaluacionRequest):
    resultado_porcentaje = payload.resultado_global * 100
    nivel_glb, msj_glb, color_glb = obtener_nivel_global(resultado_porcentaje)
    
    criterios_out = []
    recomendaciones_out = []
    texto_criterios = "\n\n== Análisis por criterios: ==\n"
    
    for crit in payload.criterios:
        valor_porcentaje = crit.valor * 100
        nivel_crit, color_crit = evaluar_criterio(valor_porcentaje, crit.peso_maximo)
        
        criterios_out.append(CriterioOutput(
            nombre=crit.nombre,
            nivel=nivel_crit,
            color_hex=color_crit
        ))
        
        texto_criterios += f"• {crit.nombre}: {nivel_crit}\n"
        
        if nivel_crit in ["Insuficiente", "Deficiente"]:
            recom = generar_recomendacion(crit.nombre)
            if recom:
                if recom not in recomendaciones_out: # Evitar duplicados si aplican varias reglas
                    recomendaciones_out.append(recom)
                texto_criterios += recom + "\n"

    texto_final = f"{msj_glb}{texto_criterios}\n\nEvaluador: {payload.evaluador}"
    
    return EvaluacionResponse(
        nivel_global=nivel_glb,
        mensaje_global=msj_glb,
        color_global_hex=color_glb,
        criterios_evaluados=criterios_out,
        recomendaciones=recomendaciones_out,
        texto_salida=texto_final
    )