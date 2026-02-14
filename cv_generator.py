from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from PIL import Image  # <--- NUEVA LIBRERÍA
import io
import os

def crear_docx_cv(data, foto_bytes=None):
    # 1. Cargar Plantilla
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(base_dir, "plantillas", "plantilla_cv.docx")

    if not os.path.exists(template_path):
        raise FileNotFoundError(f"No encuentro la plantilla en: {template_path}")

    doc = DocxTemplate(template_path)
    
    # 2. Procesar Foto (LAVADO DE IMAGEN)
    if foto_bytes:
        print(f"🖼️ Procesando imagen de {len(foto_bytes)} bytes...")
        try:
            # A. Abrir la imagen desde los bytes crudos
            image_stream = io.BytesIO(foto_bytes)
            img = Image.open(image_stream)

            # B. Convertir a RGB (arregla problemas con PNGs transparentes o JPGs CMYK)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # C. Guardar la imagen limpia en un nuevo flujo de memoria
            img_clean_stream = io.BytesIO()
            img.save(img_clean_stream, format='JPEG', quality=90)
            img_clean_stream.seek(0) # Rebobinar el stream al principio

            # D. Insertar la imagen LIMPIA en el Word
            # Ajusta width=Mm(35) según el tamaño que desees en el círculo
            imagen_word = InlineImage(doc, img_clean_stream, width=Mm(35))
            
            data['foto'] = imagen_word
            print("✅ Imagen procesada e insertada correctamente.")

        except Exception as e:
            print(f"⚠️ Error insertando la imagen (se omitirá): {e}")
            data['foto'] = "" # Si falla, no rompemos el PDF, solo sale sin foto
    else:
        data['foto'] = ""

    # 3. Renderizar y Guardar
    doc.render(data)
    
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)
    
    return file_stream