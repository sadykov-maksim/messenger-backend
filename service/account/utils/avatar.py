import hashlib
from io import BytesIO

import pydenticon
from django.core.files.base import ContentFile


def generate_identicon_png(seed: str, size: int = 256) -> ContentFile:
    """
    Возвращает PNG как ContentFile для сохранения в ImageField.
    seed — строка (email/id/username), из которой строим уникальную картинку.
    """
    if not seed:
        seed = "user"

    digest = hashlib.sha256(seed.strip().lower().encode("utf-8")).hexdigest()

    generator = pydenticon.Generator(
        5, 5,  # сетка 5x5
        foreground=["rgb(45, 125, 210)", "rgb(60, 200, 120)", "rgb(240, 140, 60)", "rgb(170, 90, 220)"],
        background="rgb(245, 246, 248)"
    )

    png_bytes = generator.generate(digest, size, size, output_format="png")
    return ContentFile(png_bytes)