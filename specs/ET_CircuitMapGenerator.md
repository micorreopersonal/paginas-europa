# Especificación Técnica — Circuit Map Generator
**Versión:** 1.0  
**Fecha:** Marzo 2026  
**Proyecto:** Generador estático de mapas interactivos de circuitos turísticos  
**Audiencia:** Equipo de desarrollo

---

## 1. Resumen de la solución

Un script Python standalone (`generate_map.py`) que se añade como etapa al pipeline de publicación WordPress existente. Lee el JSON del circuito, resuelve coordenadas geográficas, calcula rutas reales por carretera, y renderiza un archivo HTML completamente autónomo con el mapa interactivo y los datos inlineados. No requiere servidor, plugin, ni llamadas en runtime desde el browser del visitante.

```
JSON circuito
    ↓
generate_map.py
    ├── geopy + Nominatim  →  coordenadas
    ├── OSRM               →  rutas GeoJSON
    └── Jinja2 template    →  HTML self-contained
                                  ↓
                        {circuit_id}_map.html
                        (o string de retorno)
```

---

## 2. Stack tecnológico

| Componente | Librería / Servicio | Versión | Rol |
|---|---|---|---|
| Lenguaje | Python | 3.11+ | runtime del generador |
| Geocodificación | geopy | 2.4+ | Nominatim client con rate limiting |
| HTTP client | httpx | 0.27+ | llamadas a OSRM, MapTiler |
| Templates | Jinja2 | 3.1+ | renderizado del HTML final |
| Validación | pydantic v2 | 2.7+ | parsing y validación del JSON |
| Simplificación GeoJSON | shapely | 2.0+ | Douglas-Peucker sobre rutas |
| Gestor de dependencias | uv | latest | instalación reproducible |
| Mapa en browser | MapLibre GL JS | 4.x (CDN) | render del mapa vectorial |
| Tiles base | MapTiler Cloud | — | proveedor de tiles vectoriales |
| Routing engine | OSRM | public API | cálculo de rutas por carretera |

**Dependencias del HTML generado (cargadas en browser del visitante):**

- `maplibre-gl@4` desde `https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.js` — única dependencia externa en runtime.
- Tiles vectoriales de MapTiler — requieren conexión a internet al cargar el mapa.

---

## 3. Estructura del proyecto

```
circuit-map-generator/
├── pyproject.toml              # uv: dependencias y scripts
├── uv.lock
├── .env.example
│
├── generate_map.py             # entry point — uso como script o módulo
│
├── src/
│   ├── __init__.py
│   ├── models.py               # Pydantic: CircuitSchema, DaySchema, GeoPoint, Tramo
│   ├── geocoder.py             # Nominatim + caché en disco
│   ├── router.py               # OSRM client + great-circle fallback
│   ├── parser.py               # extrae ciudades del itinerario, detecta tramos
│   └── renderer.py             # Jinja2 → HTML string
│
├── templates/
│   └── circuit_map.html.j2     # plantilla HTML del mapa
│
├── .cache/
│   └── coords_cache.json       # caché persistente de coordenadas (gitignore)
│
└── tests/
    ├── test_geocoder.py
    ├── test_router.py
    ├── test_parser.py
    └── fixtures/
        └── rajasthan_mumbai.json
```

---

## 4. Modelos de datos (Pydantic v2)

```python
# src/models.py

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class TramoType(str, Enum):
    terrestre = "terrestre"
    aereo = "aereo"

class GeoPoint(BaseModel):
    lat: float
    lng: float

class DaySchema(BaseModel):
    dia: str
    dia_semana: str
    ciudades: str
    descripcion: str

class IncludesSchema(BaseModel):
    almuerzos: Optional[str] = None
    cenas: Optional[str] = None
    vuelos_incluidos: Optional[str] = None

class CircuitSchema(BaseModel):
    id: str
    titulo: str
    dias: int = Field(gt=0, le=60)
    precio_desde: Optional[str] = None
    itinerario: list[DaySchema] = Field(min_length=1)
    incluye: Optional[IncludesSchema] = None
    coords_override: Optional[dict[str, GeoPoint]] = None  # forzar coords por ciudad

class Tramo(BaseModel):
    origen: str
    destino: str
    tipo: TramoType
    geojson: dict                   # GeoJSON LineString
    dia_inicio: int                 # índice del día donde comienza

class MapData(BaseModel):
    circuit: CircuitSchema
    coords: dict[str, GeoPoint]    # ciudad → coordenadas
    tramos: list[Tramo]
    days_by_city: dict[str, list[int]]  # ciudad → lista de índices de días
```

