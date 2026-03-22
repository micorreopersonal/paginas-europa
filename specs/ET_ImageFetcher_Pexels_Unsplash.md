# Especificación Técnica — Image Fetcher
## Módulo de obtención automática de imágenes de destinos turísticos
**Versión:** 1.0  
**Fecha:** Marzo 2026  
**Proyecto:** Circuit Map Generator — etapa de imágenes  
**Contexto:** Etapa adicional en pipeline de publicación WordPress  
**Audiencia:** Equipo de desarrollo

---

## 1. Resumen

Módulo Python (`image_fetcher.py`) que se integra como etapa del pipeline de publicación WordPress. Dado el JSON de un circuito turístico, resuelve automáticamente la imagen de portada y las imágenes secundarias de cada destino consultando las APIs de Pexels y Unsplash. Las URLs resultantes se almacenan en el JSON enriquecido y quedan disponibles para el template WordPress y el generador de mapas HTML.

```
JSON circuito
    ↓
image_fetcher.py
    ├── construye query por ciudad/destino
    ├── consulta Pexels API  (prioridad 1)
    ├── consulta Unsplash API (fallback)
    ├── aplica filtros de calidad y relevancia
    ├── guarda URLs en caché local
    └── retorna JSON enriquecido con _images{}
```

---

## 2. Stack tecnológico

| Componente | Librería / Servicio | Versión | Rol |
|---|---|---|---|
| Lenguaje | Python | 3.11+ | runtime del módulo |
| HTTP client | httpx | 0.27+ | llamadas async a ambas APIs |
| Validación | pydantic v2 | 2.7+ | modelos de respuesta de API |
| Caché | diskcache | 5.6+ | evitar llamadas repetidas |
| Gestor deps | uv | latest | entorno reproducible |
| Fuente primaria | Pexels API | v1 | stock fotográfico gratuito |
| Fuente secundaria | Unsplash API | v1 | fallback y diversidad |

**Límites de las APIs (tier gratuito):**

| API | Rate limit | Requests/mes | API Key requerida |
|---|---|---|---|
| Pexels | 200 req/hora | 20,000 | Sí — registro gratuito |
| Unsplash | 50 req/hora (demo) / 5,000 (producción) | ilimitado (producción) | Sí — registro gratuito |

---

## 3. Posición en el pipeline

```
[JSON circuito crudo]
        ↓
[image_fetcher.py]      ← ESTE MÓDULO
        ↓
[JSON con _images{}]
        ↓
[generate_map.py]       ← mapa interactivo HTML
        ↓
[template WordPress]    ← usa _images.cover para la card
        ↓
[página WP publicada]
```

El módulo puede ejecutarse de forma independiente o encadenado con `generate_map.py` ya que ambos consumen y enriquecen el mismo JSON.

---

## 4. Estructura del proyecto

```
circuit-map-generator/
├── image_fetcher.py            # entry point — uso como script o módulo
│
├── src/
│   ├── images/
│   │   ├── __init__.py
│   │   ├── models.py           # Pydantic: ImageResult, ImageSet, ProviderResponse
│   │   ├── pexels_client.py    # cliente Pexels API v1
│   │   ├── unsplash_client.py  # cliente Unsplash API v1
│   │   ├── query_builder.py    # construye queries desde nombres de destino
│   │   ├── selector.py         # lógica de selección y ranking de imágenes
│   │   └── cache.py            # caché en disco con diskcache
│
├── .cache/
│   └── images_cache/           # caché persistente de URLs (gitignore)
│
└── tests/
    ├── test_pexels_client.py
    ├── test_unsplash_client.py
    ├── test_query_builder.py
    └── fixtures/
        └── rajasthan_mumbai.json
```

---

## 5. Modelos de datos (Pydantic v2)

