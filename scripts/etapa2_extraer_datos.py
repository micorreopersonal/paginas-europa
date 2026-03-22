"""
Etapa 2: Extraer datos estructurados de cada programa usando Claude Vision API.

Envía cada imagen de programa a Claude Sonnet para obtener un JSON con:
ID, título, itinerario, fechas de salida, precio desde, número de días,
mapa del itinerario (recorte), y condiciones incluidas.

Los IDs se extraen directamente del texto del PDF (más confiable que leer
texto rotado verticalmente desde la imagen).

Uso:
    python etapa2_extraer_datos.py <ruta_pdf> [--test N]

    --test N : Procesa solo las primeras N imágenes (para pruebas)
"""

import sys
import os
import re
import json
import base64
import glob
import time
import fitz  # PyMuPDF
from dotenv import load_dotenv

load_dotenv()

# --- Configuración ---
MAX_TOKENS = 4096

EXTRACTION_PROMPT = """Analiza esta imagen de un programa de viaje de Europamundo y extrae la información en formato JSON.

IMPORTANTE: Responde ÚNICAMENTE con el JSON, sin markdown, sin ```json, sin texto adicional.

Estructura requerida:
{
  "titulo": "nombre del programa de viaje",
  "dias": número de días (entero),
  "precio_desde": "precio en formato original (ej: 1.600 $)",
  "fechas_salida": "texto completo de fechas de salida (ej: Viernes todo el año)",
  "itinerario": [
    {
      "dia": "01",
      "dia_semana": "abreviatura del día (ej: VIE)",
      "ciudades": "ciudades del día",
      "descripcion": "descripción completa de las actividades del día"
    }
  ],
  "incluye": {
    "servicios_generales": "descripción de servicios generales",
    "traslado_llegada": true/false,
    "traslado_salida": true/false,
    "visitas_panoramicas": "ciudades con visita panorámica",
    "excursiones": "descripción de excursiones incluidas",
    "entradas": "lista de entradas incluidas",
    "traslado_nocturno": "descripción si aplica o null",
    "barco": "descripción si aplica o null",
    "vuelos_incluidos": "descripción si aplica o null",
    "almuerzos": "cantidad y ciudades",
    "cenas": "cantidad y ciudades",
    "otros": "cualquier otro servicio incluido no categorizado arriba"
  }
}

Notas:
- NO intentes leer el ID del borde izquierdo (está rotado y es difícil de leer). El ID se proporcionará por separado.
- Lee TODA la información del itinerario día por día.
- En "incluye", captura TODOS los servicios mencionados en la sección "El precio incluye".
- Si algún campo no aplica o no está presente, usa null.
"""


def extract_ids_from_pdf(pdf_path, index_pages=2):
    """
    Extrae los IDs de cada programa directamente del texto del PDF.
    Retorna un dict: {(page_num, position_index): id}
    donde page_num es 1-based y position_index es 0-based dentro de la página.
    """
    doc = fitz.open(pdf_path)
    page_ids = {}

    for page_num in range(index_pages, doc.page_count):
        text = doc[page_num].get_text()
        ids = re.findall(r"ID:(\d+)", text)
        for pos, prog_id in enumerate(ids):
            page_ids[(page_num + 1, pos)] = prog_id  # page_num + 1 para 1-based

    doc.close()
    return page_ids


def match_image_to_id(filename, page_ids):
    """
    Dado un nombre de archivo como 'programa_001_pag03.png',
    determina el ID correspondiente usando la info del PDF.
    """
    # Extraer número de página del nombre de archivo
    match = re.search(r"pag(\d+)", filename)
    if not match:
        return None

    page_num = int(match.group(1))

    # Contar cuántas imágenes hay de esta misma página para determinar posición
    # Esto se maneja externamente pasando el índice correcto
    return page_ids.get((page_num, 0))


def extract_program_data(image_path):
    """Envía imagen a LLM Vision y extrae datos estructurados."""
    from llm_client import llm_vision, get_provider_info

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    response_text, usage = llm_vision(image_bytes, EXTRACTION_PROMPT, "image/png", MAX_TOKENS)

    # Limpiar posible markdown wrapping
    clean = response_text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]
        clean = clean.rsplit("```", 1)[0]

    data = json.loads(clean)
    return data, usage


def process_programs(pdf_path, test_count=None):
    """Procesa todas las imágenes de programa extraídas de un PDF."""
    from llm_client import get_provider_info
    info = get_provider_info()
    print(f"Usando: {info['provider']} ({info['model']})")

    # Directorio de imágenes (mismo que usa etapa 1)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    input_dir = os.path.join(os.path.dirname(pdf_path), "output", pdf_name)

    # Buscar imágenes de programa
    images = sorted(glob.glob(os.path.join(input_dir, "programa_*.png")))
    if not images:
        print(f"No se encontraron imágenes en: {input_dir}")
        print("Ejecuta primero: python etapa1_extraer_programas.py <pdf>")
        return

    # Extraer IDs del PDF
    print("Extrayendo IDs del PDF...")
    page_ids = extract_ids_from_pdf(pdf_path)
    print(f"  {len(page_ids)} IDs encontrados en el PDF")

    # Crear mapa de imagen -> ID basado en página y posición
    # Agrupar imágenes por página para determinar posición
    page_groups = {}
    for img_path in images:
        filename = os.path.basename(img_path)
        match = re.search(r"pag(\d+)", filename)
        if match:
            page_num = int(match.group(1))
            if page_num not in page_groups:
                page_groups[page_num] = []
            page_groups[page_num].append(img_path)

    # Mapear cada imagen a su ID
    image_id_map = {}
    for page_num, page_images in page_groups.items():
        for pos, img_path in enumerate(sorted(page_images)):
            prog_id = page_ids.get((page_num, pos))
            if prog_id:
                image_id_map[img_path] = prog_id

    if test_count:
        images = images[:test_count]

    print(f"Procesando {len(images)} imágenes con Claude Vision...")
    print("-" * 50)

    results = []
    total_input_tokens = 0
    total_output_tokens = 0

    for i, img_path in enumerate(images):
        filename = os.path.basename(img_path)
        prog_id = image_id_map.get(img_path, "desconocido")
        print(f"  [{i+1}/{len(images)}] {filename} (ID:{prog_id})...", end=" ", flush=True)

        try:
            data, usage = extract_program_data(img_path)
            total_input_tokens += usage["input_tokens"]
            total_output_tokens += usage["output_tokens"]

            # Inyectar ID correcto del PDF y metadata
            data["id"] = prog_id
            data["_source_image"] = filename
            results.append(data)

            print(f"OK - {data.get('titulo', '?')} ({usage['input_tokens']}+{usage['output_tokens']} tokens)")

        except json.JSONDecodeError as e:
            print(f"ERROR JSON: {e}")
            results.append({"id": prog_id, "_source_image": filename, "_error": str(e)})
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({"id": prog_id, "_source_image": filename, "_error": str(e)})

        # Pausa breve para respetar rate limits
        if i < len(images) - 1:
            time.sleep(1)

    # Guardar resultados
    output_file = os.path.join(input_dir, "programas.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Resumen de costos
    # Sonnet: $3/M input, $15/M output
    cost_input = (total_input_tokens / 1_000_000) * 3
    cost_output = (total_output_tokens / 1_000_000) * 15
    cost_total = cost_input + cost_output

    print("-" * 50)
    print(f"Resultados guardados en: {output_file}")
    print(f"Programas procesados: {len([r for r in results if '_error' not in r])}/{len(images)}")
    print(f"\nConsumo de tokens:")
    print(f"  Input:  {total_input_tokens:,} tokens (${cost_input:.4f})")
    print(f"  Output: {total_output_tokens:,} tokens (${cost_output:.4f})")
    print(f"  TOTAL:  ${cost_total:.4f} USD")

    return results


def main():
    if len(sys.argv) < 2:
        print("Uso: python etapa2_extraer_datos.py <ruta_pdf> [--test N]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    test_count = None

    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        test_count = int(sys.argv[idx + 1])

    if not os.path.exists(pdf_path):
        print(f"Error: No se encontró el archivo: {pdf_path}")
        sys.exit(1)

    process_programs(pdf_path, test_count)


if __name__ == "__main__":
    main()
