# Europamundo PDF → WordPress Pipeline

Automatiza la extracción de programas turísticos desde catálogos PDF de Europamundo
y los publica como circuitos en WordPress con mapa interactivo, SEO optimizado e
imágenes de portada.

## Arquitectura

```
input/catalogo.pdf
    │
    ├── [1] etapa1_extraer_programas.py  → imágenes por programa
    ├── [2] etapa2_extraer_datos.py      → programas.json (LLM Vision)
    ├── [3] generate_seo.py             → enriquece JSON con SEO
    ├── [4] fetch_images.py             → agrega imágenes Pexels
    ├── [5] generate_map.py             → mapas interactivos MapLibre
    └── [6] etapa4_publicar_wordpress.py → publica en WordPress
                                            ↓
                                    paqueteseuropa.com/circuitos/{slug}/
```

## Uso rápido

```bash
# Instalar dependencias
pip install -r requirements.txt

# Procesar PDF completo (etapas 1-5, sin publicar)
python procesar_pdf.py input/catalogo.pdf

# Procesar y publicar en WordPress
python procesar_pdf.py input/catalogo.pdf --etapas 1,2,3,4,5,6

# Solo publicar (si ya se procesó antes)
python procesar_pdf.py input/catalogo.pdf --etapas 6 --status publish

# Probar con pocos programas
python procesar_pdf.py input/catalogo.pdf --test 3

# Tests de regresión
python test_pipeline.py
```

## Estructura del proyecto

```
procesar-paginas-europamundo/
├── procesar_pdf.py              # Orquestador del pipeline
├── llm_client.py                # Wrapper multi-LLM (Claude/Gemini)
│
├── etapa1_extraer_programas.py  # PDF → imágenes (detección barra dorada)
├── etapa2_extraer_datos.py      # Imágenes → JSON (LLM Vision)
├── generate_seo.py              # JSON → SEO (keywords, intro, CTA)
├── fetch_images.py              # JSON → imágenes Pexels
├── generate_map.py              # JSON → mapa interactivo HTML
├── etapa4_publicar_wordpress.py # JSON → WordPress (CPT + SEO + mapa)
│
├── templates/
│   └── circuit_map.html.j2      # Template Jinja2 del mapa MapLibre
│
├── wordpress/
│   └── europamundo-circuitos.php # Plugin WP: CPT, taxonomías, menú, shortcode
│
├── specs/                        # Especificaciones funcionales/técnicas
├── input/                        # PDFs a procesar (gitignore)
├── output/                       # Resultados generados (gitignore)
├── .cache/                       # Caché geocoding + imágenes (gitignore)
│
├── test_pipeline.py              # Tests de regresión
├── requirements.txt
├── .env.example
└── CLAUDE.md
```

## Configuración (.env)

| Variable | Uso | Requerido |
|---|---|---|
| LLM_PROVIDER | "claude" o "gemini" | Sí |
| ANTHROPIC_API_KEY | Claude API | Si provider=claude |
| GOOGLE_API_KEY | Gemini API | Si provider=gemini |
| WP_URL | URL WordPress | Solo etapa 6 |
| WP_USER | Usuario WP | Solo etapa 6 |
| WP_APP_PASSWORD | App Password WP | Solo etapa 6 |
| MAPTILER_API_KEY | Tiles del mapa | Sí |
| PEXELS_API_KEY | Imágenes portada | Sí |

## WordPress

- **CPT:** "circuito" (slug: /circuitos/)
- **Taxonomías:** region_europamundo, serie_europamundo
- **Plugin:** wordpress/europamundo-circuitos.php
- **Shortcode:** `[europamundo_circuitos region="india-y-oceania"]`
- **SEO:** Rank Math con endpoint custom `/europamundo/v1/seo/{id}`
- **Publicar como:** draft por defecto, publish con --status publish

## Costos por programa

| Componente | Claude Haiku | Gemini Flash |
|---|---|---|
| Extracción datos (etapa 2) | ~$0.008 | ~$0.002 |
| SEO (etapa 3) | ~$0.005 | ~$0.001 |
| Pexels (etapa 4) | Gratis | Gratis |
| OSRM routing (etapa 5) | Gratis | Gratis |
| **Total por programa** | **~$0.013** | **~$0.003** |
| **500 programas** | **~$6.50** | **~$1.50** |
