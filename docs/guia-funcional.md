# Guía Funcional — Europamundo PDF to WordPress Pipeline

> **Gina Travel — Paquetes Europa**
> Sistema automatizado de publicación de circuitos turísticos
> Versión 1.0 — Marzo 2026

---

## 1. Visión General

Este sistema transforma catálogos PDF de **Europamundo Vacaciones** en páginas web publicadas automáticamente en WordPress, con mapa interactivo, contenido SEO optimizado e imágenes de portada.

```mermaid
graph LR
    A["📄 PDF Europamundo"] --> B["🤖 Pipeline Automatizado"]
    B --> C["🌐 WordPress"]
    C --> D["👤 Cliente Final"]

    style A fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#1565c0
    style B fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#e65100
    style C fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#2e7d32
    style D fill:#fce4ec,stroke:#c62828,stroke-width:2px,color:#c62828
```

### El problema que resuelve

| Antes (manual) | Después (automatizado) |
|---|---|
| Copiar datos del PDF uno por uno | Un comando procesa todo el catálogo |
| Crear página en WordPress manualmente | Páginas se publican automáticamente |
| Buscar y subir imágenes manualmente | Imágenes se obtienen de Pexels automáticamente |
| SEO básico o inexistente | SEO 79/100 generado por IA |
| Mapa como imagen estática | Mapa interactivo con navegación por días |
| ~2 horas por circuito | ~30 segundos por circuito |

---

## 2. Arquitectura del Pipeline

```mermaid
flowchart TB
    subgraph INPUT["📥 ENTRADA"]
        PDF["📄 PDF Catálogo<br/>Europamundo"]
    end

    subgraph PIPELINE["⚙️ PIPELINE DE PROCESAMIENTO"]
        direction TB
        E1["1️⃣ Extraer Programas<br/><i>Detección barra dorada</i><br/><i>PyMuPDF + Pillow</i>"]
        E2["2️⃣ Extraer Datos<br/><i>LLM Vision (Claude/Gemini)</i><br/><i>JSON estructurado</i>"]
        E3["3️⃣ Generar SEO<br/><i>Keywords, intro, CTA</i><br/><i>Rank Math optimizado</i>"]
        E4["4️⃣ Obtener Imágenes<br/><i>Pexels API</i><br/><i>Portada automática</i>"]
        E5["5️⃣ Generar Mapas<br/><i>MapLibre + OSRM</i><br/><i>Rutas reales interactivas</i>"]
        E6["6️⃣ Publicar WordPress<br/><i>REST API + CPT</i><br/><i>Taxonomías + SEO meta</i>"]

        E1 --> E2 --> E3 --> E4 --> E5 --> E6
    end

    subgraph OUTPUT["📤 SALIDA"]
        WP["🌐 WordPress<br/>paqueteseuropa.com"]
        PAGE["📄 Página del Circuito<br/>/circuitos/india-fascinante/"]
        CARD["🃏 Cards en Shortcode<br/>[europamundo_circuitos]"]
    end

    PDF --> E1
    E6 --> WP
    WP --> PAGE
    WP --> CARD

    style INPUT fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style PIPELINE fill:#fff8e1,stroke:#f9a825,stroke-width:2px
    style OUTPUT fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style E1 fill:#bbdefb,stroke:#1565c0
    style E2 fill:#c8e6c9,stroke:#2e7d32
    style E3 fill:#ffe0b2,stroke:#e65100
    style E4 fill:#f8bbd0,stroke:#c62828
    style E5 fill:#b3e5fc,stroke:#0277bd
    style E6 fill:#d1c4e9,stroke:#4527a0
```

---

## 3. Detalle de cada Etapa

### Etapa 1 — Extraer Programas del PDF

```mermaid
flowchart LR
    PDF["📄 PDF<br/>28 páginas"] --> DETECT["🔍 Detectar<br/>barra dorada<br/>RGB(159,110,0)"]
    DETECT --> CROP["✂️ Recortar<br/>cada programa"]
    CROP --> IMGS["🖼️ 42 imágenes<br/>programa_001.png<br/>programa_002.png<br/>..."]

    style PDF fill:#e3f2fd,stroke:#1565c0
    style DETECT fill:#fff3e0,stroke:#e65100
    style CROP fill:#fff3e0,stroke:#e65100
    style IMGS fill:#e8f5e9,stroke:#2e7d32
```