```python
# src/images/models.py

from pydantic import BaseModel, HttpUrl
from typing import Optional
from enum import Enum

class ImageProvider(str, Enum):
    pexels = "pexels"
    unsplash = "unsplash"

class ImageSize(str, Enum):
    small = "small"       # ~400px — thumbnails, cards pequeñas
    medium = "medium"     # ~800px — cards estándar (caso de uso principal)
    large = "large"       # ~1280px — hero, portada full-width
    original = "original" # resolución original

class ImageResult(BaseModel):
    provider: ImageProvider
    provider_id: str                    # ID en la plataforma de origen
    url_small: str                      # URL directa ~400px
    url_medium: str                     # URL directa ~800px
    url_large: str                      # URL directa ~1280px
    url_original: str                   # URL resolución original
    photographer: str                   # atribución — requerida por licencia
    photographer_url: str               # link al perfil del fotógrafo
    provider_url: str                   # link a la página original en Pexels/Unsplash
    alt_text: Optional[str] = None      # descripción accesible
    width: int
    height: int
    query_used: str                     # query que generó este resultado

class ImageSet(BaseModel):
    """Conjunto de imágenes asociadas a un circuito completo."""
    cover: ImageResult                  # imagen principal de la card/portada
    destinations: dict[str, ImageResult]  # ciudad → imagen individual
    query_cover: str                    # query usada para la portada

class CircuitImages(BaseModel):
    """Bloque _images que se añade al JSON del circuito."""
    cover: ImageResult
    destinations: dict[str, ImageResult]
    generated_at: str                   # ISO timestamp de generación
    cache_hits: int                     # cuántas imágenes vinieron del caché
    api_calls: int                      # cuántas llamadas reales se hicieron
```

---

## 6. Constructor de queries

La calidad de las imágenes depende directamente de qué query se envía a cada API. El módulo construye queries enriquecidas desde los nombres de destino del JSON.

```python
# src/images/query_builder.py

# Mapeo de destinos conocidos a queries optimizadas.
# Cubre los destinos turísticos más frecuentes en paquetes desde Lima.
DESTINATION_QUERY_MAP: dict[str, str] = {
    # Europa
    "Paris": "Paris France Eiffel Tower travel",
    "Roma": "Rome Italy Colosseum travel photography",
    "Barcelona": "Barcelona Spain Sagrada Familia travel",
    "Amsterdam": "Amsterdam Netherlands canals travel",
    "Londres": "London England Big Ben travel photography",
    "Berlin": "Berlin Germany Brandenburg Gate travel",
    "Praga": "Prague Czech Republic old town travel",
    "Vienna": "Vienna Austria Schönbrunn Palace travel",
    "Budapest": "Budapest Hungary Parliament Danube travel",
    "Venecia": "Venice Italy Grand Canal gondola travel",
    "Florencia": "Florence Italy Duomo travel photography",
    "Athens": "Athens Greece Acropolis travel",
    "Lisboa": "Lisbon Portugal Belem Tower travel",
    "Madrid": "Madrid Spain Prado Museum travel",
    "Dubrovnik": "Dubrovnik Croatia old city walls travel",
    # Asia
    "Delhi": "Delhi India Red Fort travel photography",
    "Agra": "Agra India Taj Mahal travel",
    "Jaipur": "Jaipur India Pink City travel",
    "Udaipur": "Udaipur India Lake Palace travel",
    "Mumbai": "Mumbai India Gateway of India travel",
    "Tokio": "Tokyo Japan Shibuya travel photography",
    "Kyoto": "Kyoto Japan temples travel",
    "Bangkok": "Bangkok Thailand temple travel",
    "Bali": "Bali Indonesia rice terraces travel",
    # América
    "Cusco": "Cusco Peru Machu Picchu travel",
    "Buenos Aires": "Buenos Aires Argentina travel photography",
    "Rio de Janeiro": "Rio de Janeiro Brazil Christ Redeemer travel",
    "New York": "New York USA Manhattan skyline travel",
    # África / Otros
    "Marrakech": "Marrakech Morocco medina travel photography",
    "El Cairo": "Cairo Egypt Pyramids Giza travel",
    "Dubái": "Dubai UAE Burj Khalifa skyline travel",
}

def build_query(city_name: str, circuit_title: str = "") -> str:
    """
    Construye la query óptima para buscar imagen de un destino.
    
    Prioridad:
    1. Query predefinida en DESTINATION_QUERY_MAP (mayor relevancia)
    2. Normalización del nombre de ciudad + sufijo "travel photography"
    3. Fallback genérico si la ciudad no se reconoce
    """
    # Normalizar nombre (quitar acentos, capitalizar)
    normalized = _normalize_city_name(city_name)
    
    if normalized in DESTINATION_QUERY_MAP:
        return DESTINATION_QUERY_MAP[normalized]
    
    # Construcción dinámica para ciudades no mapeadas
    return f"{city_name} travel photography landmark scenic"


def build_cover_query(circuit_json: dict) -> str:
    """
    Construye la query para la imagen de portada del circuito.
    Usa la primera ciudad del itinerario o el título del circuito.
    
    Ejemplos:
    "Paquetes a Europa" → "Europe travel landmarks scenic"
    "Gran Gira de Alemania" → "Germany travel scenic photography"
    "Rajastán y Mumbai" → build_query("Jaipur") — primera ciudad
    """
    titulo = circuit_json.get("titulo", "")
    itinerario = circuit_json.get("itinerario", [])
    
    # Primera ciudad con imagen disponible como protagonista
    if itinerario:
        primera_ciudad = _extract_first_city(itinerario[0]["ciudades"])
        return build_query(primera_ciudad)
    
    # Fallback al título del circuito
    return f"{titulo} travel photography"


def _normalize_city_name(name: str) -> str:
    """Normaliza el nombre: quita acentos, capitaliza primera letra."""
    import unicodedata
    normalized = unicodedata.normalize("NFD", name)
    without_accents = "".join(c for c in normalized
                              if unicodedata.category(c) != "Mn")
    return without_accents.strip().title()
```

