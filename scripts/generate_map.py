"""
Generador de mapas interactivos para circuitos turísticos Europamundo.

Toma el JSON de un programa y genera un HTML self-contained con un mapa
MapLibre GL JS interactivo: rutas reales por carretera (OSRM), arcos de
vuelo, navegación día a día y panel de información.

Uso como módulo:
    from generate_map import generate_circuit_map
    html = generate_circuit_map(program_dict)

Uso como script:
    python generate_map.py programas.json [output_dir]
"""

import json
import math
import os
import re
import sys
import time
from pathlib import Path

import requests
from geopy.geocoders import Nominatim
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv

load_dotenv()

# --- Configuración ---
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CACHE_PATH = PROJECT_ROOT / ".cache" / "coords_cache.json"
TEMPLATE_DIR = PROJECT_ROOT / "templates"
NOMINATIM_DELAY = 1.1  # segundos entre llamadas (fair use)
OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
MAPTILER_KEY = os.getenv("MAPTILER_API_KEY", "")
CITY_SEPARATORS = re.compile(r"\s*[-–—]\s*")
FLIGHT_KEYWORDS = {"vuelo", "aeropuerto", "flight", "avión", "aéreo"}


# ══════════════════════════════════════════════════════════════════════
# A. GEOCODIFICACIÓN CON CACHÉ
# ══════════════════════════════════════════════════════════════════════

def _load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return {}


def _save_cache(cache):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def geocode_cities(cities, overrides=None):
    """
    Resuelve coordenadas para una lista de ciudades.
    Retorna {ciudad: {"lat": float, "lng": float}}.
    Usa caché en disco para evitar llamadas repetidas.
    """
    cache = _load_cache()
    geolocator = Nominatim(user_agent="europamundo-circuit-map/1.0")
    result = {}
    needs_save = False

    for city in cities:
        if city in cache:
            result[city] = cache[city]
            continue

        try:
            loc = geolocator.geocode(city, language="es")
            if loc:
                point = {"lat": loc.latitude, "lng": loc.longitude}
                result[city] = point
                cache[city] = point
                needs_save = True
                print(f"    Geocoded: {city} → ({loc.latitude:.4f}, {loc.longitude:.4f})")
            else:
                print(f"    [WARN] Ciudad no encontrada: {city}")
        except Exception as e:
            print(f"    [WARN] Error geocodificando {city}: {e}")

        time.sleep(NOMINATIM_DELAY)

    if needs_save:
        _save_cache(cache)

    if overrides:
        result.update(overrides)

    return result


# ══════════════════════════════════════════════════════════════════════
# B. EXTRACCIÓN DE CIUDADES Y SEGMENTOS
# ══════════════════════════════════════════════════════════════════════

def extract_unique_cities(itinerario):
    """Extrae lista de ciudades únicas en orden de aparición."""
    seen = set()
    cities = []
    for day in itinerario:
        for city in CITY_SEPARATORS.split(day.get("ciudades", "")):
            city = city.strip()
            if city and city not in seen:
                seen.add(city)
                cities.append(city)
    return cities


def detect_flight(day, vuelos_incluidos=None):
    """Determina si el desplazamiento de un día es aéreo."""
    ciudades_text = day.get("ciudades", "")
    desc = (day.get("descripcion") or day.get("descripción") or "").lower()

    # Indicadores explícitos en la descripción del día
    if any(kw in desc for kw in FLIGHT_KEYWORDS):
        return True

    # Verificar si el PAR origen-destino aparece en vuelos_incluidos
    # (no basta con que UNA ciudad aparezca)
    if vuelos_incluidos:
        cities = [c.strip() for c in CITY_SEPARATORS.split(ciudades_text)]
        if len(cities) >= 2:
            origen = cities[0].lower()
            destino = cities[-1].lower()
            vuelos_lower = vuelos_incluidos.lower()
            if origen in vuelos_lower and destino in vuelos_lower:
                return True

    return False


def build_segments(itinerario, vuelos_incluidos=None):
    """
    Genera lista de segmentos entre ciudades consecutivas.
    Retorna [{from, to, day_idx, is_flight}].
    """
    segments = []
    prev_city = None
    for i, day in enumerate(itinerario):
        cities = [c.strip() for c in CITY_SEPARATORS.split(day.get("ciudades", ""))]
        current_city = cities[-1] if cities else None
        if prev_city and current_city and prev_city != current_city:
            is_flight = detect_flight(day, vuelos_incluidos)
            segments.append({
                "from": prev_city,
                "to": current_city,
                "day_idx": i,
                "is_flight": is_flight,
            })
        prev_city = current_city
    return segments


def compute_nights_per_city(itinerario):
    """Cuenta noches por ciudad (último día no cuenta como noche)."""
    nights = {}
    for i, day in enumerate(itinerario):
        cities = [c.strip() for c in CITY_SEPARATORS.split(day.get("ciudades", ""))]
        city = cities[-1] if cities else None
        if city and i < len(itinerario) - 1:
            nights[city] = nights.get(city, 0) + 1
    return nights


def detect_meals(day):
    """Detecta comidas incluidas en la descripción del día."""
    desc = (day.get("descripcion") or day.get("descripción") or "").lower()
    return {
        "lunch": "almuerzo" in desc,
        "dinner": "cena" in desc,
    }


# ══════════════════════════════════════════════════════════════════════
# C. ROUTING
# ══════════════════════════════════════════════════════════════════════

