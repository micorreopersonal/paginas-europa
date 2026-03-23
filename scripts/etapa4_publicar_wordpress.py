"""
Etapa 4: Publicar programas como páginas en WordPress vía REST API.

Genera mapa interactivo (MapLibre) y lo embebe junto al itinerario
y servicios incluidos como contenido de la página.

Uso:
    python etapa4_publicar_wordpress.py <ruta_pdf> [--status draft|publish]

Requisitos (.env):
    WP_URL, WP_USER, WP_APP_PASSWORD
    MAPTILER_API_KEY (para el mapa interactivo)
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


def build_page_content(program, map_html=None):
    """Genera HTML Gutenberg-compatible para el contenido de la página."""
    # Itinerario — estilo similar a página hermana: día en bold, ciudad uppercase, descripción normal
    itinerary_parts = []
    for day in program.get("itinerario", []):
        desc = day.get("descripcion") or day.get("descripción") or ""
        ciudades = day.get("ciudades", "").upper()
        dia_num = day.get("dia", "")
        dia_semana = day.get("dia_semana", "")

        itinerary_parts.append(
            f"<!-- wp:paragraph -->\n"
            f"<p><strong>DÍA {dia_num}: {dia_semana} — {ciudades}</strong><br>"
            f"{desc}</p>\n"
            f"<!-- /wp:paragraph -->"
        )

    # Incluye — con checks verdes ✔ como la página hermana
    include_items = []
    for key, label in INCLUDE_LABELS.items():
        value = program.get("incluye", {}).get(key)
        if value is None or value == "":
            continue
        if isinstance(value, bool):
            if not value:
                continue
            value = "Incluido"
        include_items.append(f"<li>✔ <strong>{label}:</strong> {value}</li>")

    # Info resumen
    precio = program.get("precio_desde", "")
    dias = program.get("dias", "")
    fechas = program.get("fechas_salida", "")
    prog_id = program.get("id", "")

    # SEO content
    seo = program.get("seo", {})
    intro = seo.get("intro", "")
    highlights = seo.get("highlights", [])
    cta = seo.get("cta", "")
    heading_kw = seo.get("heading_keyword", "")
    titulo = program.get("titulo", "")

    # Construir contenido
    parts = []

    # Párrafo intro SEO (keyword al inicio del contenido)
    if intro:
        parts.append(f"""<!-- wp:paragraph -->
<p>{intro}</p>
<!-- /wp:paragraph -->""")

    # Mapa interactivo
    if map_html:
        parts.append(f"<!-- wp:html -->\n{map_html}\n<!-- /wp:html -->")

    # Resumen
    parts.append(f"""<!-- wp:paragraph -->
<p><strong>Duración:</strong> {dias} días | <strong>Desde:</strong> {precio} | <strong>Salidas:</strong> {fechas} | <strong>Código:</strong> {prog_id}</p>
<!-- /wp:paragraph -->""")

    # Highlights con heading que contiene keyword
    if highlights:
        h2_title = heading_kw if heading_kw else "Experiencias destacadas"
        highlight_items = "\n".join(f"<li>{h}</li>" for h in highlights)
        parts.append(f"""<!-- wp:heading {{"level":2}} -->
<h2>{h2_title}</h2>
<!-- /wp:heading -->

<!-- wp:list -->
<ul>
{highlight_items}
</ul>
<!-- /wp:list -->""")

    # Itinerario — heading con barra azul
    parts.append(f"""<!-- wp:html -->
<h2 style="background:#1a8fb5; color:white; padding:10px 20px; border-radius:4px; font-size:20px; margin-top:30px;">Itinerario</h2>
<!-- /wp:html -->

{chr(10).join(itinerary_parts)}""")

    # Incluye — heading con barra azul + checks verdes
    parts.append(f"""<!-- wp:html -->
<h2 style="background:#1a8fb5; color:white; padding:10px 20px; border-radius:4px; font-size:20px; margin-top:30px;">Incluye:</h2>
<!-- /wp:html -->

<!-- wp:list {{"className":"no-bullets"}} -->
<ul style="list-style:none; padding-left:10px;">
{chr(10).join(include_items)}
</ul>
<!-- /wp:list -->""")

    # CTA final + links internos y externos (SEO)
    if cta:
        parts.append(f"""<!-- wp:paragraph -->
