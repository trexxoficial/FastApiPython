from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse


import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

app = FastAPI()

CSV_FILE_PATH = "Violencia_clean.csv"

@app.get("/")
def root():
    return {
        "message": "API en Render OK. en V1. Usa /variables para consultar datos del CSV remoto."
    }

@app.get("/variables")
async def variables():
    try:
        df = pd.read_csv(CSV_FILE_PATH, sep=";")
        # descripcion = df.describe().to_dict()

        # resumen = {
        #     "filas": df.shape[0],
        #     "columnas": df.shape[1],
        #     "columnas_info": df.dtypes.astype(str).to_dict(),
        # }


         # Crear histograma
        plt.figure()
        plt.hist(df["Escolaridad"], bins=10, color='skyblue', edgecolor='black')
        plt.title("Histograma de Escolaridad")
        plt.xlabel("Escolaridad")
        plt.ylabel("Frecuencia")

        ruta = "histograma.png"
        plt.savefig(ruta)
        plt.close()
        
        return {
            "histograma": FileResponse(path=ruta, media_type="image/png", filename="histograma.png")
         }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))





















# def get_variables(columns: str = None):
#     try:
#         # Leer el archivo CSV
#         df = pd.read_csv(CSV_FILE_PATH)
#         return {"data": df['ICOUNT'].count()}
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail="Archivo CSV no encontrado")
#     except KeyError as e:
#         raise HTTPException(status_code=400, detail=f"Columna no encontrada: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error al procesar el archivo CSV: {str(e)}")

# Endpoint para descargar las variables en formato CSV


# @app.get("/variables/csv")
# def get_variables_csv(columns: str = None):
#     try:
#         # Leer el archivo CSV
#         df = pd.read_csv(CSV_FILE_PATH)
        
#         # Si se especifican columnas, filtrar el DataFrame
#         if columns:
#             column_list = columns.split(",")  # Dividir las columnas por comas
#             df = df[column_list]  # Filtrar el DataFrame
        
#         # Convertir el DataFrame a CSV en memoria
#         csv_data = df.to_csv(index=False)
        
#         # Devolver el archivo CSV como una respuesta
#         return Response(content=csv_data, media_type="text/csv")
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail="Archivo CSV no encontrado")
#     except KeyError as e:
#         raise HTTPException(status_code=400, detail=f"Columna no encontrada: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error al procesar el archivo CSV: {str(e)}")

# # Endpoint para descargar las variables en formato Excel
# @app.get("/variables/excel")
# def get_variables_excel(columns: str = None):
#     try:
#         # Leer el archivo CSV
#         df = pd.read_csv(CSV_FILE_PATH)
        
#         # Si se especifican columnas, filtrar el DataFrame
#         if columns:
#             column_list = columns.split(",")  # Dividir las columnas por comas
#             df = df[column_list]  # Filtrar el DataFrame
        
#         # Crear un archivo Excel en memoria
#         output = io.BytesIO()
#         with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
#             df.to_excel(writer, index=False)
        
#         # Devolver el archivo Excel como una respuesta
#         return Response(
#             content=output.getvalue(),
#             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#             headers={"Content-Disposition": "attachment; filename=variables.xlsx"}
#         )
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail="Archivo CSV no encontrado")
#     except KeyError as e:
#         raise HTTPException(status_code=400, detail=f"Columna no encontrada: {str(e)}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error al procesar el archivo CSV: {str(e)}")