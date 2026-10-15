import json
import os

CLAVES = ("siguiente_reserva", "habitaciones", "huespedes", "reservas")


class ErrorDeDatos(Exception):
    """El archivo de datos no puede leerse, interpretarse o escribirse."""


def estructura_vacia():
    """Estado inicial cuando todavía no existe el archivo."""
    return {"siguiente_reserva": 1, "habitaciones": [], "huespedes": [], "reservas": []}


def leer_datos(ruta):
    """Lee el archivo JSON y devuelve un diccionario con las cuatro claves.

    Si el archivo no existe devuelve la estructura vacía (y no lo crea).
    Lanza ErrorDeDatos si no puede leerse o interpretarse.
    """
    if not os.path.exists(ruta):
        return estructura_vacia()
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except json.JSONDecodeError as error:
        raise ErrorDeDatos(
            f"El archivo «{ruta}» no es JSON válido "
            f"(línea {error.lineno}, columna {error.colno}: {error.msg})."
        ) from error
    except (OSError, UnicodeDecodeError) as error:
        raise ErrorDeDatos(f"No se pudo leer el archivo «{ruta}»: {error}") from error

    if not isinstance(datos, dict):
        raise ErrorDeDatos(f"El archivo «{ruta}» no contiene un objeto JSON con las colecciones.")
    faltan = [clave for clave in CLAVES if clave not in datos]
    if faltan:
        raise ErrorDeDatos(f"Al archivo «{ruta}» le faltan las claves: {', '.join(faltan)}.")
    for clave in CLAVES[1:]:
        if not isinstance(datos[clave], list):
            raise ErrorDeDatos(f"En «{ruta}», «{clave}» debe ser una lista.")
    return datos


def escribir_datos(ruta, datos):
    """Guarda el estado completo en el archivo JSON.

    Escribe primero en un archivo temporal y luego lo reemplaza, de modo que un
    fallo a mitad de escritura nunca deja el archivo original truncado.
    Lanza ErrorDeDatos si no puede escribir.
    """
    temporal = ruta + ".tmp"
    try:
        carpeta = os.path.dirname(os.path.abspath(ruta))
        os.makedirs(carpeta, exist_ok=True)
        with open(temporal, "w", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=2)
        os.replace(temporal, ruta)
    except (OSError, TypeError, ValueError) as error:
        try:
            if os.path.exists(temporal):
                os.remove(temporal)
        except OSError:
            pass
        raise ErrorDeDatos(f"No se pudo escribir el archivo «{ruta}»: {error}") from error