**¿Qué hace?** Lee el PDF página por página, detecta la barra dorada "Fechas de Salida" como separador visual, y recorta cada programa como imagen individual.

**Tecnología:** PyMuPDF (renderizado), NumPy (detección color), Pillow (recorte)

---

### Etapa 2 — Extraer Datos con IA

```mermaid
flowchart LR
    IMG["🖼️ Imagen<br/>del programa"] --> LLM["🤖 LLM Vision<br/>Claude Haiku /<br/>Gemini Flash"]
    LLM --> JSON["📋 JSON<br/>estructurado"]

    subgraph JSON_CONTENT["Datos Extraídos"]
        direction TB
        T["Título"]
        P["Precio"]
        D["Días"]
        I["Itinerario día a día"]
        INC["Servicios incluidos"]
    end

    JSON --> JSON_CONTENT

    style IMG fill:#e3f2fd,stroke:#1565c0
    style LLM fill:#c8e6c9,stroke:#2e7d32
    style JSON fill:#e8f5e9,stroke:#2e7d32
    style JSON_CONTENT fill:#f5f5f5,stroke:#9e9e9e
```

**¿Qué hace?** Envía cada imagen a un modelo de IA con visión que lee todos los datos del programa y los estructura en JSON.

**Proveedores soportados:**

| Provider | Modelo | Costo/programa | Config |
|---|---|---|---|
| Claude | Haiku 4.5 | ~$0.008 | `LLM_PROVIDER=claude` |
| Gemini | Flash 2.5 | ~$0.002 | `LLM_PROVIDER=gemini` |

---

### Etapa 3 — Generar Contenido SEO

```mermaid
flowchart LR
    JSON["📋 JSON del<br/>programa"] --> LLM["🤖 LLM<br/>Text"]
    LLM --> SEO["📝 Contenido SEO"]

    subgraph SEO_CONTENT["SEO Generado"]
        direction TB
        KW["🔑 Focus Keyword<br/><i>India Fascinante</i>"]
        TI["📰 SEO Title<br/><i>India Fascinante: Descubre 11 Días...</i>"]
        MD["📝 Meta Description<br/><i>155 chars optimizados</i>"]
        IN["📖 Intro<br/><i>80-120 palabras con keyword</i>"]
        HL["⭐ Highlights<br/><i>Experiencias destacadas</i>"]
        CT["📢 CTA<br/><i>Llamada a acción</i>"]
    end

    SEO --> SEO_CONTENT

    style JSON fill:#e3f2fd,stroke:#1565c0
    style LLM fill:#ffe0b2,stroke:#e65100
    style SEO fill:#fff3e0,stroke:#e65100
    style SEO_CONTENT fill:#f5f5f5,stroke:#9e9e9e
```

**Score SEO alcanzado:** 79/100 en Rank Math (de 11/100 sin SEO)

**Optimizaciones automáticas:**
- Keyword en título, URL, meta description, contenido, headings
- Power words y sentiment words en el título
- Links internos y externos (dofollow)
- Keyword density óptima

---

### Etapa 4 — Obtener Imágenes

```mermaid
flowchart LR
    CITIES["🏙️ Ciudades<br/>del programa"] --> QUERY["🔍 Query<br/><i>Delhi India Red Fort travel</i>"]
    QUERY --> PEXELS["📸 Pexels API<br/>landscape, HD"]
    PEXELS --> IMG["🖼️ Imagen<br/>de portada"]
    CACHE["💾 Caché local"] -.-> PEXELS

    style CITIES fill:#e3f2fd,stroke:#1565c0
    style QUERY fill:#fff3e0,stroke:#e65100
    style PEXELS fill:#f8bbd0,stroke:#c62828
    style IMG fill:#e8f5e9,stroke:#2e7d32
    style CACHE fill:#f5f5f5,stroke:#9e9e9e
```

