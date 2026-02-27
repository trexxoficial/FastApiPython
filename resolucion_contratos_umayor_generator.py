import io
import os
from pydantic import BaseModel
from docxtpl import DocxTemplate

class DatosResolucionContrato(BaseModel):
    numero_resolucion: str
    dia_resolucion: str
    Mes_Resolucion: str
    Año_Resolucion: str
    nombre_completo: str
    cedula: str
    facultad: str
    fecha_inicio: str
    fecha_Fin: str
    titulo: str
    valor_hora: str
    modalidad: str
    intensidad_horaria: str
    intensidad_mensual: str
    Total_Horas: str
    dedicacion: str
    decano: str

def formatear_fecha_espanol(fecha_str: str) -> str:
    if not fecha_str or "-" not in fecha_str:
        return fecha_str
    
    try:
        # Divide la fecha YYYY-MM-DD
        anio, mes, dia = fecha_str.split("-")
        
        meses = {
            "01": "enero", "02": "febrero", "03": "marzo",
            "04": "abril", "05": "mayo", "06": "junio",
            "07": "julio", "08": "agosto", "09": "septiembre",
            "10": "octubre", "11": "noviembre", "12": "diciembre"
        }
        
        # int(dia) quita el cero a la izquierda (ej. "08" -> "8")
        dia_limpio = str(int(dia))
        mes_texto = meses.get(mes, "")
        
        return f"{dia_limpio} de {mes_texto} del {anio}"
    except Exception:
        # En caso de error, retorna la fecha original
        return fecha_str

def procesar_resolucion_contrato(data: DatosResolucionContrato) -> io.BytesIO:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_plantilla = os.path.join(base_dir, "plantillas", "plantilla_resolucion.docx")
    
    if not os.path.exists(ruta_plantilla):
        raise ValueError(f"No se encontró la plantilla en: {ruta_plantilla}")
    
    doc = DocxTemplate(ruta_plantilla)
    
    if hasattr(data, 'model_dump'):
        context = data.model_dump()
    else:
        context = data.dict()
        
    # --- NUEVO: Sobrescribir las fechas con el nuevo formato ---
    context["fecha_inicio"] = formatear_fecha_espanol(context["fecha_inicio"])
    context["fecha_fin"] = formatear_fecha_espanol(context["fecha_fin"])
    # -----------------------------------------------------------
        
    doc.render(context)
    
    archivo_stream = io.BytesIO()
    doc.save(archivo_stream)
    archivo_stream.seek(0)
    
    return archivo_stream