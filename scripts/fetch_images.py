"""
Obtiene imágenes de destinos turísticos desde Pexels API.

Busca una imagen de portada + una por ciudad principal del circuito.
Guarda URLs en el JSON del programa y en caché local.

Uso como módulo:
    from fetch_images import fetch_program_images
    images = fetch_program_images(program_dict)

Uso como script:
    python fetch_images.py programas.json [--test N]
"""

import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuración ---
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PEXELS_BASE = "https://api.pexels.com/v1"
CACHE_PATH = Path(__file__).parent.parent / ".cache" / "images_cache.json"

# Queries optimizadas por destino conocido
DESTINATION_QUERIES = {
    "Delhi": "Delhi India Red Fort travel",
    "Agra": "Taj Mahal India sunrise travel",
    "Jaipur": "Jaipur India Pink City palace travel",
    "Udaipur": "Udaipur India Lake Palace travel",
    "Mumbai": "Mumbai India Gateway travel",
    "Bombay": "Mumbai India Gateway travel",
    "Varanasi": "Varanasi India Ganges travel",
    "Khajuraho": "Khajuraho India temple travel",
    "Paris": "Paris Eiffel Tower travel",
    "Roma": "Rome Colosseum travel",
    "Barcelona": "Barcelona Sagrada Familia travel",
    "Londres": "London Big Ben travel",
    "Amsterdam": "Amsterdam canals travel",
    "Berlin": "Berlin Brandenburg Gate travel",
    "Praga": "Prague old town travel",
    "Vienna": "Vienna Schonbrunn travel",
    "Budapest": "Budapest Parliament Danube travel",
    "Venecia": "Venice Grand Canal travel",
    "Florencia": "Florence Duomo travel",
    "Madrid": "Madrid Spain travel",
    "Lisboa": "Lisbon Portugal travel",
    "New York": "New York Manhattan skyline",
    "Los Angeles": "Los Angeles Hollywood travel",
    "San Francisco": "San Francisco Golden Gate travel",
    "Washington": "Washington DC Capitol travel",
    "Chicago": "Chicago skyline travel",
    "Las Vegas": "Las Vegas strip night travel",
    "Toronto": "Toronto CN Tower travel",
    "Montreal": "Montreal Canada travel",
    "Cusco": "Cusco Peru Machu Picchu travel",
    "Bangkok": "Bangkok Thailand temple travel",
    "Tokio": "Tokyo Japan Shibuya travel",
    "Kyoto": "Kyoto Japan temple travel",
    "Bali": "Bali Indonesia temple rice travel",
    "Marrakech": "Marrakech Morocco medina travel",
    "El Cairo": "Cairo Egypt Pyramids travel",
    "Dubai": "Dubai Burj Khalifa travel",
    "Estambul": "Istanbul Turkey mosque travel",
    "Atenas": "Athens Greece Acropolis travel",
}


def _normalize(name):
    """Quita acentos y capitaliza."""
    nfkd = unicodedata.normalize("NFD", name)
    clean = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return clean.strip().title()


def _build_query(city):
    """Construye query de búsqueda para una ciudad."""
    normalized = _normalize(city)
    if normalized in DESTINATION_QUERIES:
        return DESTINATION_QUERIES[normalized]
    return f"{city} travel photography landmark"


def _load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return {}


def _save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def search_pexels(query, per_page=3):
    """Busca fotos en Pexels API. Retorna lista de resultados."""
    r = requests.get(
        f"{PEXELS_BASE}/search",
        headers={"Authorization": PEXELS_API_KEY},
        params={"query": query, "per_page": per_page, "orientation": "landscape"},
        timeout=10,
    )
    r.raise_for_status()
    photos = r.json().get("photos", [])

    results = []
    for p in photos:
        ratio = p["width"] / p["height"] if p["height"] > 0 else 0
        if ratio < 1.2 or ratio > 2.5:
            continue
        if p["width"] < 700:
            continue

        results.append({
            "url_small": p["src"]["small"],
            "url_medium": p["src"]["medium"],
            "url_large": p["src"]["large"],
            "photographer": p["photographer"],
            "photographer_url": p["photographer_url"],
            "alt": p.get("alt", ""),
            "pexels_url": p["url"],
            "query": query,
        })

    return results


def fetch_image_for_query(query, cache):
    """Busca imagen para un query, con caché."""
    cache_key = query.lower().strip()
    if cache_key in cache:
        return cache[cache_key], True  # (result, from_cache)

    try:
        results = search_pexels(query)
        if results:
            cache[cache_key] = results[0]
            return results[0], False
    except Exception as e:
        print(f"      [WARN] Pexels error: {e}")

    return None, False


def fetch_program_images(program):
    """
    Obtiene imagen de portada para un programa.
    Retorna dict con cover image data, o None.
    """
    cache = _load_cache()
    itinerario = program.get("itinerario", [])

    # Extraer ciudades únicas
    cities = []
    seen = set()
    for day in itinerario:
        for city in re.split(r"\s*[-–—]\s*", day.get("ciudades", "")):
            city = city.strip()
            if city and city not in seen:
                seen.add(city)
                cities.append(city)

    if not cities:
        return None

    # Buscar imagen de portada: probar las primeras ciudades
    cover = None
    api_calls = 0
    for city in cities[:3]:
        query = _build_query(city)
        result, from_cache = fetch_image_for_query(query, cache)
        if not from_cache:
            api_calls += 1
            time.sleep(0.5)  # rate limit
        if result:
            cover = result
            break

    _save_cache(cache)

    if cover:
        return {
            "cover": cover,
            "api_calls": api_calls,
        }
    return None


def enrich_programs_with_images(json_path, test_count=None):
    """Enriquece el JSON de programas con imágenes de Pexels."""
    if not PEXELS_API_KEY:
        print("Error: PEXELS_API_KEY no configurada en .env")
        sys.exit(1)

    with open(json_path, "r", encoding="utf-8") as f:
        programs = json.load(f)

    valid = [p for p in programs if "_error" not in p]
    if test_count:
        valid = valid[:test_count]

    print(f"Buscando imágenes para {len(valid)} programas...")
    print("-" * 50)

    total_api = 0
    total_cache = 0

    for i, prog in enumerate(valid):
        titulo = prog.get("titulo", "?")
        print(f"  [{i+1}/{len(valid)}] {titulo}...", end=" ", flush=True)

        result = fetch_program_images(prog)
        if result:
            prog["_images"] = result
            total_api += result["api_calls"]
            if result["api_calls"] == 0:
                total_cache += 1
            cover_url = result["cover"]["url_medium"]
            print(f"OK ({cover_url[-40:]})")
        else:
            print("Sin imagen")

    # Guardar JSON actualizado
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(programs, f, ensure_ascii=False, indent=2)

    print("-" * 50)
    print(f"Imágenes obtenidas. API calls: {total_api} | Cache hits: {total_cache}")
    print(f"JSON actualizado: {json_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python fetch_images.py <programas.json> [--test N]")
        sys.exit(1)

    json_path = sys.argv[1]
    test_count = None

    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        test_count = int(sys.argv[idx + 1])

    enrich_programs_with_images(json_path, test_count)