**¿Qué hace?** Busca una imagen profesional de la primera ciudad del circuito en Pexels (gratuito, sin atribución obligatoria). Usa caché para no repetir búsquedas.

---

### Etapa 5 — Generar Mapa Interactivo

```mermaid
flowchart LR
    CITIES["🏙️ Ciudades"] --> GEO["📍 Geocodificar<br/>Nominatim"]
    GEO --> ROUTE["🛣️ Calcular Rutas<br/>OSRM (carretera)<br/>Great Circle (vuelo)"]
    ROUTE --> MAP["🗺️ HTML<br/>MapLibre GL JS"]

    subgraph MAP_FEATURES["Funcionalidades del Mapa"]
        direction TB
        M1["📍 Marcadores con noches"]
        M2["🛣️ Rutas por carretera real"]
        M3["✈️ Arcos de vuelo"]
        M4["📅 Navegación por días"]
        M5["📋 Panel de información"]
        M6["🍽️ Chips almuerzo/cena/vuelo"]
    end

    MAP --> MAP_FEATURES

    style CITIES fill:#e3f2fd,stroke:#1565c0
    style GEO fill:#b3e5fc,stroke:#0277bd
    style ROUTE fill:#b3e5fc,stroke:#0277bd
    style MAP fill:#e8f5e9,stroke:#2e7d32
    style MAP_FEATURES fill:#f5f5f5,stroke:#9e9e9e
```

**Componente self-contained:** El mapa se genera como HTML embebible que funciona sin servidor adicional. Los datos (coordenadas, rutas, itinerario) están inlineados como variables JavaScript.

---

### Etapa 6 — Publicar en WordPress

```mermaid
flowchart TB
    JSON["📋 JSON<br/>enriquecido"] --> WP_API["🔌 WordPress<br/>REST API"]

    WP_API --> CPT["📝 CPT Circuito<br/>/circuitos/{slug}/"]
    WP_API --> TAX["🏷️ Taxonomías<br/>Región + Serie"]
    WP_API --> IMG["🖼️ Featured Image<br/>Media Library"]
    WP_API --> SEO_META["🔍 Rank Math Meta<br/>Endpoint custom"]

    subgraph WP_CONTENT["Contenido de la Página"]
        direction TB
        C1["📖 Intro SEO"]
        C2["🗺️ Mapa Interactivo"]
        C3["📊 Resumen (días, precio)"]
        C4["⭐ Highlights"]
        C5["📅 Itinerario día a día"]
        C6["✅ Servicios incluidos"]
        C7["📢 CTA + Links"]
    end

    CPT --> WP_CONTENT

    style JSON fill:#e3f2fd,stroke:#1565c0
    style WP_API fill:#d1c4e9,stroke:#4527a0
    style CPT fill:#e8f5e9,stroke:#2e7d32
    style TAX fill:#fff3e0,stroke:#e65100
    style IMG fill:#f8bbd0,stroke:#c62828
    style SEO_META fill:#ffe0b2,stroke:#e65100
    style WP_CONTENT fill:#f5f5f5,stroke:#9e9e9e
```

---

## 4. Estructura de WordPress

```mermaid
graph TB
    subgraph MENU["🔽 Menú Principal"]
        SR["Salidas Regulares"]
        SR --> EM["Circuitos Europamundo"]
        EM --> R1["China, Corea y Japón"]
        EM --> R2["Europa Atlántica"]
        EM --> R3["Europa Central"]
        EM --> R4["Europa Mediterránea"]
        EM --> R5["Europa Nórdica"]
        EM --> R6["India y Oceanía"]
        EM --> R7["México y Cuba"]
        EM --> R8["Oriente Medio y África"]
        EM --> R9["Península Ibérica y Marruecos"]
        EM --> R10["USA y Canadá"]
    end

    subgraph CPT["📝 Custom Post Type"]
        CIRC["Circuito"]
        CIRC --- REG["🏷️ Región"]
        CIRC --- SER["🏷️ Serie"]
        CIRC --- META["📊 Meta Fields:<br/>precio, días, fechas, ID"]
    end

    subgraph SHORT["🃏 Shortcode Cards"]
        SC1["[europamundo_circuitos]"]
        SC2["[europamundo_circuitos region='india-y-oceania']"]
        SC3["[europamundo_circuitos max_dias='15']"]
    end

    style MENU fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    style CPT fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    style SHORT fill:#fff3e0,stroke:#e65100,stroke-width:2px
```

