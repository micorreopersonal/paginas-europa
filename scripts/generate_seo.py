"""
Generador de contenido SEO para programas de viaje Europamundo.

Usa Claude API para generar copy optimizado para SEO:
- Focus keyword
- SEO title
- Meta description
- Párrafo introductorio
- Highlights del circuito
- CTA final

Uso como módulo:
    from generate_seo import generate_seo_content
    seo = generate_seo_content(program_dict)

Uso como script:
    python generate_seo.py programas.json [--test N]
"""

import json
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

MAX_TOKENS = 2048

SEO_PROMPT = """Eres un experto SEO en turismo. Genera contenido SEO para esta página de circuito turístico.

DATOS DEL CIRCUITO:
- Título: {titulo}
- Días: {dias}
- Precio desde: {precio}
- Fechas de salida: {fechas}
- Ciudades: {ciudades}
- Highlights del itinerario: {highlights}
- Servicios incluidos: {servicios}

GENERA un JSON con estos campos (responde SOLO el JSON, sin markdown):

{{
  "focus_keyword": "keyword de 2-3 palabras que DEBE coincidir con el slug de la URL. Usa las mismas palabras del título del programa simplificadas. Ejemplo: título 'Rajasthán Imprescindible y Mumbai' → keyword 'Rajasthán Mumbai'. Título 'India Fascinante' → keyword 'India Fascinante'. NO agregues 'circuito', 'viaje', 'días' ni números — solo las palabras que estarán en la URL.",
  "seo_title": "título SEO máximo 60 chars. DEBE incluir: keyword al inicio + días + precio + una POWER WORD (Descubre, Increíble, Exclusivo, Imperdible, Mejor, Único, Garantizado) + una SENTIMENT WORD (positiva o negativa: Inolvidable, Soñado, Fascinante, Mágico, Espectacular). Ejemplo: 'India Fascinante: Descubre 11 Días Inolvidables desde $1,575'",
  "meta_description": "descripción meta de 140-155 chars, incluye keyword, beneficio emocional y CTA implícito. Debe generar deseo de clic.",
  "og_title": "título para redes sociales, máximo 70 chars, atractivo y con keyword + emoji relevante",
  "og_description": "descripción para compartir en redes, 100-150 chars, genera curiosidad",
  "intro": "párrafo introductorio de 80-120 palabras. La PRIMERA PALABRA debe ser la focus keyword exacta. Menciona las ciudades principales, la duración y el precio. Incluye la keyword EXACTA al menos 3 veces de forma natural repartida en el texto.",
  "heading_keyword": "un H2 heading atractivo que contenga la focus keyword exacta. Ejemplo: 'Tu circuito India Fascinante día a día' o 'Descubre Rajasthán Mumbai paso a paso'. Este heading se usará en el contenido.",
  "highlights": ["3-5 experiencias destacadas del circuito en frases cortas y atractivas"],
  "cta": "llamada a la acción de 2-3 frases. Menciona Gina Travel. Incluye la focus keyword una vez más. Incluye un enlace textual mencionando que pueden ver más circuitos en la web.",
  "schema_description": "descripción breve de 1-2 oraciones para schema.org TouristTrip, factual y concisa"
}}

REGLAS SEO CRÍTICAS:
- La focus keyword EXACTA (las mismas palabras, mismo orden) debe aparecer en: seo_title, meta_description, intro (3 veces), heading_keyword, cta
- El intro DEBE EMPEZAR literalmente con la focus keyword como primera(s) palabra(s)
- El seo_title DEBE contener al menos una power word (Descubre, Increíble, Exclusivo, Imperdible, Único, Garantizado, Mejor)
- El seo_title DEBE contener al menos una sentiment word (Inolvidable, Soñado, Fascinante, Mágico, Espectacular, Encantador)
- Escribe en español, tono profesional pero cálido
- Los highlights deben ser concretos (nombres de lugares, experiencias reales del itinerario)
- El seo_title NO debe exceder 60 caracteres
- La meta_description NO debe exceder 155 caracteres
- IMPORTANTE: Los precios están en DÓLARES AMERICANOS (USD, $). Usa el símbolo $ no €. El mercado es Perú/Latinoamérica.
"""


