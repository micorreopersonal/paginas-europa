"""
Etapa 1: Extraer imágenes individuales de cada programa de viaje desde un PDF de Europamundo.

Detecta el patrón visual "Fechas de Salida" (barra dorada) como separador entre programas.
Genera una imagen recortada por cada programa encontrado.

Uso:
    python etapa1_extraer_programas.py <ruta_pdf>
"""

import sys
import os
import fitz  # PyMuPDF
import numpy as np
from PIL import Image


# --- Configuración ---
DPI = 200  # Resolución para renderizar páginas
GOLD_THRESHOLD = 0.7  # % mínimo de píxeles dorados en una fila para considerarla "barra dorada"
MIN_GAP_BETWEEN_PROGRAMS = 300  # Píxeles mínimos entre barras doradas para considerarlas programas distintos
INDEX_PAGES = 2  # Número de páginas de índice al inicio del PDF (se omiten)


def is_gold_pixel(r, g, b):
    """Máscara para detectar el color dorado de la barra 'Fechas de Salida'."""
    return (r > 120) & (r < 200) & (g > 70) & (g < 150) & (b < 50)


def find_program_starts(img_array):
    """
    Encuentra las posiciones Y donde inicia cada programa en una página.
    Busca bandas horizontales doradas que cruzan la mayor parte del ancho.
    Retorna lista de posiciones Y donde inicia cada programa.
    """
    h, w, _ = img_array.shape
    gold_rows = []

    for y in range(h):
        row = img_array[y]
        mask = is_gold_pixel(row[:, 0], row[:, 1], row[:, 2])
        if mask.sum() / w > GOLD_THRESHOLD:
            gold_rows.append(y)

    if not gold_rows:
        return []

    # Agrupar filas doradas en bandas, separadas por gaps > MIN_GAP
    program_starts = [gold_rows[0]]
    for i in range(1, len(gold_rows)):
        if gold_rows[i] - gold_rows[i - 1] > MIN_GAP_BETWEEN_PROGRAMS:
            program_starts.append(gold_rows[i])

    return program_starts


def page_to_image(page, dpi=DPI):
    """Renderiza una página PDF como imagen PIL."""
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img


def extract_programs(pdf_path, output_dir):
    """
    Extrae cada programa del PDF como imagen individual.
    Retorna lista de (nombre_archivo, page_num, y_start, y_end).
    """
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    print(f"PDF: {os.path.basename(pdf_path)}")
    print(f"Total páginas: {total_pages}")
    print(f"Páginas de índice (omitidas): {INDEX_PAGES}")
    print(f"Procesando páginas {INDEX_PAGES + 1} a {total_pages}...")
    print("-" * 50)

    program_count = 0
    programs_info = []

    for page_num in range(INDEX_PAGES, total_pages):
        page = doc[page_num]
        img = page_to_image(page)
        arr = np.array(img)
        h, w, _ = arr.shape

        starts = find_program_starts(arr)

        if not starts:
            print(f"  Página {page_num + 1}: Sin programas detectados (posible página decorativa)")
            continue

        print(f"  Página {page_num + 1}: {len(starts)} programa(s) detectado(s)")

        for i, y_start in enumerate(starts):
            # El programa termina donde inicia el siguiente, o al final de la página
            if i + 1 < len(starts):
                y_end = starts[i + 1]
            else:
                y_end = h

            # Recortar la imagen del programa
            program_img = img.crop((0, y_start, w, y_end))

            # Nombrar archivo: programa_NNN_pagPP.png
            program_count += 1
            filename = f"programa_{program_count:03d}_pag{page_num + 1:02d}.png"
            filepath = os.path.join(output_dir, filename)
            program_img.save(filepath, optimize=True)

            programs_info.append({
                "filename": filename,
                "page": page_num + 1,
                "y_start": y_start,
                "y_end": y_end,
                "height": y_end - y_start,
            })

    doc.close()

    print("-" * 50)
    print(f"Total programas extraídos: {program_count}")
    print(f"Imágenes guardadas en: {output_dir}")

    return programs_info


def main():
    if len(sys.argv) < 2:
        print("Uso: python etapa1_extraer_programas.py <ruta_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: No se encontró el archivo: {pdf_path}")
        sys.exit(1)

    # Directorio de salida basado en el nombre del PDF
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), "output", pdf_name)

    programs = extract_programs(pdf_path, output_dir)

    # Resumen
    if programs:
        print("\nResumen:")
        for p in programs:
            print(f"  {p['filename']} - Página {p['page']} - Alto: {p['height']}px")


if __name__ == "__main__":
    main()