---

## 5. Pasos de Uso — Guía del Operador

### Primera vez (setup)

```mermaid
flowchart TB
    S1["1. Clonar repositorio<br/><code>git clone repo</code>"] --> S2["2. Instalar dependencias<br/><code>pip install -r requirements.txt</code>"]
    S2 --> S3["3. Copiar .env.example → .env<br/>Llenar API keys"]
    S3 --> S4["4. Instalar plugin WordPress<br/>Subir europamundo-circuitos.php<br/>a wp-content/plugins/"]
    S4 --> S5["5. Activar plugin en wp-admin<br/>Verifica: menú Circuitos visible"]
    S5 --> S6["✅ Listo para procesar PDFs"]

    style S1 fill:#e3f2fd,stroke:#1565c0
    style S2 fill:#e3f2fd,stroke:#1565c0
    style S3 fill:#fff3e0,stroke:#e65100
    style S4 fill:#e8f5e9,stroke:#2e7d32
    style S5 fill:#e8f5e9,stroke:#2e7d32
    style S6 fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
```

### Procesar un nuevo catálogo PDF

```mermaid
flowchart TB
    P1["📥 <b>Paso 1:</b> Descargar PDF<br/>desde europamundo.com/catalogo.aspx<br/>Elegir versión en dólares"] --> P2["📁 <b>Paso 2:</b> Colocar PDF<br/>en la carpeta <code>input/</code>"]
    P2 --> P3{"¿Primera vez<br/>con este PDF?"}
    P3 -->|Sí| P4["⚙️ <b>Paso 3:</b> Probar con pocos<br/><code>python procesar_pdf.py input/catalogo.pdf --test 3</code>"]
    P3 -->|No, ya probé| P5

    P4 --> P4b["👀 <b>Paso 4:</b> Revisar output/<br/>Abrir mapas HTML en navegador<br/>Verificar datos en programas.json"]
    P4b --> P4c{"¿Se ve bien?"}
    P4c -->|Sí| P5
    P4c -->|No| P4d["🔧 Ajustar y re-procesar"]
    P4d --> P4

    P5["🚀 <b>Paso 5:</b> Procesar completo<br/><code>python procesar_pdf.py input/catalogo.pdf</code>"] --> P6["📤 <b>Paso 6:</b> Publicar en WordPress<br/><code>python procesar_pdf.py input/catalogo.pdf --etapas 6</code>"]

    P6 --> P7["✅ <b>Paso 7:</b> Verificar en wp-admin<br/>Circuitos → Todos los Circuitos<br/>Revisar borradores, previsualizar"]
    P7 --> P8{"¿Publicar?"}
    P8 -->|Sí| P9["📢 Cambiar estado a <i>publish</i><br/>desde wp-admin o re-ejecutar<br/>con <code>--status publish</code>"]
    P8 -->|Ajustar| P10["✏️ Editar en wp-admin<br/>Ajustar texto, imágenes, SEO"]

    style P1 fill:#e3f2fd,stroke:#1565c0
    style P2 fill:#e3f2fd,stroke:#1565c0
    style P3 fill:#fff3e0,stroke:#e65100
    style P4 fill:#fff3e0,stroke:#e65100
    style P4b fill:#fff3e0,stroke:#e65100
    style P5 fill:#c8e6c9,stroke:#2e7d32
    style P6 fill:#d1c4e9,stroke:#4527a0
    style P7 fill:#e8f5e9,stroke:#2e7d32
    style P9 fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
```

### Paso a paso detallado