def _extract_highlights(program):
    """Extrae puntos destacados del itinerario para el prompt."""
    highlights = []
    for day in program.get("itinerario", []):
        desc = day.get("descripcion") or day.get("descripción") or ""
        if any(kw in desc.lower() for kw in ["taj mahal", "templo", "palacio", "fuerte",
                                               "ceremonia", "barco", "mercado", "museo",
                                               "elefante", "rickshaw", "ganges", "safari"]):
            ciudades = day.get("ciudades", "")
            highlights.append(f"Día {day.get('dia')}: {ciudades} - {desc[:100]}")
    return highlights[:5]


def _extract_cities_summary(program):
    """Lista de ciudades únicas visitadas."""
    cities = []
    seen = set()
    for day in program.get("itinerario", []):
        for city in day.get("ciudades", "").split(" - "):
            city = city.strip()
            if city and city not in seen:
                seen.add(city)
                cities.append(city)
    return ", ".join(cities)


def _extract_services(program):
    """Resumen de servicios incluidos."""
    incluye = program.get("incluye", {})
    if not incluye:
        return "Información no disponible"
    parts = []
    if incluye.get("visitas_panoramicas"):
        parts.append(f"Visitas en: {incluye['visitas_panoramicas']}")
    if incluye.get("entradas"):
        parts.append(f"Entradas: {incluye['entradas'][:100]}")
    if incluye.get("vuelos_incluidos"):
        parts.append(f"Vuelos: {incluye['vuelos_incluidos'][:80]}")
    if incluye.get("almuerzos"):
        parts.append(incluye["almuerzos"])
    if incluye.get("cenas"):
        parts.append(incluye["cenas"])
    return ". ".join(parts)


def generate_seo_content(program):
    """
    Genera contenido SEO para un programa usando LLM (Claude o Gemini).
    Retorna dict con: focus_keyword, seo_title, meta_description, intro, highlights, cta
    """
    from llm_client import llm_text

    prompt = SEO_PROMPT.format(
        titulo=program.get("titulo", ""),
        dias=program.get("dias", ""),
        precio=program.get("precio_desde", ""),
        fechas=program.get("fechas_salida", ""),
        ciudades=_extract_cities_summary(program),
        highlights="\n".join(_extract_highlights(program)),
        servicios=_extract_services(program),
    )

    # Intentar hasta 2 veces (Gemini a veces devuelve JSON malformado)
    seo_data = None
    for attempt in range(2):
        response_text, usage = llm_text(prompt, MAX_TOKENS)

        # Limpiar markdown wrapping
        clean = response_text.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1]
            clean = clean.rsplit("```", 1)[0]

        # Extraer JSON si hay texto extra
        json_start = clean.find("{")
        json_end = clean.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            clean = clean[json_start:json_end]

        try:
            seo_data = json.loads(clean)
            break
        except json.JSONDecodeError:
            if attempt == 0:
                continue
            raise

    return seo_data, usage


def enrich_programs_with_seo(json_path, test_count=None):
    """Enriquece el JSON de programas con contenido SEO."""
    with open(json_path, "r", encoding="utf-8") as f:
        programs = json.load(f)

    valid = [p for p in programs if "_error" not in p]
    if test_count:
        valid = valid[:test_count]

    print(f"Generando SEO para {len(valid)} programas...")
    print("-" * 50)

    total_input = 0
    total_output = 0

    for i, prog in enumerate(valid):
        titulo = prog.get("titulo", "?")
        print(f"  [{i+1}/{len(valid)}] {titulo}...", end=" ", flush=True)

        try:
            seo_data, usage = generate_seo_content(prog)
            prog["seo"] = seo_data
            total_input += usage["input_tokens"]
            total_output += usage["output_tokens"]
            print(f"OK ({usage['input_tokens']}+{usage['output_tokens']} tokens)")
        except Exception as e:
            print(f"ERROR: {e}")

        if i < len(valid) - 1:
            time.sleep(0.5)

    # Guardar JSON actualizado
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(programs, f, ensure_ascii=False, indent=2)

    # Costos
    cost_input = (total_input / 1_000_000) * 3
    cost_output = (total_output / 1_000_000) * 15
    cost_total = cost_input + cost_output

    print("-" * 50)
    print(f"SEO generado para {len(valid)} programas")
    print(f"Costo: ${cost_total:.4f} USD")
    print(f"JSON actualizado: {json_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generate_seo.py <programas.json> [--test N]")
        sys.exit(1)

    json_path = sys.argv[1]
    test_count = None

    if "--test" in sys.argv:
        idx = sys.argv.index("--test")
        test_count = int(sys.argv[idx + 1])

    enrich_programs_with_seo(json_path, test_count)