---

## 5. Módulo de geocodificación

```python
# src/geocoder.py

import json
import time
from pathlib import Path
from geopy.geocoders import Nominatim
from .models import GeoPoint

CACHE_PATH = Path(".cache/coords_cache.json")

class GeocoderService:
    def __init__(self, user_agent: str = "circuit-map-generator/1.0",
                 nominatim_delay: float = 1.1):
        self.geolocator = Nominatim(user_agent=user_agent)
        self.delay = nominatim_delay
        self._cache: dict[str, dict] = self._load_cache()

    def resolve_all(self, cities: list[str],
                    overrides: dict[str, GeoPoint] | None = None) -> dict[str, GeoPoint]:
        """
        Resuelve coordenadas para todas las ciudades.
        - Consulta caché primero
        - Llama a Nominatim solo para las no cacheadas
        - Aplica overrides al final (mayor prioridad)
        """
        result = {}

        for city in cities:
            if city in self._cache:
                result[city] = GeoPoint(**self._cache[city])
            else:
                loc = self.geolocator.geocode(city, language="es")
                if loc:
                    point = GeoPoint(lat=loc.latitude, lng=loc.longitude)
                    result[city] = point
                    self._cache[city] = point.model_dump()
                else:
                    print(f"[WARN] Ciudad no encontrada: {city}")
                time.sleep(self.delay)

        self._save_cache()

        if overrides:
            result.update(overrides)

        return result

    def _load_cache(self) -> dict:
        if CACHE_PATH.exists():
            return json.loads(CACHE_PATH.read_text())
        CACHE_PATH.parent.mkdir(exist_ok=True)
        return {}

    def _save_cache(self):
        CACHE_PATH.write_text(json.dumps(self._cache, indent=2, ensure_ascii=False))
```

---

## 6. Módulo de routing

```python
# src/router.py

import httpx
import math
from .models import GeoPoint, Tramo, TramoType

OSRM_PUBLIC = "https://router.project-osrm.org"

def get_road_route(origin: GeoPoint, destination: GeoPoint,
                   osrm_url: str = OSRM_PUBLIC) -> dict:
    """Llama a OSRM y devuelve un GeoJSON LineString simplificado."""
    url = (f"{osrm_url}/route/v1/driving/"
           f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"
           f"?geometries=geojson&overview=simplified")
    
    with httpx.Client(timeout=10) as client:
        resp = client.get(url)
        resp.raise_for_status()
        data = resp.json()

    return data["routes"][0]["geometry"]   # GeoJSON LineString


def get_arc_route(origin: GeoPoint, destination: GeoPoint,
                  steps: int = 50) -> dict:
    """
    Genera un arco de gran círculo entre dos puntos para tramos aéreos.
    Devuelve un GeoJSON LineString con `steps` puntos interpolados.
    """
    coords = []
    lat1, lon1 = math.radians(origin.lat), math.radians(origin.lng)
    lat2, lon2 = math.radians(destination.lat), math.radians(destination.lng)

    for i in range(steps + 1):
        f = i / steps
        A = math.sin((1 - f) * math.acos(
            math.sin(lat1) * math.sin(lat2) +
            math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        )) / math.sin(math.acos(
            math.sin(lat1) * math.sin(lat2) +
            math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        ))
        B = math.sin(f * math.acos(
            math.sin(lat1) * math.sin(lat2) +
            math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        )) / math.sin(math.acos(
            math.sin(lat1) * math.sin(lat2) +
            math.cos(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
        ))
        x = A * math.cos(lat1) * math.cos(lon1) + B * math.cos(lat2) * math.cos(lon2)
        y = A * math.cos(lat1) * math.sin(lon1) + B * math.cos(lat2) * math.sin(lon2)
        z = A * math.sin(lat1) + B * math.sin(lat2)
        lat = math.degrees(math.atan2(z, math.sqrt(x**2 + y**2)))
        lng = math.degrees(math.atan2(y, x))
        coords.append([lng, lat])

    return {"type": "LineString", "coordinates": coords}
```

