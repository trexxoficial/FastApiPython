from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from docxtpl import DocxTemplate
from io import BytesIO
from fastapi.responses import StreamingResponse
from datetime import datetime
import locale

try:
    locale.setlocale(locale.LC_ALL, 'es_CO.UTF-8')
except:
    pass

app = FastAPI()

class DatosContrato(BaseModel):
    proveedor: str
    nit: str
    num_contrato: str
    fecha_contrato: str
    objeto_contrato: str
    valor_contrato: float
    numero_cuota: int       # Ejemplo: 5
    duracion_meses: int     # Ejemplo: 6
    cert_disp_pres: str
    reg_pres: str
    cargo_supervisor: str
    periodo_inicio: str = ""
    periodo_fin: str = ""

@app.post("/generar-recibo")
async def generar_recibo(data: DatosContrato):
    try:
        # --- LÓGICA MATEMÁTICA ---
        if data.duracion_meses == 0:
             raise HTTPException(status_code=400, detail="La duración no puede ser 0")

        # 1. VALOR MENSUAL (Lo que se paga en este recibo)
        # 30.000.000 / 6 = 5.000.000
        valor_mensual = data.valor_contrato / data.duracion_meses

        # 2. SALDO EJECUTADO (El acumulado hasta hoy)
        # 5.000.000 * 5 = 25.000.000
        valor_acumulado = valor_mensual * data.numero_cuota

        # 3. SALDO PENDIENTE (Lo que faltará después de este pago)
        # 30.000.000 - 25.000.000 = 5.000.000
        saldo_pendiente = data.valor_contrato - valor_acumulado
        
        # 4. CUOTAS RESTANTES (Número)
        # 6 - 5 = 1
        cuotas_restantes_num = data.duracion_meses - data.numero_cuota

        # --- TEXTO PERIODO ---
        if data.periodo_inicio and data.periodo_fin:
            periodo_txt = f"Del {data.periodo_inicio} al {data.periodo_fin}"
        else:
            periodo_txt = f"Correspondiente a la cuota No. {data.numero_cuota}"

        # --- VARIABLES PARA EL WORD ---
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
            'SALDO_EJECUTADO': f"${valor_acumulado:,.0f}",
            
            # Úsala en la TABLA frente a "SALDO POR EJECUTAR"
            'SALDO_PENDIENTE': f"${saldo_pendiente:,.0f}",
            
            # Mantenemos estas por compatibilidad (opcional)
            'CUOTA': f"${valor_mensual:,.0f}",  # Por si olvidaste cambiar el texto
            
            # --- VARIABLES DE CONTEO ---
            'NUMERO_CUOTA': data.numero_cuota,      # El número "5"
            'CUOTAS_RESTANTES': cuotas_restantes_num # El número "1"
        }

        doc = DocxTemplate("plantillas/plantilla.docx") 
        doc.render(context)

        stream = BytesIO()
        doc.save(stream)
        stream.seek(0)

        nombre_archivo = f"Recibo_{data.proveedor.replace(' ', '_')}_Cuota{data.numero_cuota}.docx"
        
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'}
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))