from docxtpl import DocxTemplate
from io import BytesIO
from datetime import datetime
from pydantic import BaseModel
import locale

# Configuración regional
try:
    locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')
except:
    pass

# 1. Definimos el modelo aquí para compartirlo
class DatosContrato(BaseModel):
    proveedor: str
    nit: str
    num_contrato: str
    fecha_contrato: str
    objeto_contrato: str
    valor_contrato: float
    numero_cuota: int
    duracion_meses: int
    cert_disp_pres: str
    reg_pres: str
    cargo_supervisor: str
    periodo_inicio: str = ""
    periodo_fin: str = ""

# 2. Esta es la función que busca tu main.py
def procesar_recibo(data: DatosContrato) -> BytesIO:
    # --- CÁLCULOS MATEMÁTICOS ---
    if data.duracion_meses == 0:
        raise ValueError("La duración en meses no puede ser 0")

    # Valor mensual (lo que vale 1 mes)
    valor_mensual = data.valor_contrato / data.duracion_meses

    # Saldo Ejecutado (Acumulado hasta la fecha)
    saldo_ejecutado = valor_mensual * data.numero_cuota

    # Saldo Pendiente (Lo que falta)
    saldo_ejecutar = data.valor_contrato - saldo_ejecutado
    
    # Cuotas restantes
    cuotas_restantes_num = data.duracion_meses - data.numero_cuota

    # Texto del periodo
    if data.periodo_inicio and data.periodo_fin:
        periodo_txt = f"Del {data.periodo_inicio} al {data.periodo_fin}"
    else:
        periodo_txt = f"Correspondiente a la cuota No. {data.numero_cuota}"

    # --- CONTEXTO WORD ---
    context = {
        # Datos básicos
        'FECHA_PAGO': datetime.now().strftime("%d/%m/%Y"),
        'PROVEEDOR': data.proveedor,
        'NIT': data.nit,
        'NUM_CONTRATO': data.num_contrato,
        'FECHA_CONTRATO': data.fecha_contrato,
        'OBJETO_CONTRATO': data.objeto_contrato,
        'DURACION_INICIAL': f"{data.duracion_meses} Meses",
        'PERIODO_PAGO': periodo_txt,
        'CERT_DISP_PRES': data.cert_disp_pres,
        'REG_PRES': data.reg_pres,
        'CARGO_SUPERVISOR': data.cargo_supervisor,
        'VALOR_CONTRATO': f"${data.valor_contrato:,.0f}",
        'VALOR_TOTAL': f"${data.valor_contrato:,.0f}",

        # --- VARIABLES CLAVE DE DINERO ---
        
        # Úsala en el texto del párrafo ("...por valor de {{VALOR_MENSUAL}}")
        'VALOR_MENSUAL': f"${valor_mensual:,.0f}",
        
        # Úsala en la TABLA frente a "SALDO EJECUTADO"
        'SALDO_EJECUTADO': f"${saldo_ejecutado:,.0f}",
        
        # Úsala en la TABLA frente a "SALDO POR EJECUTAR"
        'SALDO_EJECUTAR': f"${saldo_ejecutar:,.0f}",
        
        # Mantenemos estas por compatibilidad (opcional)
        'CUOTA': f"${valor_mensual:,.0f}",  # Por si olvidaste cambiar el texto
        
        # --- VARIABLES DE CONTEO ---
        'NUMERO_CUOTA': data.numero_cuota,      # El número "5"
        'CUOTAS_RESTANTES': cuotas_restantes_num # El número "1"
    }

    # Renderizar
    # OJO: Verifica que esta ruta sea correcta
    doc = DocxTemplate("plantillas/plantilla.docx") 
    doc.render(context)

    stream = BytesIO()
    doc.save(stream)
    stream.seek(0)
    
    return stream