"""
Pipeline completo: Procesar un PDF de Europamundo y publicar en WordPress.

Ejecuta las 4 etapas en secuencia:
  1. Extraer imágenes de programas del PDF
  2. Extraer datos estructurados con Claude Vision API
  3. Generar HTML local + mapas
  4. Publicar páginas en WordPress (opcional)

Uso:
    python procesar_pdf.py <ruta_pdf> [opciones]

Opciones:
    --etapas 1,2,3,4    Etapas a ejecutar (default: 1,2,3)
    --test N             Solo procesar N programas en etapa 2
    --status draft       Estado de publicación WP (draft|publish)

Ejemplos:
    python procesar_pdf.py catalogo.pdf                    # Etapas 1-3
    python procesar_pdf.py catalogo.pdf --etapas 1,2,3,4   # Completo con WordPress
    python procesar_pdf.py catalogo.pdf --etapas 2 --test 3 # Solo etapa 2, 3 programas
    python procesar_pdf.py catalogo.pdf --etapas 4          # Solo publicar a WordPress

Requisitos:
    pip install PyMuPDF Pillow anthropic python-dotenv requests

Configuración (.env):
    ANTHROPIC_API_KEY=sk-ant-...
    WP_URL=https://tusitio.com        (solo para etapa 4)
    WP_USER=usuario                    (solo para etapa 4)
    WP_APP_PASSWORD=xxxx xxxx xxxx    (solo para etapa 4)
"""

import sys
import os
import time

# Asegurar que el directorio del script está en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: No se encontró: {pdf_path}")
        sys.exit(1)

    # Parse opciones
    etapas = [1, 2, 3]
    test_count = None
    wp_status = "draft"

    if "--etapas" in sys.argv:
        idx = sys.argv.index("--etapas")
        etapas = [int(e) for e in sys.argv[idx + 1].split(",")]

    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        test_count = int(sys.argv[idx + 1])

    if "--status" in sys.argv:
        idx = sys.argv.index("--status")
        wp_status = sys.argv[idx + 1]

    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print("=" * 60)
    print(f"  EUROPAMUNDO PDF PROCESSOR")
    print(f"  PDF: {pdf_name}")
    print(f"  Etapas: {etapas}")
    print("=" * 60)

    start = time.time()

    # --- ETAPA 1 ---
    if 1 in etapas:
        print("\n[ETAPA 1] Extrayendo programas del PDF...")
        from etapa1_extraer_programas import extract_programs
        output_dir = os.path.join(os.path.dirname(pdf_path), "output", pdf_name)
        programs_info = extract_programs(pdf_path, output_dir)

    # --- ETAPA 2 ---
    if 2 in etapas:
        print("\n[ETAPA 2] Extrayendo datos con Claude Vision API...")
        from etapa2_extraer_datos import process_programs
        process_programs(pdf_path, test_count)

    # --- ETAPA 3 ---
    if 3 in etapas:
        print("\n[ETAPA 3] Generando HTML local + mapas...")
        from etapa3_generar_html import extract_maps_from_pdf, generate_html
        from etapa3_generar_html import sanitize_filename
        import json
        import re

        output_base = os.path.join(os.path.dirname(pdf_path), "output", pdf_name)
        json_path = os.path.join(output_base, "programas.json")

        with open(json_path, "r", encoding="utf-8") as f:
            programs = json.load(f)

        maps = extract_maps_from_pdf(pdf_path)
        print(f"  {len(maps)} mapas extraídos")

        # Agrupar por página
        page_groups = {}
        for prog in programs:
            source = prog.get("_source_image", "")
            match = re.search(r"pag(\d+)", source)
            if match:
                page = int(match.group(1))
                if page not in page_groups:
                    page_groups[page] = []
                page_groups[page].append(prog)

        html_dir = os.path.join(output_base, "html")
        os.makedirs(html_dir, exist_ok=True)

        count = 0
        for page_num, page_programs in page_groups.items():
            for pos, prog in enumerate(page_programs):
                if "_error" in prog:
                    continue
                map_data = maps.get((page_num, pos))
                generate_html(prog, html_dir, map_data)
                count += 1

        print(f"  {count} páginas HTML generadas en: {html_dir}")

    # --- ETAPA 4 ---
    if 4 in etapas:
        print("\n[ETAPA 4] Publicando en WordPress...")
        from etapa4_publicar_wordpress import publish_programs
        publish_programs(pdf_path, wp_status)

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  Completado en {elapsed:.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
