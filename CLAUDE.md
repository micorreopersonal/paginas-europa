# Europamundo PDF Processor

Pipeline automatizado para extraer datos de catálogos PDF de Europamundo y publicar páginas en WordPress.

## Pipeline

```
PDF → Etapa 1 (imágenes) → Etapa 2 (JSON via Claude Vision) → Etapa 3 (HTML + mapas) → Etapa 4 (WordPress)
```

## Uso rápido

```bash
# Procesar un PDF completo (etapas 1-3)
python procesar_pdf.py catalogo.pdf

# Procesar y publicar en WordPress
python procesar_pdf.py catalogo.pdf --etapas 1,2,3,4

# Solo extraer imágenes
python procesar_pdf.py catalogo.pdf --etapas 1

# Probar con pocos programas
python procesar_pdf.py catalogo.pdf --test 3
```

## Scripts individuales

```bash
python etapa1_extraer_programas.py <pdf>          # PDF → imágenes por programa
python etapa2_extraer_datos.py <pdf> [--test N]   # Imágenes → JSON (Claude Vision)
python etapa3_generar_html.py <pdf>               # JSON → HTML local + mapas
python etapa4_publicar_wordpress.py <pdf>          # JSON → WordPress páginas (draft)
```

## Configuración

Copiar `.env.example` a `.env` y llenar:

- `ANTHROPIC_API_KEY` — API key de Anthropic (console.anthropic.com)
- `WP_URL` — URL del sitio WordPress (solo etapa 4)
- `WP_USER` — Usuario de WordPress (solo etapa 4)
- `WP_APP_PASSWORD` — Application Password de WordPress (solo etapa 4)

### Crear Application Password en WordPress

1. wp-admin > Usuarios > Tu perfil
2. Sección "Contraseñas de aplicación"
3. Nombre: "script-europamundo" > Agregar
4. Copiar la contraseña generada al .env

## Dependencias

```bash
pip install PyMuPDF Pillow anthropic python-dotenv requests
```

## Estructura del PDF esperada

- Páginas 1-2: Índice (ID, nombre viaje, página)
- Páginas 3+: Programas de viaje separados por barra dorada "Fechas de Salida"
- Cada programa: título, precio, días, itinerario, mapa, sección "incluye"

## Output

```
output/<nombre-pdf>/
├── programa_001_pag03.png    # Imágenes recortadas por programa
├── programa_002_pag03.png
├── programas.json            # Datos estructurados
├── html/
│   ├── assets/               # Mapas extraídos del PDF
│   └── *.html                # Páginas HTML locales
└── wordpress_log.json        # Log de publicación WP
```

## Costos estimados (API Claude)

- ~$0.03 por programa (Sonnet, input+output)
- PDF típico de 50 programas: ~$1.50 USD
