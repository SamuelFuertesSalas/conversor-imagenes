# Imagen mínima con Python para convertir imágenes sin instalar nada en el host
FROM python:3.12-slim

# Dependencias del script: Pillow (procesado de imágenes), plugin AVIF y barra de progreso
RUN pip install --no-cache-dir pillow pillow-avif-plugin tqdm

WORKDIR /app
COPY convertir_imagenes_masivo.py .

# El script es interactivo (pide rutas y formato por teclado),
# por eso se ejecuta con "docker run -it" (ver instrucciones)
ENTRYPOINT ["python", "convertir_imagenes_masivo.py"]