<p><strong>{cta}</strong></p>
<!-- /wp:paragraph -->""")

    # Links para SEO (interno + externo dofollow)
    parts.append(f"""<!-- wp:paragraph -->
<p>Consulta todos nuestros <a href="https://paqueteseuropa.com/circuitos/">circuitos disponibles</a> o conoce más sobre el operador <a href="https://www.europamundo.com/" target="_blank" rel="dofollow">Europamundo Vacaciones</a>, líder mundial en circuitos turísticos con guía en español.</p>
<!-- /wp:paragraph -->""")

    return "\n\n".join(parts)


# Mapeo catálogo PDF → región WordPress
CATALOG_TO_REGION = {
    "usa-canada": "USA y Canadá",
    "mexico-cuba": "México y Cuba",
    "china-japon-y-corea": "China, Corea y Japón",
    "sudeste-india-y-oceania": "India y Oceanía",
    "oriente-medio-africa": "Oriente Medio y África",
    "peninsula": "Península Ibérica y Marruecos",
    "mediterranea": "Europa Mediterránea",
    "atlantica": "Europa Atlántica",
    "nordica": "Europa Nórdica",
    "central": "Europa Central",
    "mas-incluido": "Más Incluido",
    "turista": "Turista",
    "cruceros-fluviales": "Cruceros Fluviales",
}

CATALOG_TO_SERIE = {
    "mas-incluido": "Más Incluido",
    "turista": "Turista",
    "cruceros-fluviales": "Cruceros Fluviales",
}


def resolve_taxonomy_ids(pdf_name, auth):
    """Determina los IDs de región y serie a partir del nombre del PDF."""
    region_id = None
    serie_id = None

    # Buscar coincidencia en el nombre del PDF
    pdf_lower = pdf_name.lower()
    for key, region_name in CATALOG_TO_REGION.items():
        if key in pdf_lower:
            # Buscar ID de la región
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/region_europamundo",
                auth=auth, params={"search": region_name}
            )
            if r.status_code == 200 and r.json():
                region_id = r.json()[0]["id"]
            break

    # Serie: por defecto "Regular", override si es catálogo de serie
    for key, serie_name in CATALOG_TO_SERIE.items():
        if key in pdf_lower:
            r = requests.get(
                f"{WP_URL}/wp-json/wp/v2/serie_europamundo",
                auth=auth, params={"search": serie_name}
            )
            if r.status_code == 200 and r.json():
                serie_id = r.json()[0]["id"]
            break

    if not serie_id:
        # Default: Regular
        r = requests.get(
            f"{WP_URL}/wp-json/wp/v2/serie_europamundo",
            auth=auth, params={"search": "Regular"}
        )
        if r.status_code == 200 and r.json():
            serie_id = r.json()[0]["id"]

    return region_id, serie_id


def upload_image_from_url(image_url, title, auth, alt_text=None):
    """Descarga imagen desde URL y la sube a WordPress Media."""
    try:
        img_r = requests.get(image_url, timeout=15)
        img_r.raise_for_status()

        filename = f"{title[:50].replace(' ', '-').lower()}.jpg"
        r = requests.post(
            f"{WP_URL}/wp-json/wp/v2/media",
            auth=auth,
            files={"file": (filename, img_r.content, "image/jpeg")},
            data={"title": title, "alt_text": alt_text or title},
        )
        if r.status_code == 201:
            return r.json()["id"]
    except Exception as e:
        print(f"      [WARN] Upload imagen: {e}")
    return None


def create_circuito(title, content, status, auth, seo=None,
                    region_id=None, serie_id=None, program=None,
                    featured_media_id=None):
    """Crea un circuito en WordPress con taxonomías y meta SEO."""
    post_data = {
        "title": title,
        "content": content,
        "status": status,
    }

    # Featured image
    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    # Taxonomías
    if region_id:
        post_data["region_europamundo"] = [region_id]
    if serie_id:
        post_data["serie_europamundo"] = [serie_id]

    # Meta fields propios del circuito
    if program:
        post_data["meta"] = {
            "id_europamundo": program.get("id", ""),
            "precio_desde": program.get("precio_desde", ""),
            "dias": str(program.get("dias", "")),
            "fechas_salida": program.get("fechas_salida", ""),
        }

    # Crear el circuito
    r = requests.post(f"{WP_URL}/wp-json/wp/v2/circuito", auth=auth, json=post_data)

    if r.status_code != 201:
        return r

    post_id = r.json()["id"]

    # Setear meta SEO de Rank Math via endpoint custom
    if seo:
        seo_meta = {
            "rank_math_title": seo.get("seo_title", ""),
            "rank_math_description": seo.get("meta_description", ""),
            "rank_math_focus_keyword": seo.get("focus_keyword", ""),
            "rank_math_facebook_title": seo.get("og_title", seo.get("seo_title", "")),
            "rank_math_facebook_description": seo.get("og_description", seo.get("meta_description", "")),
            "rank_math_twitter_title": seo.get("og_title", seo.get("seo_title", "")),
            "rank_math_twitter_description": seo.get("og_description", seo.get("meta_description", "")),
        }
        requests.post(
            f"{WP_URL}/wp-json/europamundo/v1/seo/{post_id}",
            auth=auth, json=seo_meta
        )

    return r


def publish_programs(pdf_path, status="draft"):
    """Publica todos los programas como circuitos en WordPress."""
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
    from scripts import get_output_dir
    output_base = get_output_dir(pdf_path)
    json_path = os.path.join(output_base, "programas.json")

    if not os.path.exists(json_path):
        print(f"Error: No se encontró {json_path}")
        print("Ejecuta primero las Etapas 1-2.")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        programs = json.load(f)

    # Importar generador de mapas
    from generate_map import generate_circuit_map

    # Resolver taxonomías (región y serie) a partir del nombre del PDF
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    region_id, serie_id = resolve_taxonomy_ids(pdf_name, auth)
    print(f"Región: {region_id or 'no detectada'} | Serie: {serie_id or 'no detectada'}")

    valid = [p for p in programs if "_error" not in p]
    print(f"Publicando {len(valid)} circuitos como '{status}'...")
    print("-" * 50)

    results = []
    for i, prog in enumerate(valid):
        prog_id = prog["id"]
        titulo = prog.get("titulo", "Sin título")
        print(f"  [{i+1}/{len(valid)}] {titulo}...")

        # Generar mapa interactivo
        map_html = None
        try:
            print(f"    Mapa...", end=" ", flush=True)
            map_html = generate_circuit_map(prog)
            print("OK", end=" | ", flush=True)
        except Exception as e:
            print(f"WARN: {e}", end=" | ", flush=True)

        # Subir imagen de portada (Pexels)
        featured_id = None
        images = prog.get("_images", {})
        cover = images.get("cover", {})
        if cover.get("url_large"):
            print(f"    Imagen...", end=" ", flush=True)
            seo_data = prog.get("seo", {})
            focus_kw = seo_data.get("focus_keyword", "") if seo_data else ""
            alt_text = f"{focus_kw} - {titulo}" if focus_kw else titulo
            featured_id = upload_image_from_url(cover["url_large"], titulo, auth, alt_text=alt_text)
            print(f"{'OK' if featured_id else 'SKIP'}", end=" | ", flush=True)

        # Generar contenido y crear circuito con SEO + taxonomías
        seo = prog.get("seo")
        content = build_page_content(prog, map_html)
        r = create_circuito(
            titulo, content, status, auth,
            seo=seo, region_id=region_id, serie_id=serie_id, program=prog,
            featured_media_id=featured_id,
        )

        if r.status_code == 201:
            post = r.json()
            print(f"OK (id={post['id']})")
            results.append({"id": prog_id, "post_id": post["id"], "link": post["link"]})
        else:
            print(f"ERROR {r.status_code}")
            results.append({"id": prog_id, "error": r.text[:150]})

    # Guardar log
    log_path = os.path.join(output_base, "wordpress_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("-" * 50)
    ok = len([r for r in results if "post_id" in r])
    print(f"Páginas creadas: {ok}/{len(valid)}")
    print(f"Log guardado en: {log_path}")
    print(f"Revisa en: {WP_URL}/wp-admin/edit.php?post_type=circuito")


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
