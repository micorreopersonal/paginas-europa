"""
Pipeline Europamundo: PDF → Páginas WordPress publicadas.

Ejecuta las etapas en secuencia:
  1. Extraer imágenes de programas del PDF
  2. Extraer datos estructurados con LLM Vision (Claude/Gemini)
  3. Generar contenido SEO (keywords, intro, highlights)
  4. Obtener imágenes de portada desde Pexels
  5. Generar mapas interactivos (MapLibre + OSRM)
  6. Publicar circuitos en WordPress (CPT + taxonomías + Rank Math SEO)

Uso:
    python procesar_pdf.py <ruta_pdf> [opciones]

Opciones:
    --etapas 1,2,3,4,5,6   Etapas a ejecutar (default: 1,2,3,4,5)
    --test N                Solo procesar N programas
    --status draft          Estado WP: draft|publish (default: draft)

Ejemplos:
    python procesar_pdf.py input/catalogo.pdf                      # Etapas 1-5 (sin publicar)
    python procesar_pdf.py input/catalogo.pdf --etapas 1,2,3,4,5,6 # Completo con WordPress
    python procesar_pdf.py input/catalogo.pdf --etapas 6            # Solo publicar
    python procesar_pdf.py input/catalogo.pdf --test 3              # Solo 3 programas

Configuración (.env):
    ANTHROPIC_API_KEY   — API key Claude (si LLM_PROVIDER=claude)
    GOOGLE_API_KEY      — API key Gemini (si LLM_PROVIDER=gemini)
    LLM_PROVIDER        — "claude" o "gemini" (default: claude)
    PEXELS_API_KEY      — Para imágenes de portada
    MAPTILER_API_KEY    — Para mapas interactivos
    WP_URL              — URL WordPress (solo etapa 6)
    WP_USER             — Usuario WordPress (solo etapa 6)
    WP_APP_PASSWORD     — Application Password (solo etapa 6)
"""

import sys
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: No se encontró: {pdf_path}")
        sys.exit(1)

    # Parse opciones
    etapas = [1, 2, 3, 4, 5]
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
    output_base = os.path.join(os.path.dirname(pdf_path) or ".", "output", pdf_name)

    print("=" * 60)
    print("  EUROPAMUNDO PDF → WORDPRESS PIPELINE")
    print(f"  PDF: {pdf_name}")
    print(f"  Etapas: {etapas}")
    if test_count:
        print(f"  Test mode: {test_count} programas")
    print("=" * 60)

    start = time.time()

    # ── ETAPA 1: PDF → Imágenes ──────────────────────────────────
    if 1 in etapas:
        print("\n[1/6] Extrayendo programas del PDF...")
        from etapa1_extraer_programas import extract_programs
        extract_programs(pdf_path, output_base)

    # ── ETAPA 2: Imágenes → JSON (LLM Vision) ───────────────────
    if 2 in etapas:
        print("\n[2/6] Extrayendo datos con LLM Vision...")
        from etapa2_extraer_datos import process_programs
        process_programs(pdf_path, test_count)

    # ── ETAPA 3: Generar contenido SEO ───────────────────────────
    if 3 in etapas:
        print("\n[3/6] Generando contenido SEO...")
        from generate_seo import enrich_programs_with_seo
        json_path = os.path.join(output_base, "programas.json")
        enrich_programs_with_seo(json_path, test_count)

    # ── ETAPA 4: Obtener imágenes de Pexels ──────────────────────
    if 4 in etapas:
        print("\n[4/6] Obteniendo imágenes de Pexels...")
        from fetch_images import enrich_programs_with_images
        json_path = os.path.join(output_base, "programas.json")
        enrich_programs_with_images(json_path, test_count)

    # ── ETAPA 5: Generar mapas interactivos ──────────────────────
    if 5 in etapas:
        print("\n[5/6] Generando mapas interactivos...")
        import json
        from generate_map import generate_map_file
        json_path = os.path.join(output_base, "programas.json")
        with open(json_path, "r", encoding="utf-8") as f:
            programs = json.load(f)
        maps_dir = os.path.join(output_base, "maps")
        valid = [p for p in programs if "_error" not in p]
        if test_count:
            valid = valid[:test_count]
        for prog in valid:
            try:
                generate_map_file(prog, maps_dir)
            except Exception as e:
                print(f"    WARN {prog.get('id', '?')}: {e}")

    # ── ETAPA 6: Publicar en WordPress ───────────────────────────
    if 6 in etapas:
        print("\n[6/6] Publicando en WordPress...")
        from etapa4_publicar_wordpress import publish_programs
        publish_programs(pdf_path, wp_status)

    # ── Mover PDF a procesados ─────────────────────────────────
    import shutil
    input_dir = os.path.dirname(pdf_path) or "."
    procesados_dir = os.path.join(input_dir, "procesados")
    os.makedirs(procesados_dir, exist_ok=True)
    dest = os.path.join(procesados_dir, os.path.basename(pdf_path))
    if not os.path.exists(dest):
        shutil.move(pdf_path, dest)
        print(f"\n  PDF movido a: {dest}")

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  Completado en {elapsed:.1f}s")
    print(f"  Output: {output_base}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
