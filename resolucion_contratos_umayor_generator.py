import io
import os
import unicodedata
from docxtpl import DocxTemplate

def normalizar_clave(clave: str) -> str:
    # Quita acentos y pasa a minúsculas
    # Importante: "Año_Resolucion" se convertirá en "ano_resolucion"
    clave_limpia = ''.join((c for c in unicodedata.normalize('NFD', str(clave)) if unicodedata.category(c) != 'Mn'))
    return clave_limpia.lower().strip().replace(" ", "_")

def obtener_nombre_mes(mes_valor) -> str:
    """Convierte un número de mes (1, 01, "1") en el nombre del mes en español."""
    meses = {
        "1": "enero", "2": "febrero", "3": "marzo", "4": "abril",
        "5": "mayo", "6": "junio", "7": "julio", "8": "agosto",
        "9": "septiembre", "10": "octubre", "11": "noviembre", "12": "diciembre",
        "01": "enero", "02": "febrero", "03": "marzo", "04": "abril",
        "05": "mayo", "06": "junio", "07": "julio", "08": "agosto",
        "09": "septiembre"
    }
    mes_str = str(mes_valor).strip()
    return meses.get(mes_str, mes_str)

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
    ruta_plantilla = os.path.join(base_dir, "plantillas", "plantilla_resolucion_(2).docx")
    
    if not os.path.exists(ruta_plantilla):
        raise ValueError(f"No se encontró la plantilla en: {ruta_plantilla}")
    
    doc = DocxTemplate(ruta_plantilla)
    
    # 1. Normalizar todas las llaves que llegan desde el Excel
    context = {}
    for key, value in data_dict.items():
        clave_normalizada = normalizar_clave(key)
        context[clave_normalizada] = value
        
    # 2. Lógica específica para Mes de Resolución (Número a Texto)
    if "mes_resolucion" in context:
        context["mes_resolucion"] = obtener_nombre_mes(context["mes_resolucion"])
        
    # 3. Asegurar variables críticas
    context["decano"] = context.get("decano", "")
    context["cedula"] = context.get("cedula", "")
    context["total_horas"] = context.get("total_horas", "")
    context["dia_resolucion"] = context.get("dia_resolucion", "")
    context["anio_resolucion"] = context.get("anio_resolucion", "") # Nota: 'n' no 'ñ'
    
    # Si dia_notificacion no viene, hereda el dia de la resolución
    if not context.get("dia_notificacion"):
        context["dia_notificacion"] = context.get("dia_resolucion", "")
        
    # 4. Aplicar formato de fechas largas (si existen columnas de fecha completa)
    if "fecha_inicio" in context:
        context["fecha_inicio"] = formatear_fecha_espanol(context["fecha_inicio"])
    if "fecha_fin" in context:
        context["fecha_fin"] = formatear_fecha_espanol(context["fecha_fin"])
        
    # 5. Renderizar
    doc.render(context)
    
    archivo_stream = io.BytesIO()
    doc.save(archivo_stream)
    archivo_stream.seek(0)
    
    return archivo_stream