---

## 7. Cliente Pexels API

```python
# src/images/pexels_client.py

import httpx
from .models import ImageResult, ImageProvider

PEXELS_BASE = "https://api.pexels.com/v1"

class PexelsClient:
    def __init__(self, api_key: str):
        self.headers = {"Authorization": api_key}

    async def search(
        self,
        query: str,
        per_page: int = 5,
        orientation: str = "landscape",  # landscape | portrait | square
    ) -> list[ImageResult]:
        """
        Busca fotos en Pexels.
        
        Parámetros clave:
        - orientation: "landscape" para cards horizontales (caso de uso principal)
        - per_page: devolver N resultados para que el selector elija el mejor
        - locale: no especificamos para obtener el pool más amplio
        """
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{PEXELS_BASE}/search",
                headers=self.headers,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

        return [self._parse_photo(p, query) for p in data.get("photos", [])]

    def _parse_photo(self, photo: dict, query: str) -> ImageResult:
        src = photo["src"]
        return ImageResult(
            provider=ImageProvider.pexels,
            provider_id=str(photo["id"]),
            url_small=src["small"],       # ~400px wide
            url_medium=src["medium"],     # ~800px wide (principal para cards)
            url_large=src["large"],       # ~1280px wide
            url_original=src["original"],
            photographer=photo["photographer"],
            photographer_url=photo["photographer_url"],
            provider_url=photo["url"],
            alt_text=photo.get("alt", ""),
            width=photo["width"],
            height=photo["height"],
            query_used=query,
        )
```

**Notas sobre la API de Pexels:**

El endpoint principal es `GET /v1/search`. La autenticación va en el header `Authorization: {API_KEY}` (sin prefijo "Bearer"). El parámetro `orientation=landscape` es crítico para imágenes de cards turísticas — evita fotos verticales que se recortarán mal. El campo `src.medium` (~800px) es el tamaño óptimo para las cards del sitio visto en la captura. La API no requiere attribution en el HTML según su licencia, pero sí enlace a Pexels y al fotógrafo cuando sea posible — el modelo `ImageResult` almacena ambos.