---

## 7. Módulo parser — extrae ciudades y detecta tramos

```python
# src/parser.py

import re
from .models import DaySchema, TramoType

# Separadores reconocidos entre ciudades en el campo `ciudades`
CITY_SEPARATORS = re.compile(r"\s*[→✈,\-–]\s*")

FLIGHT_KEYWORDS = {"vuelo", "aeropuerto", "flight", "✈", "volar", "aéreo"}


def extract_cities(itinerario: list[DaySchema]) -> list[str]:
    """Devuelve lista de ciudades únicas en orden de aparición."""
    seen = set()
    cities = []
    for day in itinerario:
        for city in CITY_SEPARATORS.split(day.ciudades):
            city = city.strip()
            if city and city not in seen:
                seen.add(city)
                cities.append(city)
    return cities


def detect_tramo_type(day: DaySchema, vuelos_incluidos: str | None) -> TramoType:
    """Determina si el desplazamiento de un día es aéreo o terrestre."""
    text = (day.ciudades + " " + day.descripcion).lower()
    if "✈" in day.ciudades:
        return TramoType.aereo
    if any(kw in text for kw in FLIGHT_KEYWORDS):
        return TramoType.aereo
    if vuelos_incluidos:
        cities_in_day = CITY_SEPARATORS.split(day.ciudades)
        for city in cities_in_day:
            if city.strip() in vuelos_incluidos:
                return TramoType.aereo
    return TramoType.terrestre


def build_day_city_pairs(itinerario: list[DaySchema]) -> list[tuple[str, str, int, TramoType]]:
    """
    Devuelve lista de (origen, destino, dia_idx, tipo) para cada tramo.
    Solo genera tramo cuando la ciudad cambia entre días consecutivos.
    """
    pairs = []
    prev_city = None
    for i, day in enumerate(itinerario):
        cities = [c.strip() for c in CITY_SEPARATORS.split(day.ciudades)]
        current_city = cities[-1]   # ciudad de llegada/destino del día
        if prev_city and prev_city != current_city:
            tipo = detect_tramo_type(day, None)
            pairs.append((prev_city, current_city, i, tipo))
        prev_city = current_city
    return pairs
```

---

## 8. Entry point — generate_map.py

```python
# generate_map.py

import json
import sys
from pathlib import Path
from src.models import CircuitSchema, MapData
from src.geocoder import GeocoderService
from src.router import get_road_route, get_arc_route
from src.parser import extract_cities, build_day_city_pairs, TramoType
from src.models import Tramo
from src.renderer import render_map_html


def generate_circuit_map(circuit_data: dict, osrm_url: str | None = None) -> str:
    """
    Función principal. Recibe el dict del JSON del circuito.
    Retorna el HTML completo como string.
    Uso como módulo desde el pipeline:
        html = generate_circuit_map(json_dict)
    """
    circuit = CircuitSchema.model_validate(circuit_data)

    # 1. Geocodificar ciudades
    geocoder = GeocoderService()
    cities = extract_cities(circuit.itinerario)
    coords = geocoder.resolve_all(cities, overrides=circuit.coords_override)

    # 2. Calcular tramos
    tramos = []
    for origen, destino, dia_idx, tipo in build_day_city_pairs(circuit.itinerario):
        if origen not in coords or destino not in coords:
            print(f"[WARN] Tramo ignorado: {origen} → {destino} (coordenadas faltantes)")
            continue

        if tipo == TramoType.aereo:
            geojson = get_arc_route(coords[origen], coords[destino])
        else:
            try:
                url = osrm_url or "https://router.project-osrm.org"
                geojson = get_road_route(coords[origen], coords[destino], url)
            except Exception as e:
                print(f"[WARN] OSRM falló para {origen}→{destino}: {e}. Usando línea recta.")
                geojson = {
                    "type": "LineString",
                    "coordinates": [
                        [coords[origen].lng, coords[origen].lat],
                        [coords[destino].lng, coords[destino].lat],
                    ]
                }

        tramos.append(Tramo(
            origen=origen, destino=destino,
            tipo=tipo, geojson=geojson, dia_inicio=dia_idx
        ))

    # 3. Agrupar días por ciudad
    days_by_city: dict[str, list[int]] = {}
    for i, day in enumerate(circuit.itinerario):
        for city in [c.strip() for c in day.ciudades.replace("→", ",")
                     .replace("✈", ",").split(",")]:
            if city:
                days_by_city.setdefault(city, []).append(i)

    map_data = MapData(
        circuit=circuit,
        coords=coords,
        tramos=tramos,
        days_by_city=days_by_city,
    )

    return render_map_html(map_data)


# ── CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generate_map.py circuit.json [output_dir]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("output")
    output_dir.mkdir(exist_ok=True)

    circuit_data = json.loads(input_path.read_text())
    html = generate_circuit_map(circuit_data)

    output_file = output_dir / f"{circuit_data['id']}_map.html"
    output_file.write_text(html, encoding="utf-8")
    print(f"[OK] Mapa generado: {output_file}")
```

