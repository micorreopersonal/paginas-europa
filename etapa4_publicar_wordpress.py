"""
Etapa 4: Publicar programas como páginas en WordPress vía REST API.

Lee el JSON de programas y los mapas extraídos, sube las imágenes
y crea páginas en WordPress como borrador.

Uso:
    python etapa4_publicar_wordpress.py <ruta_pdf> [--status draft|publish]

Requisitos:
    - Archivo .env con ANTHROPIC_API_KEY (no usado aquí pero parte del proyecto)
    - Archivo .env con WP_URL, WP_USER, WP_APP_PASSWORD
"""

import sys
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuración desde .env ---
WP_URL = os.getenv("WP_URL", "").rstrip("/")
WP_USER = os.getenv("WP_USER", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

# --- Labels para sección "incluye" ---
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


def build_page_content(program):
    """Genera HTML Gutenberg-compatible para el contenido de la página."""
    # Itinerario
    itinerary_parts = []
    for day in program.get("itinerario", []):
        desc = day.get("descripcion") or day.get("descripción") or ""
        ciudades = day.get("ciudades", "")
        dia_num = day.get("dia", "")
        dia_semana = day.get("dia_semana", "")

        itinerary_parts.append(
            f"<!-- wp:heading {{\"level\":3}} -->\n"
            f"<h3>Día {dia_num} ({dia_semana}) — {ciudades}</h3>\n"
            f"<!-- /wp:heading -->\n\n"
            f"<!-- wp:paragraph -->\n"
            f"<p>{desc}</p>\n"
            f"<!-- /wp:paragraph -->"
        )

    # Incluye
    include_items = []
    for key, label in INCLUDE_LABELS.items():
        value = program.get("incluye", {}).get(key)
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            if not value:
                continue
            value = "Incluido"
        include_items.append(f"<li><strong>{label}:</strong> {value}</li>")

    # Info resumen arriba
    precio = program.get("precio_desde", "")
    dias = program.get("dias", "")
    fechas = program.get("fechas_salida", "")
    prog_id = program.get("id", "")

    content = f"""<!-- wp:paragraph -->
<p><strong>Duración:</strong> {dias} días | <strong>Desde:</strong> {precio} | <strong>Salidas:</strong> {fechas} | <strong>Código:</strong> {prog_id}</p>
<!-- /wp:paragraph -->

<!-- wp:heading {{"level":2}} -->
<h2>Itinerario día a día</h2>
<!-- /wp:heading -->

{chr(10).join(itinerary_parts)}

<!-- wp:heading {{"level":2}} -->
<h2>El precio incluye</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>
{chr(10).join(include_items)}
</ul>
<!-- /wp:list -->
"""
    return content


def upload_map(map_path, title, auth):
    """Sube imagen del mapa a WordPress y retorna el media ID."""
    with open(map_path, "rb") as img:
        filename = os.path.basename(map_path)
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            auth=auth,
            files={"file": (filename, img, "image/png")},
            data={"title": f"Mapa {title}", "alt_text": f"Mapa del itinerario - {title}"},
        )
    if r.status_code == 201:
        return r.json()["id"]
    else:
        print(f"    ERROR subiendo mapa: {r.status_code} {r.text[:150]}")
        return None


def create_page(title, content, media_id, status, auth):
    """Crea una página en WordPress y retorna la respuesta."""
    page_data = {
        "title": title,
        "content": content,
        "status": status,
        "featured_media": media_id or 0,
    }
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/pages", auth=auth, json=page_data)
    return r


def publish_programs(pdf_path, status="draft"):
    """Publica todos los programas como páginas en WordPress."""
    if not WP_URL or not WP_USER or not WP_APP_PASSWORD:
        print("Error: Configura WP_URL, WP_USER y WP_APP_PASSWORD en .env")
        sys.exit(1)

    auth = (WP_USER, WP_APP_PASSWORD)

    # Verificar conexión
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/users/me", auth=auth)
    if r.status_code != 200:
        print(f"Error de autenticación: {r.status_code}")
        sys.exit(1)
    print(f"Conectado a {WP_URL} como '{r.json().get('name')}'")

    # Localizar archivos
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_base = os.path.join(os.path.dirname(pdf_path), "output", pdf_name)
    json_path = os.path.join(output_base, "programas.json")
    maps_dir = os.path.join(output_base, "html", "assets")

    if not os.path.exists(json_path):
        print(f"Error: No se encontró {json_path}")
        print("Ejecuta primero las Etapas 1-3.")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        programs = json.load(f)

    valid = [p for p in programs if "_error" not in p]
    print(f"Publicando {len(valid)} páginas como '{status}'...")
    print("-" * 50)

    results = []
    for i, prog in enumerate(valid):
        prog_id = prog["id"]
        titulo = prog.get("titulo", "Sin título")
        print(f"  [{i+1}/{len(valid)}] {titulo}...", end=" ", flush=True)

        # Subir mapa
        map_path = os.path.join(maps_dir, f"mapa_{prog_id}.png")
        media_id = None
        if os.path.exists(map_path):
            media_id = upload_map(map_path, titulo, auth)

        # Generar contenido y crear página
        content = build_page_content(prog)
        r = create_page(titulo, content, media_id, status, auth)

        if r.status_code == 201:
            page = r.json()
            print(f"OK (page_id={page['id']})")
            results.append({"id": prog_id, "page_id": page["id"], "link": page["link"]})
        else:
            print(f"ERROR {r.status_code}")
            results.append({"id": prog_id, "error": r.text[:150]})

    # Guardar log
    log_path = os.path.join(output_base, "wordpress_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("-" * 50)
    ok = len([r for r in results if "page_id" in r])
    print(f"Páginas creadas: {ok}/{len(valid)}")
    print(f"Log guardado en: {log_path}")
    print(f"Revisa en: {WP_URL}/wp-admin/edit.php?post_type=page")


def main():
    if len(sys.argv) < 2:
        print("Uso: python etapa4_publicar_wordpress.py <ruta_pdf> [--status draft|publish]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    status = "draft"

    if "--status" in sys.argv:
        idx = sys.argv.index("--status")
        status = sys.argv[idx + 1]

    if not os.path.exists(pdf_path):
        print(f"Error: No se encontró: {pdf_path}")
        sys.exit(1)

    publish_programs(pdf_path, status)


if __name__ == "__main__":
    main()
