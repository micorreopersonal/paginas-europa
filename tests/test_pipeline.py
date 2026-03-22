"""
Tests de regresión para el pipeline Europamundo PDF → WordPress.

Valida que todos los componentes funcionan correctamente sin ejecutar
llamadas reales a APIs externas (usa datos de prueba existentes).

Uso:
    python tests/test_pipeline.py      (desde raíz del proyecto)
    python -m tests.test_pipeline      (como módulo)
"""

import json
import os
import sys
import importlib

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, "scripts")
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, SCRIPTS_DIR)

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

passed = 0
failed = 0
warnings = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  {GREEN}✓{RESET} {name}")
        passed += 1
    else:
        print(f"  {RED}✗{RESET} {name} — {detail}")
        failed += 1


def warn(name, detail=""):
    global warnings
    print(f"  {YELLOW}⚠{RESET} {name} — {detail}")
    warnings += 1


def find_test_json():
    """Busca un programas.json existente para tests."""
    for root, dirs, files in os.walk(os.path.join(PROJECT_ROOT, "output")):
        if "programas.json" in files:
            return os.path.join(root, "programas.json")
    return None


# ══════════════════════════════════════════════════════
# 1. ESTRUCTURA DEL PROYECTO
# ══════════════════════════════════════════════════════
print("\n1. Estructura del proyecto")

required_files = [
    "procesar_pdf.py",
    "scripts/__init__.py",
    "scripts/llm_client.py",
    "scripts/etapa1_extraer_programas.py",
    "scripts/etapa2_extraer_datos.py",
    "scripts/generate_seo.py",
    "scripts/fetch_images.py",
    "scripts/generate_map.py",
    "scripts/etapa4_publicar_wordpress.py",
    "templates/circuit_map.html.j2",
    "wordpress/europamundo-circuitos.php",
    "tests/test_pipeline.py",
    "requirements.txt",
    ".env.example",
    "CLAUDE.md",
]

for f in required_files:
    path = os.path.join(PROJECT_ROOT, f)
    test(f"Archivo: {f}", os.path.exists(path), "NO ENCONTRADO")

required_dirs = ["input", "scripts", "templates", "tests", "wordpress", "specs"]
for d in required_dirs:
    path = os.path.join(PROJECT_ROOT, d)
    test(f"Carpeta: {d}/", os.path.isdir(path), "NO ENCONTRADA")


# ══════════════════════════════════════════════════════
# 2. DEPENDENCIAS
# ══════════════════════════════════════════════════════
print("\n2. Dependencias Python")

deps = {
    "fitz": "PyMuPDF",
    "PIL": "Pillow",
    "anthropic": "anthropic",
    "google.generativeai": "google-generativeai",
    "dotenv": "python-dotenv",
    "requests": "requests",
    "geopy": "geopy",
    "jinja2": "Jinja2",
}

for module, package in deps.items():
    try:
        importlib.import_module(module)
        test(f"Importar: {package}", True)
    except ImportError:
        test(f"Importar: {package}", False, f"pip install {package}")


# ══════════════════════════════════════════════════════
# 3. CONFIGURACIÓN
# ══════════════════════════════════════════════════════
print("\n3. Configuración (.env)")

from dotenv import load_dotenv
load_dotenv()

env_vars = {
    "LLM_PROVIDER": ("claude", "gemini"),
    "MAPTILER_API_KEY": None,
    "PEXELS_API_KEY": None,
}

for var, valid_values in env_vars.items():
    val = os.getenv(var, "")
    if valid_values:
        test(f"{var} = {val}", val in valid_values, f"Debe ser uno de: {valid_values}")
    else:
        test(f"{var} configurado", bool(val) and "tu-" not in val, "Falta configurar en .env")

# API key del provider seleccionado
provider = os.getenv("LLM_PROVIDER", "claude")
if provider == "claude":
    test("ANTHROPIC_API_KEY configurada", bool(os.getenv("ANTHROPIC_API_KEY", "")), "Requerida para LLM_PROVIDER=claude")
else:
    test("GOOGLE_API_KEY configurada", bool(os.getenv("GOOGLE_API_KEY", "")), "Requerida para LLM_PROVIDER=gemini")

# WordPress (opcional)
wp_url = os.getenv("WP_URL", "")
if wp_url:
    test("WP_URL configurado", bool(wp_url))
    test("WP_USER configurado", bool(os.getenv("WP_USER", "")), "Requerido para etapa 6")
    test("WP_APP_PASSWORD configurado", bool(os.getenv("WP_APP_PASSWORD", "")), "Requerido para etapa 6")
else:
    warn("WordPress no configurado", "Etapa 6 no disponible")


# ══════════════════════════════════════════════════════
# 4. MÓDULOS IMPORTABLES
# ══════════════════════════════════════════════════════
print("\n4. Módulos del pipeline")

modules = [
    ("etapa1_extraer_programas", "extract_programs"),
    ("etapa2_extraer_datos", "process_programs"),
    ("generate_seo", "generate_seo_content"),
    ("fetch_images", "fetch_program_images"),
    ("generate_map", "generate_circuit_map"),
    ("etapa4_publicar_wordpress", "publish_programs"),
    ("llm_client", "llm_text"),
    ("llm_client", "llm_vision"),
]

for mod_name, func_name in modules:
    try:
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name, None)
        test(f"{mod_name}.{func_name}()", func is not None, "Función no encontrada")
    except Exception as e:
        test(f"{mod_name}.{func_name}()", False, str(e)[:80])


# ══════════════════════════════════════════════════════
# 5. TEMPLATE JINJA2
# ══════════════════════════════════════════════════════
print("\n5. Template del mapa")