---

## 8. Cliente Unsplash API

```python
# src/images/unsplash_client.py

import httpx
from .models import ImageResult, ImageProvider

UNSPLASH_BASE = "https://api.unsplash.com"

class UnsplashClient:
    def __init__(self, access_key: str):
        self.headers = {"Authorization": f"Client-ID {access_key}"}

    async def search(
        self,
        query: str,
        per_page: int = 5,
        orientation: str = "landscape",
    ) -> list[ImageResult]:
        """
        Busca fotos en Unsplash.
        
        Diferencias clave vs Pexels:
        - Requiere prefijo "Client-ID" en Authorization
        - Las URLs de imágenes son dinámicas via Unsplash CDN (imgix)
        - Permite pasar ?w=800 para obtener el tamaño exacto
        - Requiere disparar un "download event" al usar la imagen (ver _trigger_download)
        """
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation,
            "content_filter": "high",  # excluye contenido sensible
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{UNSPLASH_BASE}/search/photos",
                headers=self.headers,
                params=params,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

        return [self._parse_photo(p, query) for p in data.get("results", [])]

    def _parse_photo(self, photo: dict, query: str) -> ImageResult:
        urls = photo["urls"]
        user = photo["user"]
        # Las URLs de Unsplash son dinámicas — se pueden parametrizar con ?w=N
        base_url = urls["raw"]
        return ImageResult(
            provider=ImageProvider.unsplash,
            provider_id=photo["id"],
            url_small=f"{base_url}&w=400&fit=crop&auto=format",
            url_medium=f"{base_url}&w=800&fit=crop&auto=format",
            url_large=f"{base_url}&w=1280&fit=crop&auto=format",
            url_original=urls["full"],
            photographer=user["name"],
            photographer_url=user["links"]["html"],
            provider_url=photo["links"]["html"],
            alt_text=photo.get("alt_description", ""),
            width=photo["width"],
            height=photo["height"],
            query_used=query,
        )

    async def trigger_download(self, photo_id: str) -> None:
        """
        Requerido por los términos de Unsplash: disparar este evento
        cuando la imagen se usa (no solo se busca). Llamar en el pipeline
        al confirmar que la imagen fue seleccionada y usada.
        """
        async with httpx.AsyncClient() as client:
            await client.get(
                f"{UNSPLASH_BASE}/photos/{photo_id}/download",
                headers=self.headers,
                timeout=5,
            )
```

**Notas sobre la API de Unsplash:**

La cuenta de demostración permite 50 req/hora — suficiente para desarrollo. Para producción se debe solicitar la "Production Access" en el dashboard de Unsplash (proceso gratuito, aprobación en 1-3 días), que sube a 5,000 req/hora. El requisito más importante de los términos de uso es llamar al endpoint `/photos/{id}/download` cada vez que se usa una imagen — esto se hace en el pipeline al confirmar selección, no en el browser del visitante.

---

## 9. Sistema de caché

