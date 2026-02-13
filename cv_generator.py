# cv_generator.py
import os
from docxtpl import DocxTemplate
import io

def crear_docx_cv(data):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # ACTUALIZACIÓN AQUÍ: Carpeta 'plantillas', archivo 'plantilla_cv.docx'
    template_path = os.path.join(base_dir, "plantillas", "plantilla_cv.docx")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"No encuentro la plantilla en: {template_path}")

    doc = DocxTemplate(template_path)
    doc.render(data)
    
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream