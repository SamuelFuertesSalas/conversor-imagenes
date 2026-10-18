#!/usr/bin/env python3
"""
Convierte imágenes .png, .jpg, .jpeg de una carpeta (y subcarpetas) a .webp o .avif,
replicando la misma estructura y nombres de archivo en la carpeta de destino.

Pensado para funcionar bien tanto con pocas imágenes como con decenas de miles:
- Procesa en paralelo usando todos los núcleos de la CPU disponibles.
- Muestra progreso cada cierto número de imágenes.
- Si una imagen destino ya existe, la salta (permite relanzar el script tras
  un corte sin repetir trabajo ya hecho).

Requiere:
    pip install pillow pillow-avif-plugin tqdm
"""

import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

from PIL import Image

try:
    import pillow_avif  # noqa: F401  -> registra el soporte AVIF en Pillow
    AVIF_DISPONIBLE = True
except ImportError:
    AVIF_DISPONIBLE = False

try:
    from tqdm import tqdm
    TQDM_DISPONIBLE = True
except ImportError:
    TQDM_DISPONIBLE = False

EXTENSIONES_ORIGEN = {".png", ".jpg", ".jpeg"}

# Configuración pensada para reducir mucho el peso del archivo mientras la
# pérdida de calidad sea prácticamente imperceptible a simple vista.
# WEBP: modo lossy (con pérdida) a calidad alta -> 75-85 es el punto óptimo
#       entre peso y calidad visual.
# AVIF: calidad más baja que WEBP porque el códec comprime mucho mejor a
#       igual calidad percibida; ~45-55 ya da resultados muy buenos, y el
#       submuestreo 4:2:0 (en vez de 4:4:4) recorta bastante peso extra
#       sin que se note casi nada en fotos normales.
CALIDAD_WEBP = 80
CALIDAD_AVIF = 50

# Cuántos procesos en paralelo usar. Por defecto, todos los núcleos.
NUM_PROCESOS = cpu_count()


def pedir_ruta(mensaje: str, debe_existir: bool) -> Path:
    while True:
        entrada = input(mensaje).strip().strip('"').strip("'")
        ruta = Path(entrada).expanduser().resolve()
        if debe_existir and not ruta.is_dir():
            print(f"  ⚠ La carpeta '{ruta}' no existe. Inténtalo de nuevo.")
            continue
        return ruta


def pedir_formato() -> str:
    """Pregunta al usuario a qué formato quiere convertir: webp o avif."""
    while True:
        entrada = input("¿A qué formato quieres convertir? (webp/avif): ").strip().lower()
        if entrada in ("webp", "avif"):
            if entrada == "avif" and not AVIF_DISPONIBLE:
                print("  ⚠ No se encontró 'pillow-avif-plugin'. Instálalo con:")
                print("    pip install pillow-avif-plugin")
                continue
            return entrada
        print("  ⚠ Opción no válida. Escribe 'webp' o 'avif'.")


def convertir_imagen(args):
    """Convierte una imagen al formato elegido, conservando la carpeta/nombre relativo.

    Recibe una tupla porque ProcessPoolExecutor.map/submit solo pasa un argumento
    limpio a cada proceso trabajador.
    """
    ruta_origen, carpeta_destino_base, ruta_relativa, formato = args

    carpeta_destino = carpeta_destino_base / ruta_relativa.parent
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    nombre_base = ruta_relativa.stem
    destino = carpeta_destino / f"{nombre_base}.{formato}"

    # Reanudación: si ya existe el archivo convertido, lo saltamos.
    if destino.exists():
        return ("saltada", ruta_relativa, None)

    calidad = CALIDAD_WEBP if formato == "webp" else CALIDAD_AVIF

    try:
        with Image.open(ruta_origen) as img:
            if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                img_convertida = img.convert("RGBA")
            else:
                img_convertida = img.convert("RGB")

            if formato == "webp":
                img_convertida.save(destino, format="WEBP", quality=calidad, method=6)
            else:  # avif
                img_convertida.save(destino, format="AVIF", quality=calidad, subsampling="4:2:0", speed=6)

        return ("ok", ruta_relativa, None)

    except Exception as e:
        return ("error", ruta_relativa, str(e))


def main():
    print("=== Conversor de imágenes a WEBP o AVIF (paralelo, apto para grandes volúmenes) ===\n")

    if not TQDM_DISPONIBLE:
        print("  (Sugerencia: instala 'tqdm' para ver una barra de progreso más clara: pip install tqdm)\n")

    carpeta_origen = pedir_ruta("Ruta de la carpeta de origen: ", debe_existir=True)
    carpeta_destino = pedir_ruta("Ruta de la carpeta de destino: ", debe_existir=False)
    formato = pedir_formato()
    carpeta_destino.mkdir(parents=True, exist_ok=True)

    imagenes = [
        p for p in carpeta_origen.rglob("*")
        if p.is_file() and p.suffix.lower() in EXTENSIONES_ORIGEN
    ]

    if not imagenes:
        print("\nNo se encontraron imágenes .png, .jpg o .jpeg en esa carpeta.")
        sys.exit(0)

    total = len(imagenes)
    print(f"\nSe encontraron {total} imágenes. Convirtiendo a {formato.upper()} "
          f"usando {NUM_PROCESOS} procesos en paralelo...\n")

    tareas = [
        (ruta_origen, carpeta_destino, ruta_origen.relative_to(carpeta_origen), formato)
        for ruta_origen in imagenes
    ]

    ok = 0
    saltadas = 0
    errores = []

    with ProcessPoolExecutor(max_workers=NUM_PROCESOS) as executor:
        futuros = [executor.submit(convertir_imagen, tarea) for tarea in tareas]

        iterador = as_completed(futuros)
        if TQDM_DISPONIBLE:
            iterador = tqdm(iterador, total=total, unit="img")

        contador = 0
        for futuro in iterador:
            estado, ruta_relativa, error = futuro.result()
            contador += 1

            if estado == "ok":
                ok += 1
            elif estado == "saltada":
                saltadas += 1
            else:
                errores.append((ruta_relativa, error))

            # Si no hay tqdm, imprimimos progreso cada 100 imágenes (o al final).
            if not TQDM_DISPONIBLE and (contador % 100 == 0 or contador == total):
                print(f"  ... {contador}/{total} procesadas")

    print(f"\nListo.")
    print(f"  Convertidas: {ok}")
    print(f"  Saltadas (ya existían): {saltadas}")
    print(f"  Errores: {len(errores)}")
    if errores:
        print("\nDetalle de errores:")
        for ruta_relativa, error in errores[:20]:
            print(f"  ✗ {ruta_relativa}: {error}")
        if len(errores) > 20:
            print(f"  ... y {len(errores) - 20} errores más.")
    print(f"\nArchivos en: {carpeta_destino}")


if __name__ == "__main__":
    main()