def get_osrm_route(origin, dest):
    """Obtiene ruta por carretera de OSRM. Retorna GeoJSON LineString."""
    url = (
        f"{OSRM_URL}/route/v1/driving/"
        f"{origin['lng']},{origin['lat']};{dest['lng']},{dest['lat']}"
        f"?geometries=geojson&overview=simplified"
    )
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()["routes"][0]["geometry"]


def get_great_circle_arc(origin, dest, steps=50):
    """Genera arco de gran círculo para tramos aéreos."""
    lat1 = math.radians(origin["lat"])
    lon1 = math.radians(origin["lng"])
    lat2 = math.radians(dest["lat"])
    lon2 = math.radians(dest["lng"])

    d = math.acos(
        math.sin(lat1) * math.sin(lat2)
        + math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    )

    if d < 1e-10:
        return {"type": "LineString", "coordinates": [
            [origin["lng"], origin["lat"]], [dest["lng"], dest["lat"]]
        ]}

    coords = []
    for i in range(steps + 1):
        f = i / steps
        A = math.sin((1 - f) * d) / math.sin(d)
        B = math.sin(f * d) / math.sin(d)
        x = A * math.cos(lat1) * math.cos(lon1) + B * math.cos(lat2) * math.cos(lon2)
        y = A * math.cos(lat1) * math.sin(lon1) + B * math.cos(lat2) * math.sin(lon2)
        z = A * math.sin(lat1) + B * math.sin(lat2)
        lat = math.degrees(math.atan2(z, math.sqrt(x ** 2 + y ** 2)))
        lng = math.degrees(math.atan2(y, x))
        coords.append([round(lng, 5), round(lat, 5)])

    return {"type": "LineString", "coordinates": coords}


def _straight_line(origin, dest):
    """Fallback: línea recta entre dos puntos."""
    return {"type": "LineString", "coordinates": [
        [origin["lng"], origin["lat"]], [dest["lng"], dest["lat"]]
    ]}


# ══════════════════════════════════════════════════════════════════════
# D. FUNCIÓN PRINCIPAL Y CLI
# ══════════════════════════════════════════════════════════════════════

def generate_circuit_map(program):
    """
    Genera HTML del mapa interactivo para un programa.
    Recibe dict del programa (mismo formato que programas.json).
    Retorna string HTML (fragmento embebible).
    """
    itinerario = program.get("itinerario", [])
    incluye = program.get("incluye", {})
    vuelos_incluidos = incluye.get("vuelos_incluidos") if incluye else None

    # 1. Extraer ciudades y geocodificar
    cities = extract_unique_cities(itinerario)
    print(f"  Ciudades: {', '.join(cities)}")
    coords = geocode_cities(cities, program.get("coords_override"))

    if not coords:
        print("  [WARN] Sin coordenadas — mapa no generado")
        return ""

    # 2. Calcular segmentos y rutas
    segments = build_segments(itinerario, vuelos_incluidos)
    tramos = []
    for seg in segments:
        if seg["from"] not in coords or seg["to"] not in coords:
            print(f"    [WARN] Tramo ignorado: {seg['from']} → {seg['to']}")
            continue

        origin = coords[seg["from"]]
        dest = coords[seg["to"]]

        if seg["is_flight"]:
            geojson = get_great_circle_arc(origin, dest)
        else:
            try:
                geojson = get_osrm_route(origin, dest)
            except Exception as e:
                print(f"    [WARN] OSRM falló {seg['from']}→{seg['to']}: {e}")
                geojson = _straight_line(origin, dest)

        tramos.append({
            "from": seg["from"],
            "to": seg["to"],
            "day_idx": seg["day_idx"],
            "is_flight": seg["is_flight"],
            "geojson": geojson,
        })
        time.sleep(0.3)  # cortesía OSRM

    # 3. Datos adicionales
    nights = compute_nights_per_city(itinerario)
    meals = [detect_meals(day) for day in itinerario]

    # 4. Detectar vuelo por día
    for i, day in enumerate(itinerario):
        is_flight_day = any(
            t["day_idx"] == i and t["is_flight"] for t in tramos
        )
        meals[i]["flight"] = is_flight_day

    # 5. Renderizar template
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("circuit_map.html.j2")

    html = template.render(
        circuit=program,
        coords_json=json.dumps(coords, ensure_ascii=False),
        tramos_json=json.dumps(tramos, ensure_ascii=False),
        nights_json=json.dumps(nights, ensure_ascii=False),
        meals_json=json.dumps(meals, ensure_ascii=False),
        maptiler_key=MAPTILER_KEY,
    )

    return html


def generate_map_file(program, output_dir):
    """
    Genera archivo HTML completo (con shell) para preview local.
    """
    fragment = generate_circuit_map(program)
    if not fragment:
        return None

    prog_id = program.get("id", "unknown")
    titulo = program.get("titulo", "Circuito")

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titulo} — Mapa Interactivo</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0; padding:20px; background:#f7f8fa; font-family:'Roboto',sans-serif;">
<h1 style="text-align:center; color:#3b3d42; font-weight:400;">{titulo}</h1>
{fragment}
</body>
</html>"""

    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{prog_id}_map.html")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


# ── CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generate_map.py <programas.json> [output_dir]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output/maps"

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Soporta JSON de un programa o lista de programas
    programs = data if isinstance(data, list) else [data]

    print(f"Generando mapas para {len(programs)} programa(s)...")
    for prog in programs:
        if "_error" in prog:
            continue
        titulo = prog.get("titulo", "?")
        prog_id = prog.get("id", "?")
        print(f"\n[{prog_id}] {titulo}")
        path = generate_map_file(prog, output_dir)
        if path:
            print(f"  → {path}")