```python
# src/images/cache.py

import json
import hashlib
from pathlib import Path
import diskcache

CACHE_DIR = Path(".cache/images_cache")

class ImageCache:
    """
    Caché persistente en disco para resultados de búsqueda de imágenes.
    
    Clave: hash SHA256 de (query + provider + orientation)
    Valor: lista de ImageResult serializados como JSON
    TTL: 30 días (las imágenes de Pexels/Unsplash son estables)
    
    Estrategia:
    - Al buscar: devuelve resultado cacheado si existe y no expiró
    - Al guardar: almacena los N resultados completos (no solo el seleccionado)
      para que el selector pueda elegir sin llamadas adicionales
    - La caché es compartida entre todos los circuitos del pipeline
    """
    TTL_SECONDS = 30 * 24 * 60 * 60  # 30 días

    def __init__(self, cache_dir: Path = CACHE_DIR):
        cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = diskcache.Cache(str(cache_dir))

    def get(self, query: str, provider: str,
            orientation: str = "landscape") -> list[dict] | None:
        key = self._make_key(query, provider, orientation)
        return self._cache.get(key)

    def set(self, query: str, provider: str, results: list[dict],
            orientation: str = "landscape") -> None:
        key = self._make_key(query, provider, orientation)
        self._cache.set(key, results, expire=self.TTL_SECONDS)

    def _make_key(self, query: str, provider: str,
                  orientation: str) -> str:
        raw = f"{query}|{provider}|{orientation}".lower().strip()
        return hashlib.sha256(raw.encode()).hexdigest()

    def stats(self) -> dict:
        return {
            "total_entries": len(self._cache),
            "size_bytes": self._cache.volume(),
        }
```

---

## 10. Selector de imágenes

El selector aplica criterios de calidad para elegir la mejor imagen del pool devuelto por cada API.

```python
# src/images/selector.py

from .models import ImageResult

# Ratio mínimo ancho/alto para aceptar una imagen como "landscape"
MIN_LANDSCAPE_RATIO = 1.2   # 1.2:1 mínimo (ej: 1200x1000 aceptado)
MAX_LANDSCAPE_RATIO = 2.5   # 2.5:1 máximo (evitar panorámicas muy anchas)

# Resolución mínima aceptable para cards web
MIN_WIDTH_MEDIUM = 700      # px — el tamaño "medium" debe tener al menos 700px

def select_best(candidates: list[ImageResult]) -> ImageResult | None:
    """
    Selecciona la mejor imagen de una lista de candidatas.
    
    Criterios aplicados en orden:
    1. Filtra imágenes con ratio de aspecto fuera del rango landscape
    2. Filtra imágenes con resolución insuficiente
    3. De las que quedan, prioriza la primera (APIs ya ordenan por relevancia)
    
    Retorna None si ninguna candidata pasa los filtros.
    """
    valid = []
    for img in candidates:
        ratio = img.width / img.height if img.height > 0 else 0
        if ratio < MIN_LANDSCAPE_RATIO or ratio > MAX_LANDSCAPE_RATIO:
            continue
        if img.width < MIN_WIDTH_MEDIUM:
            continue
        valid.append(img)

    return valid[0] if valid else None


def select_with_fallback(
    pexels_candidates: list[ImageResult],
    unsplash_candidates: list[ImageResult],
) -> tuple[ImageResult | None, str]:
    """
    Intenta Pexels primero, hace fallback a Unsplash si no hay resultado válido.
    Retorna (imagen_seleccionada, proveedor_usado).
    """
    result = select_best(pexels_candidates)
    if result:
        return result, "pexels"

    result = select_best(unsplash_candidates)
    if result:
        return result, "unsplash"

    return None, "none"
```

---

## 11. Entry point — image_fetcher.py