template_path = os.path.join(PROJECT_ROOT, "templates", "circuit_map.html.j2")
if os.path.exists(template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    test("Template existe", True)
    test("Contiene MapLibre", "maplibre-gl" in template_content)
    test("Contiene CIRCUIT data", "CIRCUIT" in template_content)
    test("Contiene COORDS", "COORDS" in template_content)
    test("Contiene TRAMOS", "TRAMOS" in template_content)
    test("Contiene MAPTILER_KEY", "MAPTILER_KEY" in template_content)
    test("Contiene day navigation", "day-nav" in template_content or "cm-days" in template_content)
    test("Contiene info panel", "cm-info" in template_content)
else:
    test("Template existe", False, "templates/circuit_map.html.j2 no encontrado")


# ══════════════════════════════════════════════════════
# 6. JSON DE DATOS (si existe output previo)
# ══════════════════════════════════════════════════════
print("\n6. Validación de datos (output existente)")

json_path = find_test_json()
if json_path:
    with open(json_path, "r", encoding="utf-8") as f:
        programs = json.load(f)

    test(f"programas.json encontrado ({len(programs)} programas)", len(programs) > 0)

    # Validar estructura de un programa
    prog = programs[0]
    required_fields = ["id", "titulo", "dias", "precio_desde", "itinerario", "incluye"]
    for field in required_fields:
        test(f"Campo '{field}' presente", field in prog, f"Falta en programa {prog.get('id', '?')}")

    # Validar itinerario
    itin = prog.get("itinerario", [])
    test(f"Itinerario tiene {len(itin)} días", len(itin) > 0)
    if itin:
        day = itin[0]
        for f in ["dia", "dia_semana", "ciudades"]:
            test(f"Día tiene campo '{f}'", f in day)

    # Validar SEO (si existe)
    seo = prog.get("seo")
    if seo:
        seo_fields = ["focus_keyword", "seo_title", "meta_description", "intro", "highlights", "cta"]
        for f in seo_fields:
            test(f"SEO campo '{f}'", f in seo)
        test("Keyword en seo_title", seo.get("focus_keyword", "x") in seo.get("seo_title", ""), "Keyword no aparece en título SEO")
        test("Intro empieza con keyword", seo.get("intro", "").startswith(seo.get("focus_keyword", "xxx")), "Intro no empieza con keyword")
    else:
        warn("SEO no generado aún", "Ejecutar etapa 3")

    # Validar imágenes (si existen)
    images = prog.get("_images")
    if images:
        test("Imagen cover presente", "cover" in images)
        test("Cover tiene url_medium", "url_medium" in images.get("cover", {}))
    else:
        warn("Imágenes no obtenidas aún", "Ejecutar etapa 4")
else:
    warn("No hay output previo", "Ejecutar el pipeline primero para generar datos de test")


# ══════════════════════════════════════════════════════
# 7. WORDPRESS PLUGIN
# ══════════════════════════════════════════════════════
print("\n7. Plugin WordPress")

plugin_path = os.path.join(PROJECT_ROOT, "wordpress", "europamundo-circuitos.php")
if os.path.exists(plugin_path):
    with open(plugin_path, "r", encoding="utf-8") as f:
        plugin_content = f.read()

    test("Plugin PHP existe", True)
    test("Registra CPT 'circuito'", "register_post_type" in plugin_content)
    test("Registra taxonomía 'region'", "region_europamundo" in plugin_content)
    test("Registra taxonomía 'serie'", "serie_europamundo" in plugin_content)
    test("Endpoint SEO custom", "europamundo_update_seo_meta" in plugin_content)
    test("Shortcode [europamundo_circuitos]", "europamundo_circuitos" in plugin_content)
    test("Menú navigation", "europamundo_create_menu" in plugin_content)
    test("Oculta author box", "single-circuito" in plugin_content)
    test("WhatsApp button", "wa.link" in plugin_content)
    test("Sin errores de comillas PHP", "echo '<style>" not in plugin_content, "Usar ?>...<?php en vez de echo con comillas")
else:
    test("Plugin PHP existe", False)


# ══════════════════════════════════════════════════════
# 8. CONECTIVIDAD (solo si hay APIs configuradas)
# ══════════════════════════════════════════════════════
print("\n8. Conectividad (APIs)")

# WordPress
if wp_url:
    try:
        import requests
        r = requests.get(f"{wp_url}/wp-json/wp/v2/circuito?per_page=1",
                         auth=(os.getenv("WP_USER", ""), os.getenv("WP_APP_PASSWORD", "")),
                         timeout=10)
        test("WordPress REST API accesible", r.status_code == 200, f"Status: {r.status_code}")

        r2 = requests.get(f"{wp_url}/wp-json/wp/v2/region_europamundo", timeout=10)
        test("Taxonomía 'region' registrada", r2.status_code == 200)
    except Exception as e:
        test("WordPress accesible", False, str(e)[:80])
else:
    warn("WordPress no configurado", "Skip")

# Pexels
pexels_key = os.getenv("PEXELS_API_KEY", "")
if pexels_key:
    try:
        import requests
        r = requests.get("https://api.pexels.com/v1/search",
                         headers={"Authorization": pexels_key},
                         params={"query": "test", "per_page": 1},
                         timeout=10)
        test("Pexels API accesible", r.status_code == 200, f"Status: {r.status_code}")
    except Exception as e:
        test("Pexels API", False, str(e)[:80])


# ══════════════════════════════════════════════════════
# RESUMEN
# ══════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print(f"  RESULTADOS: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET}, {YELLOW}{warnings} warnings{RESET}")
total = passed + failed
if total > 0:
    score = int((passed / total) * 100)
    color = GREEN if score >= 90 else YELLOW if score >= 70 else RED
    print(f"  Score: {color}{score}%{RESET}")
print(f"{'=' * 60}")

sys.exit(1 if failed > 0 else 0)
