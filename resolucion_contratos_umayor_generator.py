import io
import os
import unicodedata
from docxtpl import DocxTemplate

def normalizar_clave(clave: str) -> str:
    # Quita acentos y pasa a minúsculas (Ej: "Decano" -> "decano")
    clave_limpia = ''.join((c for c in unicodedata.normalize('NFD', clave) if unicodedata.category(c) != 'Mn'))
    # Reemplazamos espacios por guiones bajos por si acaso, y todo a minúsculas
    return clave_limpia.lower().strip().replace(" ", "_")

def formatear_fecha_espanol(fecha_str: str) -> str:
    if not fecha_str or "-" not in str(fecha_str):
        return str(fecha_str) if fecha_str else ""
    try:
        anio, mes, dia = str(fecha_str).split("-")
        meses = {
            "01": "enero", "02": "febrero", "03": "marzo",
            "04": "abril", "05": "mayo", "06": "junio",
            "07": "julio", "08": "agosto", "09": "septiembre",
            "10": "octubre", "11": "noviembre", "12": "diciembre"
        }
        return f"{int(dia)} de {meses.get(mes, '')} del {anio}"
    except:
        return str(fecha_str)

def procesar_resolucion_contrato(data_dict: dict) -> io.BytesIO:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ruta_plantilla = os.path.join(base_dir, "plantillas", "plantilla_resolucion.docx")
    
    if not os.path.exists(ruta_plantilla):
        raise ValueError(f"No se encontró la plantilla en: {ruta_plantilla}")
    
    doc = DocxTemplate(ruta_plantilla)
    
    # 1. Normalizar todas las llaves que llegan desde el Excel
    context = {}
    for key, value in data_dict.items():
        clave_normalizada = normalizar_clave(key)
        context[clave_normalizada] = value
        
    # 2. Asegurar variables críticas (si vienen vacías o con otro nombre)
    context["decano"] = context.get("decano", "")
    
    if not context.get("dia_notificacion"):
        context["dia_notificacion"] = context.get("dia_resolucion", "")
        
    # 3. Aplicar formato de fechas
    if "fecha_inicio" in context:
        context["fecha_inicio"] = formatear_fecha_espanol(context["fecha_inicio"])
    if "fecha_fin" in context:
        context["fecha_fin"] = formatear_fecha_espanol(context["fecha_fin"])
        
    # 4. Renderizar
    doc.render(context)
    
    archivo_stream = io.BytesIO()
    doc.save(archivo_stream)
    archivo_stream.seek(0)
    
    return archivo_stream