```python
# image_fetcher.py

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.images.pexels_client import PexelsClient
from src.images.unsplash_client import UnsplashClient
from src.images.query_builder import build_query, build_cover_query
from src.images.selector import select_with_fallback
from src.images.cache import ImageCache
from src.images.models import ImageResult, CircuitImages
from src.parser import extract_cities   # reutiliza el parser del pipeline


async def fetch_circuit_images(
    circuit_data: dict,
    pexels_key: str,
    unsplash_key: str,
) -> CircuitImages:
    """
    Función principal. Recibe el dict del JSON del circuito.
    Retorna CircuitImages con cover + una imagen por ciudad.
    
    Uso como módulo desde el pipeline:
        images = await fetch_circuit_images(json_dict, PEXELS_KEY, UNSPLASH_KEY)
        circuit_data["_images"] = images.model_dump()
    """
    pexels = PexelsClient(pexels_key)
    unsplash = UnsplashClient(unsplash_key)
    cache = ImageCache()

    api_calls = 0
    cache_hits = 0
    destinations: dict[str, ImageResult] = {}

    # 1. Imagen de portada
    cover_query = build_cover_query(circuit_data)
    cover, cover_provider, calls, hits = await _fetch_single(
        cover_query, pexels, unsplash, cache
    )
    api_calls += calls
    cache_hits += hits

    # 2. Imagen por ciudad
    cities = extract_cities(circuit_data["itinerario"])
    for city in cities:
        query = build_query(city)
        image, provider, calls, hits = await _fetch_single(
            query, pexels, unsplash, cache
        )
        api_calls += calls
        cache_hits += hits
        if image:
            destinations[city] = image
            # Unsplash requiere disparar download event al usar la imagen
            if provider == "unsplash":
                await unsplash.trigger_download(image.provider_id)

    if not cover:
        # Si no hay imagen de portada, usar la primera de destinos disponible
        cover = next(iter(destinations.values()), None)

    if not cover:
        raise ValueError(f"No se encontró ninguna imagen para el circuito: "
                         f"{circuit_data.get('id', 'desconocido')}")

    return CircuitImages(
        cover=cover,
        destinations=destinations,
        generated_at=datetime.now(timezone.utc).isoformat(),
        cache_hits=cache_hits,
        api_calls=api_calls,
    )


async def _fetch_single(
    query: str,
    pexels: PexelsClient,
    unsplash: UnsplashClient,
    cache: ImageCache,
) -> tuple[ImageResult | None, str, int, int]:
    """
    Busca una imagen para una query dada.
    Retorna (resultado, proveedor, api_calls, cache_hits).
    """
    api_calls = 0
    cache_hits = 0

    # Consultar caché
    pexels_cached = cache.get(query, "pexels")
    unsplash_cached = cache.get(query, "unsplash")

    if pexels_cached and unsplash_cached:
        cache_hits += 2
        pexels_results = [ImageResult(**r) for r in pexels_cached]
        unsplash_results = [ImageResult(**r) for r in unsplash_cached]
        result, provider = select_with_fallback(pexels_results, unsplash_results)
        return result, provider, api_calls, cache_hits

    # Llamadas reales a APIs (concurrentes)
    pexels_task = pexels.search(query) if not pexels_cached else None
    unsplash_task = unsplash.search(query) if not unsplash_cached else None

    if pexels_task and unsplash_task:
        pexels_results, unsplash_results = await asyncio.gather(
            pexels_task, unsplash_task
        )
        api_calls += 2
    elif pexels_task:
        pexels_results = await pexels_task
        unsplash_results = [ImageResult(**r) for r in unsplash_cached]
        api_calls += 1
        cache_hits += 1
    else:
        pexels_results = [ImageResult(**r) for r in pexels_cached]
        unsplash_results = await unsplash_task
        api_calls += 1
        cache_hits += 1

    # Guardar en caché
    if not pexels_cached:
        cache.set(query, "pexels", [r.model_dump() for r in pexels_results])
    if not unsplash_cached:
        cache.set(query, "unsplash", [r.model_dump() for r in unsplash_results])

    result, provider = select_with_fallback(pexels_results, unsplash_results)
    return result, provider, api_calls, cache_hits


def generate_circuit_images(circuit_data: dict,
                             pexels_key: str,
                             unsplash_key: str) -> dict:
    """Wrapper síncrono para uso en pipelines no-async."""
    images = asyncio.run(
        fetch_circuit_images(circuit_data, pexels_key, unsplash_key)
    )
    return images.model_dump()


# ── CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 2:
        print("Uso: python image_fetcher.py circuit.json [output.json]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    circuit_data = json.loads(input_path.read_text())

    pexels_key = os.environ["PEXELS_API_KEY"]
    unsplash_key = os.environ["UNSPLASH_ACCESS_KEY"]

    circuit_data["_images"] = generate_circuit_images(
        circuit_data, pexels_key, unsplash_key
    )

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path
    output_path.write_text(json.dumps(circuit_data, indent=2, ensure_ascii=False))

    images = circuit_data["_images"]
    print(f"[OK] Imágenes resueltas:")
    print(f"     Portada: {images['cover']['url_medium']}")
    print(f"     Destinos: {len(images['destinations'])} ciudades")
    print(f"     API calls: {images['api_calls']} | Cache hits: {images['cache_hits']}")
```

