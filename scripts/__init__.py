# Europamundo Pipeline Scripts
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent


def get_output_dir(pdf_path):
    """Retorna el directorio de output para un PDF, siempre relativo al proyecto."""
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_dir = PROJECT_ROOT / "output" / pdf_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)
