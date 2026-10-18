# Conversor masivo de imágenes a WebP / AVIF

Script en Python que convierte imágenes `.png`, `.jpg` y `.jpeg` de una carpeta (y sus subcarpetas) a **WebP** o **AVIF**, replicando la misma estructura de carpetas en el destino. Lo hice para reducir el peso de las imágenes de una web y los servidores en los que están alojadas, para mejorar su tiempo de carga.

## Qué hace

- Procesa en paralelo usando todos los núcleos de la CPU, pensado para pocas imágenes o decenas de miles.
- Muestra el progreso (barra con `tqdm`).
- Si la imagen destino ya existe, la salta, así que se puede relanzar tras un corte sin repetir trabajo.
- Conserva la transparencia de los PNG.

## Uso con Docker 

El script es interactivo (por eso el `-it`) y te pregunta tres cosas:
1. Carpeta de origen: escribe `/entrada`
2. Carpeta de destino: escribe `/salida`
3. Formato: `webp` o `avif`

## Uso sin Docker ( Normalmente con..)

```bash
pip install pillow pillow-avif-plugin tqdm
python convertir_imagenes_masivo.py
```

## Calidad

Por defecto WebP usa calidad 80 y AVIF calidad 50. Se cambian en las constantes `CALIDAD_WEBP` y `CALIDAD_AVIF` al principio del script.

## Limitaciones conocidas

- Si en una misma carpeta hay `foto.png` y `foto.jpg`, las dos se convierten al mismo nombre y una se pisa o se salta.
- No aplica la orientación EXIF ni conserva el perfil de color, así que algunas fotos de móvil pueden salir giradas.
- Una interrupción a mitad de escritura puede dejar un archivo incompleto que se salta al relanzar.