| # | Acción | Comando / Ubicación | Resultado |
|---|---|---|---|
| 1 | **Descargar PDF** | europamundo.com/catalogo.aspx → versión dólares | `usa-canada-2025-2027.pdf` |
| 2 | **Colocar en input/** | Copiar PDF a `input/` | `input/usa-canada-2025-2027.pdf` |
| 3 | **Probar (opcional)** | `python procesar_pdf.py input/usa-canada-2025-2027.pdf --test 3` | 3 programas procesados |
| 4 | **Revisar output** | Abrir `output/usa-canada-2025-2027/maps/*.html` en navegador | Mapas interactivos visibles |
| 5 | **Procesar completo** | `python procesar_pdf.py input/usa-canada-2025-2027.pdf` | ~42 programas procesados |
| 6 | **Publicar** | `python procesar_pdf.py input/usa-canada-2025-2027.pdf --etapas 6` | Circuitos como borradores en WP |
| 7 | **Verificar** | wp-admin → Circuitos → filtrar por región "USA y Canadá" | Revisar contenido y SEO |
| 8 | **Aprobar** | Cambiar estado a "Publicado" en wp-admin | Páginas live en el sitio |

### Después de procesar

- El PDF se **mueve automáticamente** a `input/procesados/`
- Los datos quedan en `output/{nombre-pdf}/programas.json`
- Los mapas HTML quedan en `output/{nombre-pdf}/maps/`
- El caché de geocoding y imágenes se comparte entre ejecuciones

### Procesamiento por lotes (todos los catálogos)

```bash
# Descargar todos los PDFs a input/
# Luego ejecutar uno por uno:

python procesar_pdf.py input/usa-canada-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/mexico-cuba-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/china-japon-y-corea-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/sudeste-india-y-oceania-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/oriente-medio-africa-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/peninsula-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/mediterranea-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/atlantica-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/nordica-2025-2027.pdf --etapas 1,2,3,4,5,6
python procesar_pdf.py input/central-2025-2027.pdf --etapas 1,2,3,4,5,6
```

### Troubleshooting

| Problema | Causa | Solución |
|---|---|---|
| "No se encontró el archivo" | PDF no está en input/ | Verificar ruta |
| "Error de autenticación" | API key inválida o WP credentials | Revisar .env |
| Ciudad no geocodificada | Nombre con typo del OCR | Se omite automáticamente, no bloquea |
| OSRM falla | Servicio público caído | Usa línea recta como fallback |
| JSON malformado (Gemini) | Gemini a veces corta respuestas | Cambiar a `LLM_PROVIDER=claude` |
| SEO score bajo | Keywords no coinciden con slug | Regenerar SEO con etapa 3 |
| Menú WP sin texto | Caché del navegador | Ctrl+Shift+R para limpiar |

---

## 6. Flujo Técnico Detallado

```mermaid
sequenceDiagram
    actor User as 👤 Operador
    participant IN as 📥 input/
    participant PY as ⚙️ procesar_pdf.py
    participant LLM as 🤖 Claude/Gemini
    participant PX as 📸 Pexels
    participant OSRM as 🛣️ OSRM
    participant WP as 🌐 WordPress
    participant OUT as 📤 output/

    User->>IN: Colocar PDF en input/
    User->>PY: python procesar_pdf.py input/catalogo.pdf

    Note over PY: Etapa 1: Extraer imágenes
    PY->>OUT: programa_001.png ... programa_042.png

    Note over PY: Etapa 2: Extraer datos
    PY->>LLM: Enviar imágenes
    LLM-->>PY: JSON estructurado
    PY->>OUT: programas.json

    Note over PY: Etapa 3: SEO
    PY->>LLM: Generar keywords + intro
    LLM-->>PY: Contenido SEO

    Note over PY: Etapa 4: Imágenes
    PY->>PX: Buscar fotos por ciudad
    PX-->>PY: URLs de imágenes HD

    Note over PY: Etapa 5: Mapas
    PY->>OSRM: Calcular rutas
    OSRM-->>PY: GeoJSON rutas
    PY->>OUT: mapas HTML interactivos

    Note over PY: Etapa 6: Publicar
    PY->>WP: Crear circuitos (REST API)
    WP-->>PY: URLs publicadas

    PY->>IN: Mover PDF a procesados/
    PY-->>User: ✅ 42 circuitos publicados
```

---

## 6. Estructura del Proyecto

```mermaid
graph TB
    subgraph ROOT["📁 procesar-paginas-europamundo/"]
        MAIN["procesar_pdf.py<br/><i>Entry point</i>"]
        REQ["requirements.txt"]
        ENV[".env"]
        CLAUDE["CLAUDE.md"]

        subgraph SCRIPTS["📁 scripts/"]
            S1["llm_client.py"]
            S2["etapa1_extraer_programas.py"]
            S3["etapa2_extraer_datos.py"]
            S4["generate_seo.py"]
            S5["fetch_images.py"]
            S6["generate_map.py"]
            S7["etapa4_publicar_wordpress.py"]
        end

        subgraph TEMPLATES["📁 templates/"]
            T1["circuit_map.html.j2"]
        end

        subgraph WP["📁 wordpress/"]
            W1["europamundo-circuitos.php"]
        end

        subgraph TESTS["📁 tests/"]
            TS1["test_pipeline.py"]
        end

        subgraph IO["📁 I/O"]
            INPUT["📁 input/<br/>PDFs nuevos"]
            PROC["📁 input/procesados/<br/>PDFs procesados"]
            OUTPUT["📁 output/{pdf-name}/<br/>programas.json<br/>maps/"]
        end
    end

    style ROOT fill:#fafafa,stroke:#424242,stroke-width:2px
    style SCRIPTS fill:#e3f2fd,stroke:#1565c0
    style TEMPLATES fill:#fff3e0,stroke:#e65100
    style WP fill:#e8f5e9,stroke:#2e7d32
    style TESTS fill:#fce4ec,stroke:#c62828
    style IO fill:#f3e5f5,stroke:#7b1fa2
```

---

## 7. Costos Operativos

```mermaid
pie title Costo por Programa (~$0.013 USD con Claude Haiku)
    "Extracción datos (LLM)" : 62
    "Generación SEO (LLM)" : 38
    "Pexels (imágenes)" : 0
    "OSRM (rutas)" : 0
    "MapTiler (tiles)" : 0
```

| Escenario | Claude Haiku | Gemini Flash |
|---|---|---|
| 1 PDF (~42 programas) | **$0.55** | **$0.13** |
| 5 PDFs (~250 programas) | **$3.25** | **$0.75** |
| Todos los catálogos (~800) | **$10.40** | **$2.40** |

---

## 8. Comandos de Referencia

```bash
# ══════════════════════════════════════════
# PROCESAMIENTO
# ══════════════════════════════════════════

# Pipeline completo (sin publicar)
python procesar_pdf.py input/catalogo.pdf

# Pipeline completo + publicar en WordPress
python procesar_pdf.py input/catalogo.pdf --etapas 1,2,3,4,5,6

# Publicar como publicado (no borrador)
python procesar_pdf.py input/catalogo.pdf --etapas 1,2,3,4,5,6 --status publish

# Solo procesar 3 programas (prueba)
python procesar_pdf.py input/catalogo.pdf --test 3

# Solo publicar (ya procesado antes)
python procesar_pdf.py input/catalogo.pdf --etapas 6

# ══════════════════════════════════════════
# TESTS
# ══════════════════════════════════════════

# Tests de regresión
python tests/test_pipeline.py

# ══════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════

# Cambiar a Gemini (más barato)
# En .env: LLM_PROVIDER=gemini

# Cambiar a Claude (más confiable)
# En .env: LLM_PROVIDER=claude
```

---

## 9. Requisitos

### Software
- Python 3.11+
- WordPress 6.x con plugin `europamundo-circuitos.php` activo

### APIs (gratuitas o de bajo costo)
- **Anthropic** o **Google AI Studio** — Para extracción y SEO
- **Pexels** — Imágenes (gratis, ilimitado)
- **MapTiler** — Tiles de mapa (gratis hasta 100K/mes)
- **OSRM** — Rutas por carretera (gratis, público)
- **Nominatim** — Geocodificación (gratis, fair use)

### WordPress Plugins
- Rank Math SEO (Free)
- Elementor (Free) — para páginas landing
- Plugin custom: `europamundo-circuitos.php`

---

> **Desarrollado con** Claude Code + Claude Opus 4.6
> **Para** Gina Travel — Paquetes Europa
> **Marzo 2026**