---

## 9. Template HTML (circuit_map.html.j2)

La plantilla Jinja2 produce un HTML completamente self-contained. Los datos del circuito se inyectan como constantes JavaScript en un bloque `<script>` en el `<head>`.

```html
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ circuit.titulo }}</title>
<link href="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.css" rel="stylesheet">
<script src="https://unpkg.com/maplibre-gl@4/dist/maplibre-gl.js"></script>
<script>
/* ── datos inlineados por generate_map.py ── */
const CIRCUIT = {{ circuit_json | tojson }};
const COORDS  = {{ coords_json | tojson }};
const TRAMOS  = {{ tramos_json | tojson }};
const DAYS_BY_CITY = {{ days_by_city_json | tojson }};
const MAPTILER_KEY = "{{ maptiler_key }}";
</script>
<style>
/* estilos del mapa y panel de días — incluidos inline */
...
</style>
</head>
<body>
<div id="map"></div>
<div id="day-panel">...</div>
<script>
/* lógica MapLibre + navegación por días */
...
</script>
</body>
</html>
```

La lógica JavaScript del mapa (inicialización de MapLibre, capas de rutas, animación flyTo, panel de días) está embebida completamente en la plantilla. No se usa React ni ningún framework — vanilla JS puro para minimizar el tamaño del HTML generado.

**Tamaño estimado del HTML generado:**

- Template base (CSS + JS MapLibre init): ~12 KB
- Datos GeoJSON de rutas (circuito de 10 etapas, rutas simplificadas): ~40-80 KB
- Total por circuito: **50-100 KB** — perfectamente manejable como campo de WordPress

---

## 10. Integración con el pipeline existente

### Opción A — Llamada como función Python (recomendada)

Si el pipeline está escrito en Python, simplemente se importa y llama:

```python
# en el pipeline existente
from generate_map import generate_circuit_map

def process_circuit(circuit_json: dict):
    # ... etapas existentes ...

    # etapa nueva: generar mapa
    map_html = generate_circuit_map(circuit_json)

    # insertar en WordPress via REST API
    wp_client.update_post_field(
        post_id=post_id,
        field="circuit_map_html",
        value=map_html
    )
```

### Opción B — Llamada como subprocess

Si el pipeline no está en Python o necesita aislamiento:

```bash
python generate_map.py data/rajasthan.json output/
# genera output/rajasthan_mumbai_map.html
```

### Inserción en WordPress

El pipeline ya existente maneja la autenticación con WordPress. El campo de destino es un campo ACF de tipo `textarea` actualizado via WP REST API:

```python
import requests

def update_map_field(post_id: int, html: str, wp_url: str, token: str):
    requests.post(
        f"{wp_url}/wp-json/acf/v3/posts/{post_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"fields": {"circuit_map_html": html}}
    )
```

