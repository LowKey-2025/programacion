import os
from datetime import date, timedelta

from almacenamiento import ErrorDeDatos, escribir_datos, leer_datos
from modelo import (
    ACTIVA,
    CAPACIDADES,
    ESTADOS,
    PISO_MAX,
    PISO_MIN,
    POSICION_MAX,
    POSICION_MIN,
    Habitacion,
    Huesped,
    Reserva,
)
from validaciones import (
    convertir_entero,
    convertir_fecha,
    fecha_a_texto,
    validar_correo,
    validar_documento,
    validar_nombre,
    validar_telefono,
)

RUTA_POR_DEFECTO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos_hotel.json")

MAX_HABITACIONES = (PISO_MAX - PISO_MIN + 1) * (POSICION_MAX - POSICION_MIN + 1)  # 20
NUMERO_MIN = PISO_MIN * 100 + POSICION_MIN  # 101
NUMERO_MAX = PISO_MAX * 100 + POSICION_MAX  # 405
DIAS_MIN, DIAS_MAX = 1, 30
MAX_PERSONAS = max(CAPACIDADES)  # 6
MAX_CONSECUTIVO = 9999  # R + 4 dígitos

# Mensajes de validación de formato (se usan en varias operaciones)
MSG_PISO = f"Piso inválido: debe ser un entero de {PISO_MIN} a {PISO_MAX}."
MSG_POSICION = f"Posición inválida: debe ser un entero de {POSICION_MIN} a {POSICION_MAX}."
MSG_CAPACIDAD = "Capacidad inválida: debe ser 2, 4 o 6."
MSG_NUMERO = f"Número de habitación inválido: debe ser un entero de {NUMERO_MIN} a {NUMERO_MAX}."
MSG_DOCUMENTO = "Documento inválido: debe tener de 6 a 10 dígitos, sin puntos ni espacios."
MSG_NOMBRE = "Nombre inválido: no puede estar vacío y debe tener al menos 3 caracteres."
MSG_TELEFONO = "Teléfono inválido: debe tener de 7 a 10 dígitos."
MSG_CORREO = "Correo inválido: debe contener «@» y un punto después (ej. nombre@correo.com)."
MSG_FECHA = (
    "Fecha de ingreso inválida: use el formato AAAA-MM-DD con una fecha que exista "
    "(ej. 2026-10-20)."
)
MSG_DIAS = f"Días de estadía inválidos: debe ser un entero de {DIAS_MIN} a {DIAS_MAX}."
MSG_PERSONAS = f"Número de personas inválido: debe ser un entero de 1 a {MAX_PERSONAS}."


def _plural(cantidad, singular, plural):
    return f"{cantidad} {singular if cantidad == 1 else plural}"


