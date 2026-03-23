"""
Cliente LLM multi-proveedor: Claude (Anthropic) y Gemini (Google).

Abstrae las diferencias de API para que el resto del pipeline
use una interfaz única.

Configuración en .env:
    LLM_PROVIDER=gemini          # "claude" o "gemini" (default: gemini)
    ANTHROPIC_API_KEY=sk-ant-... # solo si provider=claude
    GOOGLE_API_KEY=AIza...       # solo si provider=gemini

Uso:
    from llm_client import llm_text, llm_vision

    # Texto
    response = llm_text("Genera un resumen SEO para...")

    # Visión (imagen + texto)
    response = llm_vision(image_bytes, "Extrae los datos de esta imagen...")
"""

import os
import base64
from dotenv import load_dotenv

load_dotenv()

# --- Configuración ---
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()

# Modelos por defecto
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def llm_text(prompt, max_tokens=4096):
    """
    Envía un prompt de texto y retorna la respuesta.
    Retorna: (text, usage_dict)
    """
    if LLM_PROVIDER == "claude":
        return _claude_text(prompt, max_tokens)
    else:
        return _gemini_text(prompt, max_tokens)


def _resize_image(image_bytes, scale=0.5):
    """Reduce resolución de imagen para ahorrar tokens de visión (~40-50% menos)."""
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(image_bytes))
    original_size = len(image_bytes)
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img_small = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img_small.save(buf, format="PNG", optimize=True)
    resized_bytes = buf.getvalue()
    ratio = len(resized_bytes) / original_size * 100
    print(f"    Imagen: {img.width}x{img.height} → {new_w}x{new_h} ({ratio:.0f}% del original)")
    return resized_bytes


def llm_vision(image_bytes, prompt, media_type="image/png", max_tokens=4096):
    """
    Envía una imagen + prompt y retorna la respuesta.
    Reduce la imagen al 50% antes de enviar para ahorrar tokens.
    Retorna: (text, usage_dict)
    """
    image_bytes = _resize_image(image_bytes)
    if LLM_PROVIDER == "claude":
        return _claude_vision(image_bytes, prompt, media_type, max_tokens)
    else:
        return _gemini_vision(image_bytes, prompt, media_type, max_tokens)


def get_provider_info():
    """Retorna info del proveedor actual."""
    model = CLAUDE_MODEL if LLM_PROVIDER == "claude" else GEMINI_MODEL
    return {"provider": LLM_PROVIDER, "model": model}


# ══════════════════════════════════════════════════════
# CLAUDE (Anthropic)
# ══════════════════════════════════════════════════════

def _claude_text(prompt, max_tokens):
    import anthropic
    client = anthropic.Anthropic()
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    text = message.content[0].text
    usage = {
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }
    return text, usage


def _claude_vision(image_bytes, prompt, media_type, max_tokens):
    import anthropic
    client = anthropic.Anthropic()
    img_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": img_b64,
                    },
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )
    text = message.content[0].text
    usage = {
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }
    return text, usage


# ══════════════════════════════════════════════════════
# GEMINI (Google)
# ══════════════════════════════════════════════════════

def _gemini_text(prompt, max_tokens):
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
    )
    text = response.text
    usage = _gemini_usage(response)
    return text, usage


def _gemini_vision(image_bytes, prompt, media_type, max_tokens):
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(GEMINI_MODEL)

    image_part = {"mime_type": media_type, "data": image_bytes}
    response = model.generate_content(
        [image_part, prompt],
        generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
    )
    text = response.text
    usage = _gemini_usage(response)
    return text, usage


def _gemini_usage(response):
    """Extrae tokens de uso de la respuesta de Gemini."""
    try:
        meta = response.usage_metadata
        return {
            "input_tokens": meta.prompt_token_count,
            "output_tokens": meta.candidates_token_count,
        }
    except Exception:
        return {"input_tokens": 0, "output_tokens": 0}
