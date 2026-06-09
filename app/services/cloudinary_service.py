# app/services/cloudinary_service.py
import os

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True,
)

MIME_PERMITIDOS = {"image/jpeg", "image/png", "image/webp"}
LIMITE_BYTES = 2 * 1024 * 1024  # 2 MB


def subir_foto_perfil(contenido: bytes, user_id: str) -> str:
    result = cloudinary.uploader.upload(
        contenido,
        public_id=f"pisst/fotos_perfil/{user_id}",
        overwrite=True,
        resource_type="image",
        format="webp",
        transformation=[
            {"width": 400, "height": 400, "crop": "fill", "gravity": "face"}
        ],
    )
    return result["secure_url"]