class Hotel:
    """Gestor del hotel: colecciones, CRUD, reglas del negocio y guardado."""

    def __init__(self, ruta=RUTA_POR_DEFECTO):
        """Crea el gestor y carga los datos.

        Si el archivo no existe empieza con colecciones vacías. Si es ilegible
        o inconsistente lanza ErrorDeDatos y no escribe nada.
        """
        self._ruta = ruta
        self._habitaciones = {}
        self._huespedes = {}
        self._reservas = {}
        self._siguiente_reserva = 1
        self._cargar(leer_datos(ruta))

    # ======================================================================
    # Carga, reconstrucción de relaciones y guardado
    # ======================================================================
    def _cargar(self, datos):
        habitaciones, huespedes, reservas = {}, {}, {}
        try:
            siguiente = datos["siguiente_reserva"]
            if isinstance(siguiente, bool) or not isinstance(siguiente, int) or siguiente < 1:
                raise ErrorDeDatos("«siguiente_reserva» debe ser un entero mayor o igual a 1.")

            # 1. Habitaciones, con su número como clave
            for registro in datos["habitaciones"]:
                habitacion = Habitacion.desde_dict(registro)
                if habitacion.numero in habitaciones:
                    raise ErrorDeDatos(f"La habitación {habitacion.numero} está repetida.")
                habitaciones[habitacion.numero] = habitacion
            if len(habitaciones) > MAX_HABITACIONES:
                raise ErrorDeDatos(f"Hay más de {MAX_HABITACIONES} habitaciones.")

            # 2. Huéspedes, con su documento como clave
            for registro in datos["huespedes"]:
                huesped = Huesped.desde_dict(registro)
                if huesped.documento in huespedes:
                    raise ErrorDeDatos(f"El huésped {huesped.documento} está repetido.")
                huespedes[huesped.documento] = huesped

            # 3. Reservas, con referencias reales a huésped y habitación
            mayor_consecutivo = 0
            for registro in datos["reservas"]:
                codigo = registro["codigo"]
                consecutivo = self._consecutivo_de(codigo)
                if consecutivo is None:
                    raise ErrorDeDatos(f"El código de reserva «{codigo}» no tiene el formato R0000.")
                if codigo in reservas:
                    raise ErrorDeDatos(f"La reserva {codigo} está repetida.")
                documento = registro["documento_huesped"]
                numero = registro["numero_habitacion"]
                huesped = huespedes.get(documento)
                if huesped is None:
                    raise ErrorDeDatos(
                        f"La reserva {codigo} apunta al huésped {documento}, que no existe."
                    )
                habitacion = habitaciones.get(numero)
                if habitacion is None:
                    raise ErrorDeDatos(
                        f"La reserva {codigo} apunta a la habitación {numero}, que no existe."
                    )
                reserva = Reserva.desde_dict(registro, huesped, habitacion)
                if reserva.activa:
                    if not habitacion.admite(reserva.personas):
                        raise ErrorDeDatos(
                            f"La reserva ACTIVA {codigo} tiene más personas que la capacidad "
                            f"de la habitación {numero}."
                        )
                    for otra in reservas.values():
                        if (otra.activa and otra.habitacion is habitacion
                                and otra.coincide_con(reserva.fecha_ingreso, reserva.dias)):
                            raise ErrorDeDatos(
                                f"Las reservas ACTIVAS {otra.codigo} y {codigo} comparten noches "
                                f"en la habitación {numero}."
                            )
                reservas[codigo] = reserva
                mayor_consecutivo = max(mayor_consecutivo, consecutivo)

            if siguiente <= mayor_consecutivo:
                raise ErrorDeDatos(
                    f"«siguiente_reserva» ({siguiente}) no puede ser menor o igual al último "
                    f"código usado (R{mayor_consecutivo:04d})."
                )
        except ErrorDeDatos as error:
            raise ErrorDeDatos(f"Datos inconsistentes en «{self._ruta}»: {error}") from error
        except (KeyError, TypeError, ValueError, AttributeError) as error:
            detalle = f"falta el campo {error}" if isinstance(error, KeyError) else str(error)
            raise ErrorDeDatos(f"Datos inconsistentes en «{self._ruta}»: {detalle}.") from error

        # Solo si todo cargó bien se reemplaza el estado
        self._habitaciones = habitaciones
        self._huespedes = huespedes
        self._reservas = reservas
        self._siguiente_reserva = siguiente

    @staticmethod
    def _consecutivo_de(codigo):
        if isinstance(codigo, str) and len(codigo) == 5 and codigo[0] == "R":
            return convertir_entero(codigo[1:], 1, MAX_CONSECUTIVO)
        return None

    def _a_dict(self):
        """Diccionario completo con las cuatro claves, listo para escribir."""
        return {
            "siguiente_reserva": self._siguiente_reserva,
            "habitaciones": [h.a_dict() for h in self.listar_habitaciones()],
            "huespedes": [h.a_dict() for h in sorted(self._huespedes.values(),
                                                    key=lambda h: h.documento)],
            "reservas": [r.a_dict() for r in self._reservas.values()],
        }

    def _guardar(self, respaldo):
        """Escribe el JSON. Si falla, restaura el estado anterior.

        Devuelve None si guardó, o el texto del error si no pudo.
        """
        try:
            escribir_datos(self._ruta, self._a_dict())
            return None
        except ErrorDeDatos as error:
            self._cargar(respaldo)
            return str(error)

    def _aceptar(self, respaldo, mensaje, dato):
        """Guarda un cambio ya aplicado y arma la tupla de resultado."""
        error = self._guardar(respaldo)
        if error:
            return False, f"No se pudo guardar el cambio y se deshizo. {error}", None
        return True, mensaje, dato

    @staticmethod
    def _hoy(hoy):
        if hoy is None:
            return date.today()
        fecha = convertir_fecha(hoy)
        if fecha is None:
            raise ValueError(f"fecha de referencia inválida: {hoy!r}")
        return fecha

    # ======================================================================
    # Consultas generales
    # ======================================================================
    @property
    def ruta(self):
        return self._ruta

    @property
    def siguiente_reserva(self):
        return self._siguiente_reserva

    # ======================================================================
    # Habitaciones
    # ======================================================================
    def registrar_habitacion(self, piso, posicion, capacidad):
        piso_ok = convertir_entero(piso, PISO_MIN, PISO_MAX)
        if piso_ok is None:
            return False, MSG_PISO, None
        posicion_ok = convertir_entero(posicion, POSICION_MIN, POSICION_MAX)
        if posicion_ok is None:
            return False, MSG_POSICION, None
        capacidad_ok = convertir_entero(capacidad)
        if capacidad_ok not in CAPACIDADES:
            return False, MSG_CAPACIDAD, None
        numero = piso_ok * 100 + posicion_ok
        if numero in self._habitaciones:
            return False, f"La habitación {numero} ya está registrada.", None

        respaldo = self._a_dict()
        habitacion = Habitacion(numero, piso_ok, capacidad_ok)
        self._habitaciones[numero] = habitacion
        return self._aceptar(
            respaldo,
            f"Habitación {numero} registrada (piso {piso_ok}, capacidad {capacidad_ok}).",
            habitacion,
        )

    def listar_habitaciones(self):
        return [self._habitaciones[n] for n in sorted(self._habitaciones)]

    def buscar_habitacion(self, numero):
        numero_ok = convertir_entero(numero)
        return self._habitaciones.get(numero_ok)

    def actualizar_habitacion(self, numero, capacidad):
        numero_ok = convertir_entero(numero, NUMERO_MIN, NUMERO_MAX)
        if numero_ok is None:
            return False, MSG_NUMERO, None
        habitacion = self._habitaciones.get(numero_ok)
        if habitacion is None:
            return False, f"No existe la habitación {numero_ok}.", None
        capacidad_ok = convertir_entero(capacidad)
        if capacidad_ok not in CAPACIDADES:
            return False, MSG_CAPACIDAD, None
        for reserva in self.reservas_de_habitacion(numero_ok):
            if reserva.activa and reserva.personas > capacidad_ok:
                return (
                    False,
                    f"No se puede bajar la capacidad de la {numero_ok} a {capacidad_ok}: "
                    f"la reserva ACTIVA {reserva.codigo} tiene {reserva.personas} personas.",
                    None,
                )
        if habitacion.capacidad == capacidad_ok:
            return True, f"La habitación {numero_ok} ya tiene capacidad {capacidad_ok}; no hubo cambios.", habitacion

        respaldo = self._a_dict()
        habitacion.cambiar_capacidad(capacidad_ok)
        return self._aceptar(
            respaldo, f"Habitación {numero_ok} actualizada: capacidad {capacidad_ok}.", habitacion
        )

    def eliminar_habitacion(self, numero):
        numero_ok = convertir_entero(numero, NUMERO_MIN, NUMERO_MAX)
        if numero_ok is None:
            return False, MSG_NUMERO, None
        if numero_ok not in self._habitaciones:
            return False, f"No existe la habitación {numero_ok}.", None
        asociadas = self.reservas_de_habitacion(numero_ok)
        if asociadas:
            return (
                False,
                f"No se puede eliminar la habitación {numero_ok}: tiene "
                f"{_plural(len(asociadas), 'reserva asociada', 'reservas asociadas')} en su historial.",
                None,
            )
        respaldo = self._a_dict()
        del self._habitaciones[numero_ok]
        return self._aceptar(respaldo, f"Habitación {numero_ok} eliminada.", None)

    # ======================================================================
    # Huéspedes
    # ======================================================================
    def registrar_huesped(self, documento, nombre, telefono, correo):
        documento_ok = validar_documento(documento)
        if documento_ok is None:
            return False, MSG_DOCUMENTO, None
        if documento_ok in self._huespedes:
            return False, f"Ya existe un huésped con el documento {documento_ok}.", None
        error = self._validar_contacto(nombre, telefono, correo)
        if error:
            return False, error, None

        respaldo = self._a_dict()
        huesped = Huesped(documento_ok, nombre, telefono, correo)
        self._huespedes[documento_ok] = huesped
        return self._aceptar(
            respaldo, f"Huésped {huesped.nombre} ({documento_ok}) registrado.", huesped
        )

    @staticmethod
    def _validar_contacto(nombre, telefono, correo):
        if validar_nombre(nombre) is None:
            return MSG_NOMBRE
        if validar_telefono(telefono) is None:
            return MSG_TELEFONO
        if validar_correo(correo) is None:
            return MSG_CORREO
        return None

    def listar_huespedes(self):
        return sorted(self._huespedes.values(), key=lambda h: (h.nombre.lower(), h.documento))

    def buscar_huesped(self, documento):
        if not isinstance(documento, str):
            return None
        return self._huespedes.get(documento.strip())

    def buscar_huespedes_por_nombre(self, texto):
        if not isinstance(texto, str) or not texto.strip():
            return []
        buscado = " ".join(texto.split()).casefold()
        return [h for h in self.listar_huespedes() if buscado in h.nombre.casefold()]

    def actualizar_huesped(self, documento, nombre, telefono, correo):
        documento_ok = validar_documento(documento)
        if documento_ok is None:
            return False, MSG_DOCUMENTO, None
        huesped = self._huespedes.get(documento_ok)
        if huesped is None:
            return False, f"No existe el huésped {documento_ok}.", None
        error = self._validar_contacto(nombre, telefono, correo)
        if error:
            return False, error, None

        respaldo = self._a_dict()
        huesped.actualizar_datos(nombre, telefono, correo)
        return self._aceptar(
            respaldo, f"Datos de contacto de {huesped.nombre} ({documento_ok}) actualizados.", huesped
        )

    def eliminar_huesped(self, documento):
        documento_ok = validar_documento(documento)
        if documento_ok is None:
            return False, MSG_DOCUMENTO, None
        huesped = self._huespedes.get(documento_ok)
        if huesped is None:
            return False, f"No existe el huésped {documento_ok}.", None
        asociadas = self.reservas_de_huesped(documento_ok)
        if asociadas:
            return (
                False,
                f"No se puede eliminar a {huesped.nombre} ({documento_ok}): tiene "
                f"{_plural(len(asociadas), 'reserva asociada', 'reservas asociadas')} en su historial.",
                None,
            )
        respaldo = self._a_dict()
        del self._huespedes[documento_ok]
        return self._aceptar(respaldo, f"Huésped {huesped.nombre} ({documento_ok}) eliminado.", None)

    # ======================================================================
    # Reservas
    # ======================================================================
    def _conflicto(self, habitacion, fecha_ingreso, dias):
        """Primera reserva ACTIVA de la habitación que comparte noches, o None."""
        for reserva in self._reservas.values():
            if (reserva.activa and reserva.habitacion is habitacion
                    and reserva.coincide_con(fecha_ingreso, dias)):
                return reserva
        return None

    def habitaciones_disponibles(self, fecha_ingreso, dias, personas, hoy=None):
        fecha = convertir_fecha(fecha_ingreso)
        if fecha is None:
            return False, MSG_FECHA, None
        dias_ok = convertir_entero(dias, DIAS_MIN, DIAS_MAX)
        if dias_ok is None:
            return False, MSG_DIAS, None
        personas_ok = convertir_entero(personas, 1, MAX_PERSONAS)
        if personas_ok is None:
            return False, MSG_PERSONAS, None
        hoy_ok = self._hoy(hoy)
        if fecha < hoy_ok:
            return (
                False,
                f"La fecha de ingreso {fecha_a_texto(fecha)} ya pasó: no puede ser anterior "
                f"a hoy ({fecha_a_texto(hoy_ok)}).",
                None,
            )

        libres = [
            h for h in self.listar_habitaciones()
            if h.admite(personas_ok) and self._conflicto(h, fecha, dias_ok) is None
        ]
        salida = fecha_a_texto(fecha + timedelta(days=dias_ok))
        rango = f"del {fecha_a_texto(fecha)} al {salida} para {_plural(personas_ok, 'persona', 'personas')}"
        if libres:
            mensaje = f"{_plural(len(libres), 'habitación disponible', 'habitaciones disponibles')} {rango}."
        else:
            mensaje = f"No hay habitaciones disponibles {rango}."
        return True, mensaje, libres

    def registrar_reserva(self, documento, numero, fecha_ingreso, dias, personas, hoy=None):
        # Paso 2: convertir los textos
        documento_ok = validar_documento(documento)
        if documento_ok is None:
            return False, MSG_DOCUMENTO, None
        numero_ok = convertir_entero(numero, NUMERO_MIN, NUMERO_MAX)
        if numero_ok is None:
            return False, MSG_NUMERO, None
        fecha = convertir_fecha(fecha_ingreso)
        if fecha is None:
            return False, MSG_FECHA, None
        dias_ok = convertir_entero(dias, DIAS_MIN, DIAS_MAX)
        if dias_ok is None:
            return False, MSG_DIAS, None
        personas_ok = convertir_entero(personas, 1, MAX_PERSONAS)
        if personas_ok is None:
            return False, MSG_PERSONAS, None

        # Paso 3: huésped y habitación existen
        huesped = self._huespedes.get(documento_ok)
        if huesped is None:
            return False, f"No existe el huésped {documento_ok}.", None
        habitacion = self._habitaciones.get(numero_ok)
        if habitacion is None:
            return False, f"No existe la habitación {numero_ok}.", None

        # Paso 4: fecha no anterior a hoy
        hoy_ok = self._hoy(hoy)
        if fecha < hoy_ok:
            return (
                False,
                f"La fecha de ingreso {fecha_a_texto(fecha)} ya pasó: no puede ser anterior "
                f"a hoy ({fecha_a_texto(hoy_ok)}).",
                None,
            )

        # Paso 5: capacidad
        if not habitacion.admite(personas_ok):
            return (
                False,
                f"La habitación {numero_ok} admite máximo {habitacion.capacidad} personas; "
                f"se pidieron {personas_ok}: supera la capacidad.",
                None,
            )

        # Paso 6: conflicto con reservas ACTIVAS de la habitación
        conflicto = self._conflicto(habitacion, fecha, dias_ok)
        if conflicto is not None:
            return (
                False,
                f"La habitación {numero_ok} no está disponible: coincide con la reserva "
                f"{conflicto.codigo} (del {fecha_a_texto(conflicto.fecha_ingreso)} al "
                f"{fecha_a_texto(conflicto.fecha_salida)}).",
                None,
            )

        if self._siguiente_reserva > MAX_CONSECUTIVO:
            return False, "Se agotaron los códigos de reserva (R9999).", None

        # Paso 7: crear la reserva y aumentar el consecutivo
        respaldo = self._a_dict()
        codigo = f"R{self._siguiente_reserva:04d}"
        reserva = Reserva(codigo, huesped, habitacion, fecha, dias_ok, personas_ok, ACTIVA)
        self._reservas[codigo] = reserva
        self._siguiente_reserva += 1

        # Pasos 8 y 9: guardar y responder
        return self._aceptar(
            respaldo,
            f"Reserva {codigo} registrada: habitación {numero_ok}, "
            f"salida {fecha_a_texto(reserva.fecha_salida)}",
            reserva,
        )

    def listar_reservas(self, estado=None):
        """Todas las reservas (estado None, '' o 'TODAS') o las de un estado."""
        reservas = [self._reservas[c] for c in sorted(self._reservas)]
        if estado is None:
            return reservas
        filtro = str(estado).strip().upper()
        if filtro in ("", "TODAS"):
            return reservas
        if filtro not in ESTADOS:
            return []
        return [r for r in reservas if r.estado == filtro]

    def buscar_reserva(self, codigo):
        if not isinstance(codigo, str):
            return None
        return self._reservas.get(codigo.strip().upper())

    def reservas_de_huesped(self, documento):
        """Historial de un huésped, en orden cronológico de registro."""
        documento_ok = documento.strip() if isinstance(documento, str) else None
        return [r for r in self._reservas.values() if r.huesped.documento == documento_ok]

    def reservas_de_habitacion(self, numero):
        """Historial de una habitación, en orden cronológico de registro."""
        numero_ok = convertir_entero(numero)
        return [r for r in self._reservas.values() if r.habitacion.numero == numero_ok]

    def cancelar_reserva(self, codigo):
        reserva = self.buscar_reserva(codigo)
        if reserva is None:
            return False, f"No existe la reserva {str(codigo).strip().upper()}", None
        respaldo = self._a_dict()
        if not reserva.cancelar():
            return False, f"La reserva {reserva.codigo} ya está {reserva.estado}", None
        return self._aceptar(respaldo, f"Reserva {reserva.codigo} cancelada", reserva)

    def finalizar_reserva(self, codigo, hoy=None):
        reserva = self.buscar_reserva(codigo)
        if reserva is None:
            return False, f"No existe la reserva {str(codigo).strip().upper()}", None
        if not reserva.activa:
            return False, f"La reserva {reserva.codigo} ya está {reserva.estado}", None
        hoy_ok = self._hoy(hoy)
        if hoy_ok < reserva.fecha_ingreso:
            return (
                False,
                f"No se puede finalizar la reserva {reserva.codigo}: su fecha de ingreso "
                f"({fecha_a_texto(reserva.fecha_ingreso)}) aún no llega.",
                None,
            )
        respaldo = self._a_dict()
        reserva.finalizar()
        return self._aceptar(respaldo, f"Reserva {reserva.codigo} finalizada (check-out)", reserva)
