from fastapi import FastAPI, HTTPException
import pandas as pd
import httpx
from io import StringIO

app = FastAPI()

CSV_FILE_PATH = "https://firebasestorage.googleapis.com/v0/b/davgui24-6182c.firebasestorage.app/o/analisis_de_datos%2FViolencia_clean.csv?alt=media&token=664ebff8-6ba3-403d-92f0-16ee795ab344"

@app.get("/")
def root():
    return {
        "message": "API en Render OK. en V4 .Usa /variables para consultar datos del CSV remoto."
    }

@app.get("/variables")
async def variables():
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(CSV_FILE_PATH)
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text), sep=";")

            resumen = {
                "filas": df.shape[0],
                "columnas": df.shape[1],
                "columnas_info": df.dtypes.astype(str).to_dict(),
            }

            return {"data": resumen}
    except httpx.HTTPError as e:
        print(f"Error descargando CSV 1: {e}")
        raise HTTPException(status_code=502, detail=f"Error descargando CSV: {e}")
    except Exception as e:
        print(f"Error descargando CSV 2: {e}")
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


@app.get("/variables/csv")
def get_variables_csv(columns: str = None):
    try:
        # Leer el archivo CSV
        df = pd.read_csv(CSV_FILE_PATH)
        
        # Si se especifican columnas, filtrar el DataFrame
        if columns:
            column_list = columns.split(",")  # Dividir las columnas por comas
            df = df[column_list]  # Filtrar el DataFrame
        
        # Convertir el DataFrame a CSV en memoria
        csv_data = df.to_csv(index=False)
        
        # Devolver el archivo CSV como una respuesta
        return Response(content=csv_data, media_type="text/csv")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo CSV no encontrado")
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Columna no encontrada: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo CSV: {str(e)}")

# Endpoint para descargar las variables en formato Excel
@app.get("/variables/excel")
def get_variables_excel(columns: str = None):
    try:
        # Leer el archivo CSV
        df = pd.read_csv(CSV_FILE_PATH)
        
        # Si se especifican columnas, filtrar el DataFrame
        if columns:
            column_list = columns.split(",")  # Dividir las columnas por comas
            df = df[column_list]  # Filtrar el DataFrame
        
        # Crear un archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        
        # Devolver el archivo Excel como una respuesta
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=variables.xlsx"}
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Archivo CSV no encontrado")
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Columna no encontrada: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar el archivo CSV: {str(e)}")