---

## 12. Estructura del bloque `_images` en el JSON enriquecido

Después de ejecutar el módulo, el JSON del circuito contiene el bloque `_images` con esta estructura:

```json
{
  "id": "rajasthan_mumbai",
  "titulo": "Rajastán Imprescindible y Mumbai",
  "_images": {
    "cover": {
      "provider": "pexels",
      "provider_id": "1603650",
      "url_small": "https://images.pexels.com/photos/1603650/pexels-photo-1603650.jpeg?auto=compress&cs=tinysrgb&w=400",
      "url_medium": "https://images.pexels.com/photos/1603650/pexels-photo-1603650.jpeg?auto=compress&cs=tinysrgb&w=800",
      "url_large": "https://images.pexels.com/photos/1603650/pexels-photo-1603650.jpeg?auto=compress&cs=tinysrgb&w=1280",
      "url_original": "https://images.pexels.com/photos/1603650/pexels-photo-1603650.jpeg",
      "photographer": "Sudipta Mondal",
      "photographer_url": "https://www.pexels.com/@sudipta-mondal",
      "provider_url": "https://www.pexels.com/photo/taj-mahal-1603650/",
      "alt_text": "Taj Mahal at sunrise",
      "width": 3648,
      "height": 2736,
      "query_used": "Agra India Taj Mahal travel"
    },
    "destinations": {
      "Delhi": { "...": "..." },
      "Agra": { "...": "..." },
      "Jaipur": { "...": "..." },
      "Udaipur": { "...": "..." },
      "Mumbai": { "...": "..." }
    },
    "generated_at": "2026-03-22T14:35:00Z",
    "cache_hits": 3,
    "api_calls": 7
  }
}
```

---

## 13. Integración con el template WordPress

En el template PHP `single-circuito.php`, la imagen de portada se usa directamente:

```php
<?php
$circuit_data = json_decode(get_field('circuit_json'), true);
$cover = $circuit_data['_images']['cover'] ?? null;
?>

<?php if ($cover): ?>
  <div class="circuit-card-image">
    <img
      src="<?= esc_url($cover['url_medium']) ?>"
      srcset="<?= esc_url($cover['url_small']) ?> 400w,
              <?= esc_url($cover['url_medium']) ?> 800w,
              <?= esc_url($cover['url_large']) ?> 1280w"
      sizes="(max-width: 600px) 400px, (max-width: 1000px) 800px, 1280px"
      alt="<?= esc_attr($cover['alt_text'] ?? $circuit_data['titulo']) ?>"
      loading="lazy"
    >
    <!-- Atribución requerida por Pexels/Unsplash -->
    <span class="photo-credit">
      Foto: <a href="<?= esc_url($cover['photographer_url']) ?>" 
               target="_blank" rel="noopener">
        <?= esc_html($cover['photographer']) ?>
      </a> en 
      <a href="<?= esc_url($cover['provider_url']) ?>" 
         target="_blank" rel="noopener">
        <?= ucfirst($cover['provider']) ?>
      </a>
    </span>
  </div>
<?php endif; ?>
```

---

## 14. Integración con el pipeline completo

