from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
import os

# --- CONFIGURACIÓN DE COLORES ---
COLOR_FONDO_LATERAL = "2E4053" 
COLOR_TEXTO_LATERAL = RGBColor(255, 255, 255) 
COLOR_NOMBRE = RGBColor(46, 64, 83) 
COLOR_SUBTITULOS = RGBColor(46, 64, 83) 

def set_cell_background(cell, color_hex):
    shading_elm = parse_xml(r'<w:shd {} w:fill="{}"/>'.format(nsdecls('w'), color_hex))
    cell._tc.get_or_add_tcPr().append(shading_elm)

def crear_plantilla_final():
    doc = Document()
    
    # Márgenes
    for section in doc.sections:
        section.top_margin = Cm(1.27); section.bottom_margin = Cm(1.27)
        section.left_margin = Cm(1.27); section.right_margin = Cm(1.27)

    # Tabla Maestra
    table = doc.add_table(rows=1, cols=2)
    table.autofit = False
    table.columns[0].width = Inches(2.4)
    table.columns[1].width = Inches(5.0)

    # --- BARRA LATERAL ---
    cell_left = table.cell(0, 0)
    set_cell_background(cell_left, COLOR_FONDO_LATERAL)
    cell_left.vertical_alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    def add_sidebar(text, size=10, bold=False):
        p = cell_left.add_paragraph()
        run = p.add_run(text)
        run.font.name = 'Segoe UI'; run.font.size = Pt(size)
        run.font.color.rgb = COLOR_TEXTO_LATERAL; run.bold = bold
        p.paragraph_format.space_after = Pt(2)
        return p

    # FOTO
    p = add_sidebar("{{ foto }}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    add_sidebar("\nCONTACTO", size=12, bold=True)
    add_sidebar("{{ personal.email }}")
    add_sidebar("{{ personal.telefono }}")
    add_sidebar("{{ personal.direccion }}")

    add_sidebar("\nINFORMACIÓN", size=12, bold=True)
    add_sidebar("CC: {{ personal.cedula }}")
    add_sidebar("Edad: {{ personal.edad }}")
    add_sidebar("Estado: {{ personal.estadoCivil }}")

    # COMPETENCIAS (Usamos sintaxis estándar para evitar error 'endfor')
    add_sidebar("\nCOMPETENCIAS", size=12, bold=True)
    add_sidebar("{% for skill in skills %}") # <--- CAMBIO AQUÍ
    add_sidebar("• {{ skill }}")
    add_sidebar("{% endfor %}")              # <--- CAMBIO AQUÍ

    # DIPLOMAS
    add_sidebar("\nDIPLOMAS", size=12, bold=True)
    add_sidebar("{% for item in diplomas %}")
    add_sidebar("🏆 {{ item }}")
    add_sidebar("{% endfor %}")

    # --- CONTENIDO PRINCIPAL ---
    cell_right = table.cell(0, 1)
    
    # Nombre
    p = cell_right.add_paragraph()
    run = p.add_run("{{ personal.nombre }}")
    run.font.size = Pt(26); run.bold = True; run.font.color.rgb = COLOR_NOMBRE
    
    cell_right.add_paragraph("{{ personal.perfil }}")

    # Experiencia
    p = cell_right.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    run = p.add_run("EXPERIENCIA LABORAL")
    run.font.size = Pt(12); run.bold = True; run.font.color.rgb = COLOR_SUBTITULOS

    cell_right.add_paragraph("{% for item in experiencia %}") # <--- CAMBIO AQUÍ
    
    p = cell_right.add_paragraph()
    p.add_run("{{ item.cargo }}").bold = True
    p.add_run(" | {{ item.empresa }}").italic = True
    
    cell_right.add_paragraph("{{ item.fecha }}")
    cell_right.add_paragraph("{{ item.descripcion }}")
    cell_right.add_paragraph("") # Espacio
    cell_right.add_paragraph("{% endfor %}")

    # Formación
    p = cell_right.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    run = p.add_run("FORMACIÓN ACADÉMICA")
    run.font.size = Pt(12); run.bold = True; run.font.color.rgb = COLOR_SUBTITULOS
    
    cell_right.add_paragraph("{% for item in formacion %}")
    cell_right.add_paragraph("🎓 {{ item.titulo }}")
    cell_right.add_paragraph("{{ item.institucion }} - {{ item.fecha }}")
    cell_right.add_paragraph("{% endfor %}")

    if not os.path.exists("plantillas"): os.makedirs("plantillas")
    doc.save("plantillas/plantilla_cv.docx")
    print("✅ Plantilla reparada guardada en: plantillas/plantilla_cv.docx")

if __name__ == "__main__":
    crear_plantilla_final()