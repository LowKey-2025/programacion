from datetime import date, datetime

FORMATO_FECHA = "%Y-%m-%d"


def convertir_fecha(texto):
    """Convierte un texto AAAA-MM-DD en date.

    Devuelve None si el formato no es exacto o si la fecha no existe
    (por ejemplo, 2026-02-30). Acepta también un objeto date ya construido.
    """
    if isinstance(texto, datetime):
        return texto.date()
    if isinstance(texto, date):
        return texto
    if not isinstance(texto, str):
        return None
    texto = texto.strip()
    # Se exige el formato completo: 4 cifras, 2 cifras, 2 cifras.
    if len(texto) != 10 or texto[4] != "-" or texto[7] != "-":
        return None
    try:
        return datetime.strptime(texto, FORMATO_FECHA).date()
    except ValueError:
        return None


def fecha_a_texto(fecha):
    """Convierte un date en texto AAAA-MM-DD."""
    return fecha.strftime(FORMATO_FECHA)


def convertir_entero(texto, minimo=None, maximo=None):
    """Convierte un texto en entero y comprueba que esté en [minimo, maximo].

    Devuelve None si el texto no es un entero o si queda fuera del rango.
    """
    if isinstance(texto, bool):
        return None
    if isinstance(texto, int):
        valor = texto
    elif isinstance(texto, str):
        limpio = texto.strip()
        cuerpo = limpio[1:] if limpio[:1] in "+-" else limpio
        if not cuerpo or not (cuerpo.isascii() and cuerpo.isdigit()):
            return None
        valor = int(limpio)
    else:
        return None
    if minimo is not None and valor < minimo:
        return None
    if maximo is not None and valor > maximo:
        return None
    return valor


def _solo_digitos(texto, minimo, maximo):
    if not isinstance(texto, str):
        return None
    limpio = texto.strip()
    if limpio.isascii() and limpio.isdigit() and minimo <= len(limpio) <= maximo:
        return limpio
    return None


def validar_documento(texto):
    """Documento: texto numérico de 6 a 10 dígitos."""
    return _solo_digitos(texto, 6, 10)


def validar_telefono(texto):
    """Teléfono: texto numérico de 7 a 10 dígitos."""
    return _solo_digitos(texto, 7, 10)


def validar_nombre(texto):
    """Nombre: no vacío y con mínimo 3 caracteres (sin contar espacios extremos).

    Los espacios repetidos internos se reducen a uno solo.
    """
    if not isinstance(texto, str):
        return None
    limpio = " ".join(texto.split())
    return limpio if len(limpio) >= 3 else None


def validar_correo(texto):
    """Correo: contiene «@» y al menos un punto después de la arroba.

    También exige que haya texto antes de la arroba, que no haya espacios y
    que el punto no quede pegado a la arroba ni al final.
    """
    if not isinstance(texto, str):
        return None
    limpio = texto.strip()
    if " " in limpio or limpio.count("@") != 1:
        return None
    usuario, dominio = limpio.split("@")
    if not usuario or "." not in dominio:
        return None
    if dominio.startswith(".") or dominio.endswith("."):
        return None
    return limpio