```python
# pipeline.py — vista general del flujo completo

import json
import os
from pathlib import Path
from generate_map import generate_circuit_map
from image_fetcher import generate_circuit_images

def run_pipeline(circuit_json_path: str):
    circuit_data = json.loads(Path(circuit_json_path).read_text())

    # Etapa 1 — Imágenes (nueva)
    print("[1/3] Resolviendo imágenes...")
    circuit_data["_images"] = generate_circuit_images(
        circuit_data,
        pexels_key=os.environ["PEXELS_API_KEY"],
        unsplash_key=os.environ["UNSPLASH_ACCESS_KEY"],
    )

    # Etapa 2 — Mapa interactivo HTML (pipeline existente)
    print("[2/3] Generando mapa interactivo...")
    map_html = generate_circuit_map(circuit_data)

    # Etapa 3 — Publicar en WordPress
    print("[3/3] Publicando en WordPress...")
    wp_publish(circuit_data, map_html)

    print(f"[OK] Circuito {circuit_data['id']} publicado.")
```

---

## 15. Configuración

```bash
# .env

# Pexels — registro gratuito en pexels.com/api
PEXELS_API_KEY=your_pexels_api_key_here

# Unsplash — registro gratuito en unsplash.com/developers
# Usar Access Key (no Secret Key) para llamadas desde servidor
UNSPLASH_ACCESS_KEY=your_unsplash_access_key_here

# Orientación por defecto para imágenes de cards
IMAGE_ORIENTATION=landscape

# Número de candidatas a pedir por query (más = mejor selección, más lento)
IMAGE_CANDIDATES_PER_QUERY=5

# Directorio de caché
IMAGE_CACHE_DIR=.cache/images_cache

# TTL del caché en días
IMAGE_CACHE_TTL_DAYS=30
```

---

## 16. Instalación y comandos

```bash
# Añadir dependencias al pyproject.toml existente
uv add httpx diskcache python-dotenv

# Probar con un circuito de ejemplo
uv run python image_fetcher.py data/rajasthan_mumbai.json

# Ver estadísticas de caché
uv run python -c "
from src.images.cache import ImageCache
c = ImageCache()
print(c.stats())
"

# Tests
uv run pytest tests/test_pexels_client.py
uv run pytest tests/test_unsplash_client.py
```

---

## 17. Criterios de aceptación

| ID | Escenario | Criterio |
|---|---|---|
| CA-01 | Circuito con 5 ciudades conocidas | El módulo devuelve 5 imágenes de destinos + 1 portada en < 10s |
| CA-02 | Segunda ejecución del mismo circuito | 0 llamadas a API — todo desde caché |
| CA-03 | Ciudad no mapeada en DESTINATION_QUERY_MAP | Se usa query dinámica y se obtiene resultado válido |
| CA-04 | Pexels devuelve 0 resultados válidos | Fallback a Unsplash sin error ni interrupción del pipeline |
| CA-05 | Ambas APIs sin resultados | El pipeline registra warning y continúa — sin romper |
| CA-06 | Imagen usada de Unsplash | El endpoint `/download` se dispara en background |
| CA-07 | URL de imagen en HTML | Usa `url_medium` para cards y `url_large` para hero |
| CA-08 | Atribución | `photographer` y `photographer_url` están presentes en el JSON |
| CA-09 | Rate limit alcanzado | Se registra el error, se usa caché o se omite la imagen |
| CA-10 | Orientación landscape | Todas las imágenes seleccionadas tienen ratio ≥ 1.2 |

---

## 18. Notas legales de uso

**Pexels:** Las imágenes son gratuitas para uso comercial. No requiere atribución obligatoria pero es altamente recomendada. No se puede vender ni redistribuir las imágenes como stock. La API es gratuita y no requiere aprobación manual.

**Unsplash:** Las imágenes son gratuitas para uso comercial bajo la Unsplash License. Requiere disparar el evento de descarga via API cuando se usa una imagen (implementado en `trigger_download`). Para producción (>50 req/hora) se requiere solicitar Production Access en el dashboard — proceso gratuito y aprobación típica en 1-3 días hábiles.

En ambos casos, incluir el bloque de atribución en el HTML del template WordPress (implementado en la sección 13) es la práctica recomendada y protege de cualquier disputa futura.