En la plantilla WordPress (`single-circuito.php`):

```php
<?php
$map_html = get_field('circuit_map_html');
if ($map_html) {
    echo $map_html;   // el HTML ya es seguro — generado por nuestro pipeline
} else {
    // fallback a imagen fija si el mapa no se generó aún
    echo '<img src="' . get_field('circuit_image') . '" alt="Mapa del circuito">';
}
?>
```

---

## 11. Configuración

Todas las variables configurables se gestionan via `.env`:

```bash
# .env

# Geocodificación
NOMINATIM_USER_AGENT=circuit-map-generator/1.0
NOMINATIM_DELAY=1.1           # segundos entre requests (fair use)

# Fallback geocodificación de mayor precisión (opcional)
MAPTILER_API_KEY=              # si se deja vacío, solo Nominatim

# Routing
OSRM_URL=https://router.project-osrm.org   # o http://localhost:5000 para instancia local

# Mapa base en browser
MAP_STYLE_URL=https://api.maptiler.com/maps/outdoor-v2/style.json?key={MAPTILER_API_KEY}

# Simplificación de rutas (0.0 = sin simplificación, 0.001 = agresiva)
ROUTE_SIMPLIFICATION_TOLERANCE=0.0005

# Caché
CACHE_DIR=.cache
```

---

## 12. Instalación y comandos

```bash
# Setup del entorno
git clone https://github.com/org/circuit-map-generator
cd circuit-map-generator
uv sync

# Generar mapa de un circuito
uv run python generate_map.py data/rajasthan_mumbai.json

# Tests
uv run pytest

# Lint y tipos
uv run ruff check src/
uv run mypy src/
```

**pyproject.toml mínimo:**

```toml
[project]
name = "circuit-map-generator"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "geopy>=2.4",
    "httpx>=0.27",
    "jinja2>=3.1",
    "pydantic>=2.7",
    "shapely>=2.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest", "ruff", "mypy"]

[tool.uv]
dev-dependencies = ["pytest", "ruff", "mypy"]
```

---

## 13. Decisiones técnicas

| Decisión | Alternativas consideradas | Razón de elección |
|---|---|---|
| HTML self-contained vs componente con API | FastAPI backend, Web Component con fetch | Sin servidor, sin costes de infraestructura, integra directamente con pipeline existente |
| MapLibre GL JS vs Leaflet | Leaflet, Google Maps JS | Tiles vectoriales, WebGL, sin licencia, soporte nativo de estilos MapTiler |
| Datos inlineados vs fetch en runtime | fetch al cargar la página | Funciona offline, sin CORS, sin dependencia de servidor externo |
| Jinja2 vs f-strings | f-strings, mako | Template legible y mantenible, auto-escape de HTML, separación clara datos/presentación |
| geopy + Nominatim vs Google Geocoding | Google Geocoding API, HERE | Sin coste, sin API key obligatoria, suficiente para nombres de ciudades turísticas |
| OSRM público vs instancia propia | Google Directions, Mapbox, instancia Docker | Sin coste por request, datos OSM, fácil despliegue local si el volumen crece |
| Caché en archivo JSON vs Redis | Redis, SQLite | Cero dependencias extra, legible por humanos, portátil entre máquinas del equipo |
| uv vs pip/poetry | pip, poetry, conda | Instalación determinista y rápida, estándar emergente 2025-2026 |
| Vanilla JS en template vs React | React, Vue | HTML más ligero (~50KB vs ~200KB+), sin build step, sin dependencias npm en el generador |

---

## 14. Hoja de ruta

| Versión | Mejora |
|---|---|
| v1.1 | Enriquecimiento de descripciones de lugares con Claude API durante el pipeline |
| v1.2 | Generación de imagen og:image estática (screenshot del mapa via Playwright) para redes sociales |
| v1.3 | Visualización 3D de terreno con MapLibre terrain layer |
| v1.4 | Soporte de tiles pmtiles self-hosted para funcionamiento 100% offline |
| v2.0 | Instancia local de OSRM en Docker incluida en el pipeline para independencia total de APIs externas |
