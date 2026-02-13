from docxtpl import DocxTemplate
import io
import os

def crear_docx_cv(data):
    # 1. Obtiene la ruta de la carpeta donde está ESTE archivo (cv_generator.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Une esa ruta con el nombre de tu plantilla
    template_path = os.path.join(base_dir, "plantillas/plantilla_cv.docx")
    
    print(f"Buscando plantilla en: {template_path}")  # Esto se imprimirá en tu terminal

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"¡ERROR CRÍTICO! No encuentro el archivo en: {template_path}")

    doc = DocxTemplate(template_path)
    
    # Renderizamos
    doc.render(data)
    
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream