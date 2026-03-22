"""
Etapa 3: Generar páginas HTML individuales por cada programa de viaje.

Lee el JSON generado en Etapa 2, extrae los mapas de itinerario
directamente del PDF (alta calidad), y genera un archivo HTML por programa
con estilos basados en paqueteseuropa.com.

Uso:
    python etapa3_generar_html.py <ruta_pdf>
"""

import sys
import os
import re
import json
import fitz  # PyMuPDF

# --- Configuración ---
MIN_MAP_SIZE = 200  # Mínimo px en ancho/alto para considerar una imagen como mapa (excluir logos/iconos)
INDEX_PAGES = 2


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo} - Europamundo</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --color-primary: #398ffc;
            --color-primary-hover: rgb(95, 181, 255);
            --color-text: #3b3d42;
            --color-text-light: #a1a2a4;
            --color-white: #ffffff;
            --color-bg-light: #f7f8fa;
            --color-gold: #9f6e00;
            --color-gold-light: #f5eed9;
            --shadow-natural: 6px 6px 9px rgba(0, 0, 0, 0.2);
            --shadow-soft: 0 2px 12px rgba(0, 0, 0, 0.08);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Roboto', sans-serif;
            font-size: 14px;
            font-weight: 300;
            line-height: 1.6;
            color: var(--color-text);
            background-color: var(--color-bg-light);
        }}

        .container {{
            max-width: 960px;
            margin: 0 auto;
            padding: 0 1rem;
        }}

        /* --- HERO --- */
        .hero {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: var(--color-white);
            padding: 3rem 0 2rem;
            position: relative;
            overflow: hidden;
        }}

        .hero::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="0.5"/></svg>') repeat;
            opacity: 0.5;
        }}

        .hero-content {{
            position: relative;
            z-index: 1;
            display: flex;
            gap: 2rem;
            align-items: flex-start;
        }}

        .hero-info {{
            flex: 1;
        }}

        .hero-badge {{
            display: inline-block;
            background: var(--color-primary);
            color: var(--color-white);
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            padding: 4px 12px;
            border-radius: 3px;
            margin-bottom: 1rem;
            text-transform: uppercase;
        }}

        .hero h1 {{
            font-size: 2.5rem;
            font-weight: 400;
            line-height: 1.2;
            margin-bottom: 1.5rem;
        }}

        .hero-meta {{
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        }}

        .hero-meta-item {{
            display: flex;
            flex-direction: column;
        }}

        .hero-meta-label {{
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.6);
        }}

        .hero-meta-value {{
            font-size: 1.25rem;
            font-weight: 400;
        }}

        .hero-meta-value.price {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--color-primary-hover);
        }}

        .hero-map {{
            flex: 0 0 280px;
        }}

        .hero-map img {{
            width: 100%;
            border-radius: 8px;
            box-shadow: var(--shadow-natural);
        }}

        /* --- SECCIONES --- */
        .section {{
            background: var(--color-white);
            margin: 1.5rem 0;
            border-radius: 8px;
            box-shadow: var(--shadow-soft);
            overflow: hidden;
        }}

        .section-header {{
            background: var(--color-primary);
            color: var(--color-white);
            padding: 0.75rem 1.5rem;
            font-size: 18px;
            font-weight: 500;
        }}

        .section-body {{
            padding: 1.5rem;
        }}

        /* --- ITINERARIO --- */
        .itinerary-day {{
            display: flex;
            gap: 1rem;
            padding: 1rem 0;
            border-bottom: 1px solid #eee;
        }}

        .itinerary-day:last-child {{
            border-bottom: none;
        }}

        .day-number {{
            flex: 0 0 56px;
            height: 56px;
            background: var(--color-primary);
            color: var(--color-white);
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }}

        .day-number-label {{
            font-size: 10px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .day-number-num {{
            font-size: 22px;
            font-weight: 700;
        }}

        .day-content {{
            flex: 1;
        }}

        .day-cities {{
            font-weight: 500;
            font-size: 16px;
            color: var(--color-text);
            margin-bottom: 0.25rem;
        }}

        .day-weekday {{
            display: inline-block;
            background: var(--color-bg-light);
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 3px;
            color: var(--color-text-light);
            margin-left: 0.5rem;
            text-transform: uppercase;
        }}

        .day-description {{
            color: #555;
            margin-top: 0.25rem;
        }}

        /* --- INCLUYE --- */
        .includes-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }}

        .include-item {{
            display: flex;
            gap: 0.75rem;
            padding: 0.75rem;
            background: var(--color-bg-light);
            border-radius: 6px;
            align-items: flex-start;
        }}

        .include-icon {{
            flex: 0 0 36px;
            height: 36px;
            background: var(--color-primary);
            color: var(--color-white);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }}

        .include-label {{
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--color-primary);
            margin-bottom: 2px;
        }}

        .include-value {{
            font-size: 13px;
            color: #555;
        }}

        /* --- FOOTER --- */
        .page-footer {{
            text-align: center;
            padding: 2rem;
            color: var(--color-text-light);
            font-size: 12px;
        }}

        /* --- RESPONSIVE --- */
        @media (max-width: 767px) {{
            .hero h1 {{
                font-size: 1.75rem;
            }}

            .hero-content {{
                flex-direction: column-reverse;
            }}

            .hero-map {{
                flex: none;
                width: 100%;
                max-width: 280px;
                margin: 0 auto;
            }}

            .includes-grid {{
                grid-template-columns: 1fr;
            }}

            .hero-meta-value.price {{
                font-size: 1.5rem;
            }}
        }}
    </style>
</head>
<body>

    <!-- HERO -->
    <section class="hero">
        <div class="container">
            <div class="hero-content">
                <div class="hero-info">
                    <span class="hero-badge">Europamundo</span>
                    <h1>{titulo}</h1>
                    <div class="hero-meta">
                        <div class="hero-meta-item">
                            <span class="hero-meta-label">Duración</span>
                            <span class="hero-meta-value">{dias} días</span>
                        </div>
                        <div class="hero-meta-item">
                            <span class="hero-meta-label">Desde</span>
                            <span class="hero-meta-value price">{precio_desde}</span>
                        </div>
                        <div class="hero-meta-item">
                            <span class="hero-meta-label">Salidas</span>
                            <span class="hero-meta-value">{fechas_salida}</span>
                        </div>
                        <div class="hero-meta-item">
                            <span class="hero-meta-label">Código</span>
                            <span class="hero-meta-value">{id}</span>
                        </div>
                    </div>
                </div>
                {mapa_html}
            </div>
        </div>
    </section>

    <div class="container">

        <!-- ITINERARIO -->
        <div class="section">
            <div class="section-header">Itinerario día a día</div>
            <div class="section-body">
                {itinerario_html}
            </div>
        </div>

        <!-- INCLUYE -->
        <div class="section">
            <div class="section-header">El precio incluye</div>
            <div class="section-body">
                <div class="includes-grid">
                    {incluye_html}
                </div>
            </div>
        </div>

    </div>

    <div class="page-footer">
        Programa {id} &mdash; Europamundo Vacaciones &mdash; Generado automáticamente
    </div>

</body>
</html>
"""

# Iconos SVG inline para la sección "incluye"
INCLUDE_ICONS = {
    "servicios_generales": "&#9733;",   # estrella
    "traslado_llegada": "&#10148;",     # flecha
    "traslado_salida": "&#10148;",      # flecha
    "visitas_panoramicas": "&#9673;",   # ojo
    "excursiones": "&#9992;",           # avión (aventura)
    "entradas": "&#127915;",            # ticket
    "traslado_nocturno": "&#9790;",     # luna
    "barco": "&#9973;",                 # ancla
    "vuelos_incluidos": "&#9992;",      # avión
    "almuerzos": "&#127860;",           # tenedor
    "cenas": "&#127860;",              # tenedor
    "otros": "&#10010;",               # más
}

INCLUDE_LABELS = {
    "servicios_generales": "Servicios Generales",
    "traslado_llegada": "Traslado de Llegada",
    "traslado_salida": "Traslado de Salida",
    "visitas_panoramicas": "Visitas Panorámicas",
    "excursiones": "Excursiones",
    "entradas": "Entradas",
    "traslado_nocturno": "Traslado Nocturno",
    "barco": "Barco",
    "vuelos_incluidos": "Vuelos Incluidos",
    "almuerzos": "Almuerzos",
    "cenas": "Cenas",
    "otros": "Otros Servicios",
}


def extract_maps_from_pdf(pdf_path):
    """
    Extrae las imágenes de mapas del PDF renderizando solo la zona visible
    de cada imagen (el PDF puede almacenar imágenes más grandes y recortarlas).
    Retorna dict: {(page_1based, position_index): png_bytes}
    """
    doc = fitz.open(pdf_path)
    maps = {}

    for page_num in range(INDEX_PAGES, doc.page_count):
        page = doc[page_num]
        page_height = page.rect.height
        text = page.get_text()
        prog_ids = re.findall(r"ID:(\d+)", text)
        num_programs = len(prog_ids)

        # Recolectar imágenes candidatas a mapa (filtrar por tamaño)
        map_candidates = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            base_image = doc.extract_image(xref)
            w, h = base_image["width"], base_image["height"]

            if w < MIN_MAP_SIZE or h < MIN_MAP_SIZE:
                continue

            rects = page.get_image_rects(xref)
            if not rects:
                continue

            # Renderizar solo la zona visible del mapa a 200 DPI
            clip = fitz.Rect(rects[0])
            pix = page.get_pixmap(dpi=200, clip=clip)
            png_bytes = pix.tobytes("png")

            y_pos = rects[0].y0
            area = clip.width * clip.height  # Área visible, no la imagen original
            map_candidates.append((y_pos, area, png_bytes))

        # Ordenar por posición Y
        map_candidates.sort(key=lambda x: x[0])

        if num_programs == 1:
            if map_candidates:
                best = max(map_candidates, key=lambda x: x[1])
                maps[(page_num + 1, 0)] = best[2]
        elif num_programs >= 2 and len(map_candidates) >= 2:
            mid_y = page_height / num_programs
            for mc in map_candidates:
                y_pos = mc[0]
                prog_index = min(int(y_pos / mid_y), num_programs - 1)
                key = (page_num + 1, prog_index)
                if key not in maps or mc[1] > 0:
                    maps[key] = mc[2]
        elif num_programs >= 2 and len(map_candidates) == 1:
            maps[(page_num + 1, 0)] = map_candidates[0][2]

    doc.close()
    return maps


def build_itinerary_html(itinerario):
    """Genera el HTML del itinerario día a día."""
    html_parts = []
    for day in itinerario:
        desc = day.get("descripcion") or day.get("descripción") or ""
        ciudades = day.get("ciudades", "")
        dia_semana = day.get("dia_semana", "")
        dia_num = day.get("dia", "")

        html_parts.append(f"""
                <div class="itinerary-day">
                    <div class="day-number">
                        <span class="day-number-label">Día</span>
                        <span class="day-number-num">{dia_num}</span>
                    </div>
                    <div class="day-content">
                        <div class="day-cities">
                            {ciudades}
                            <span class="day-weekday">{dia_semana}</span>
                        </div>
                        <div class="day-description">{desc}</div>
                    </div>
                </div>""")

    return "\n".join(html_parts)


def build_includes_html(incluye):
    """Genera el HTML de la sección 'incluye'."""
    html_parts = []
    for key, label in INCLUDE_LABELS.items():
        value = incluye.get(key)
        if value is None or value == "":
            continue

        # Para booleanos
        if isinstance(value, bool):
            if not value:
                continue
            value = "Incluido"

        icon = INCLUDE_ICONS.get(key, "&#10003;")

        html_parts.append(f"""
                    <div class="include-item">
                        <div class="include-icon">{icon}</div>
                        <div>
                            <div class="include-label">{label}</div>
                            <div class="include-value">{value}</div>
                        </div>
                    </div>""")

    return "\n".join(html_parts)


def generate_html(program, output_dir, map_image_data=None):
    """Genera el archivo HTML para un programa."""
    prog_id = program["id"]

    # Crear directorio de assets
    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Guardar mapa si existe
    mapa_html = ""
    if map_image_data:
        map_filename = f"mapa_{prog_id}.png"
        map_path = os.path.join(assets_dir, map_filename)
        with open(map_path, "wb") as f:
            f.write(map_image_data)
        mapa_html = f"""<div class="hero-map">
                    <img src="assets/{map_filename}" alt="Mapa del itinerario">
                </div>"""

    # Generar secciones
    itinerario_html = build_itinerary_html(program.get("itinerario", []))
    incluye_html = build_includes_html(program.get("incluye", {}))

    # Rellenar template
    html = HTML_TEMPLATE.format(
        titulo=program.get("titulo", "Sin título"),
        dias=program.get("dias", ""),
        precio_desde=program.get("precio_desde", ""),
        fechas_salida=program.get("fechas_salida", ""),
        id=prog_id,
        mapa_html=mapa_html,
        itinerario_html=itinerario_html,
        incluye_html=incluye_html,
    )

    # Guardar HTML
    html_filename = f"{prog_id}_{sanitize_filename(program.get('titulo', prog_id))}.html"
    html_path = os.path.join(output_dir, html_filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return html_filename


def sanitize_filename(name):
    """Limpia un string para usarlo como nombre de archivo."""
    import re
    name = name.lower().strip()
    name = re.sub(r"[áà]", "a", name)
    name = re.sub(r"[éè]", "e", name)
    name = re.sub(r"[íì]", "i", name)
    name = re.sub(r"[óò]", "o", name)
    name = re.sub(r"[úù]", "u", name)
    name = re.sub(r"[ñ]", "n", name)
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = name.strip("-")
    return name[:60]


def main():
    if len(sys.argv) < 2:
        print("Uso: python etapa3_generar_html.py <ruta_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"Error: No se encontró el archivo: {pdf_path}")
        sys.exit(1)

    # Directorio de output (mismo que etapa 1 y 2)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_base = os.path.join(os.path.dirname(pdf_path), "output", pdf_name)
    json_path = os.path.join(output_base, "programas.json")

    if not os.path.exists(json_path):
        print(f"Error: No se encontró {json_path}")
        print("Ejecuta primero la Etapa 2.")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        programs = json.load(f)

    # Extraer mapas del PDF
    print("Extrayendo mapas del PDF...")
    maps = extract_maps_from_pdf(pdf_path)
    print(f"  {len(maps)} mapas extraídos")

    # Crear mapa de imagen_fuente -> (page, position) para buscar el mapa correcto
    # Agrupar programas por página para determinar posición
    page_program_counts = {}
    for program in programs:
        source = program.get("_source_image", "")
        match = re.search(r"pag(\d+)", source)
        if match:
            page = int(match.group(1))
            if page not in page_program_counts:
                page_program_counts[page] = []
            page_program_counts[page].append(program)

    # Directorio para HTMLs
    html_dir = os.path.join(output_base, "html")
    os.makedirs(html_dir, exist_ok=True)

    print(f"Generando {len(programs)} páginas HTML...")
    print("-" * 50)

    for page_num, page_programs in page_program_counts.items():
        for pos, program in enumerate(page_programs):
            if "_error" in program:
                print(f"  SKIP (error): {program.get('_source_image')}")
                continue

            map_data = maps.get((page_num, pos))
            filename = generate_html(program, html_dir, map_data)
            has_map = "con mapa" if map_data else "sin mapa"
            print(f"  {filename} ({has_map})")

    print("-" * 50)
    print(f"Páginas generadas en: {html_dir}")


if __name__ == "__main__":
    main()
