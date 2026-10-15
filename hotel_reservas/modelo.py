from datetime import timedelta

from validaciones import (
    convertir_entero,
    convertir_fecha,
    fecha_a_texto,
    validar_correo,
    validar_documento,
    validar_nombre,
    validar_telefono,
)

# Estados de una reserva
ACTIVA = "ACTIVA"
CANCELADA = "CANCELADA"
FINALIZADA = "FINALIZADA"
ESTADOS = (ACTIVA, CANCELADA, FINALIZADA)

# Reglas fijas del hotel
CAPACIDADES = (2, 4, 6)
PISO_MIN, PISO_MAX = 1, 4
POSICION_MIN, POSICION_MAX = 1, 5


class Habitacion:
    """Recurso que se reserva. Conoce su número, piso y capacidad."""

    def __init__(self, numero, piso, capacidad):
        if not (PISO_MIN <= piso <= PISO_MAX):
            raise ValueError(f"piso {piso} fuera de {PISO_MIN} a {PISO_MAX}")
        posicion = numero - piso * 100
        if not (POSICION_MIN <= posicion <= POSICION_MAX):
            raise ValueError(f"el número {numero} no corresponde al piso {piso}")
        if capacidad not in CAPACIDADES:
            raise ValueError(f"capacidad {capacidad} no es 2, 4 o 6")
        self._numero = numero
        self._piso = piso
        self._capacidad = capacidad

    @property
    def numero(self):
        return self._numero

    @property
    def piso(self):
        return self._piso

    @property
    def posicion(self):
        return self._numero - self._piso * 100

    @property
    def capacidad(self):
        return self._capacidad

    def admite(self, personas):
        """True si el número de personas está entre 1 y la capacidad."""
        return 1 <= personas <= self._capacidad

    def cambiar_capacidad(self, capacidad):
        """Cambia la capacidad si es 2, 4 o 6. Devuelve True si la cambió."""
        if capacidad not in CAPACIDADES:
            return False
        self._capacidad = capacidad
        return True

    def a_dict(self):
        return {"numero": self._numero, "piso": self._piso, "capacidad": self._capacidad}

    @classmethod
    def desde_dict(cls, datos):
        numero = convertir_entero(datos["numero"])
        piso = convertir_entero(datos["piso"])
        capacidad = convertir_entero(datos["capacidad"])
        if None in (numero, piso, capacidad):
            raise ValueError(f"habitación con datos no numéricos: {datos}")
        return cls(numero, piso, capacidad)

    def __repr__(self):
        return f"Habitacion({self._numero}, piso={self._piso}, capacidad={self._capacidad})"


class Huesped:
    """Datos de identificación y contacto de una persona."""

    def __init__(self, documento, nombre, telefono, correo):
        documento_ok = validar_documento(documento)
        if documento_ok is None:
            raise ValueError(f"documento inválido: {documento!r}")
        self._documento = documento_ok
        self._nombre = None
        self._telefono = None
        self._correo = None
        if not self.actualizar_datos(nombre, telefono, correo):
            raise ValueError(f"datos de contacto inválidos para el huésped {documento}")

    @property
    def documento(self):
        return self._documento

    @property
    def nombre(self):
        return self._nombre

    @property
    def telefono(self):
        return self._telefono

    @property
    def correo(self):
        return self._correo

    def actualizar_datos(self, nombre, telefono, correo):
        """Cambia nombre, teléfono y correo si los tres son válidos.

        Devuelve True si cambió; False si alguno es inválido (y no cambia nada).
        """
        nombre_ok = validar_nombre(nombre)
        telefono_ok = validar_telefono(telefono)
        correo_ok = validar_correo(correo)
        if None in (nombre_ok, telefono_ok, correo_ok):
            return False
        self._nombre = nombre_ok
        self._telefono = telefono_ok
        self._correo = correo_ok
        return True

    def a_dict(self):
        return {
            "documento": self._documento,
            "nombre": self._nombre,
            "telefono": self._telefono,
            "correo": self._correo,
        }

    @classmethod
    def desde_dict(cls, datos):
        return cls(datos["documento"], datos["nombre"], datos["telefono"], datos["correo"])

    def __repr__(self):
        return f"Huesped({self._documento}, {self._nombre!r})"


class Reserva:
    """Une un huésped con una habitación durante unas noches."""

    def __init__(self, codigo, huesped, habitacion, fecha_ingreso, dias, personas, estado=ACTIVA):
        if estado not in ESTADOS:
            raise ValueError(f"estado desconocido: {estado!r}")
        if dias < 1:
            raise ValueError("los días de estadía deben ser al menos 1")
        if personas < 1:
            raise ValueError("debe haber al menos una persona")
        self._codigo = codigo
        self._huesped = huesped
        self._habitacion = habitacion
        self._fecha_ingreso = fecha_ingreso
        self._dias = dias
        self._personas = personas
        self._estado = estado

    # --- Lectura -----------------------------------------------------------
    @property
    def codigo(self):
        return self._codigo

    @property
    def huesped(self):
        return self._huesped

    @property
    def habitacion(self):
        return self._habitacion

    @property
    def fecha_ingreso(self):
        return self._fecha_ingreso

    @property
    def dias(self):
        return self._dias

    @property
    def personas(self):
        return self._personas

    @property
    def estado(self):
        return self._estado

    @property
    def activa(self):
        return self._estado == ACTIVA

    @property
    def fecha_salida(self):
        """Fecha de salida = fecha de ingreso + días de estadía."""
        return self._fecha_ingreso + timedelta(days=self._dias)

    # --- Reglas propias ----------------------------------------------------
    def noches(self):
        """Noches ocupadas: desde el ingreso hasta el día anterior a la salida."""
        return [self._fecha_ingreso + timedelta(days=i) for i in range(self._dias)]

    def coincide_con(self, fecha_ingreso, dias):
        """True si comparte al menos una noche con la estadía indicada."""
        pedidas = {fecha_ingreso + timedelta(days=i) for i in range(dias)}
        return not pedidas.isdisjoint(self.noches())

    def cancelar(self):
        """ACTIVA → CANCELADA. Devuelve False sin cambiar nada si no estaba ACTIVA."""
        if self._estado != ACTIVA:
            return False
        self._estado = CANCELADA
        return True

    def finalizar(self):
        """ACTIVA → FINALIZADA. Devuelve False sin cambiar nada si no estaba ACTIVA."""
        if self._estado != ACTIVA:
            return False
        self._estado = FINALIZADA
        return True

    # --- Presentación y persistencia --------------------------------------
    def detalle(self):
        """Texto con el detalle completo; consola y GUI lo muestran igual."""
        h = self._huesped
        return (
            f"Reserva {self._codigo}\n"
            f"  Huésped:     {h.nombre} (documento {h.documento})\n"
            f"  Contacto:    {h.telefono} · {h.correo}\n"
            f"  Habitación:  {self._habitacion.numero} (piso {self._habitacion.piso}, "
            f"capacidad {self._habitacion.capacidad})\n"
            f"  Ingreso:     {fecha_a_texto(self._fecha_ingreso)}\n"
            f"  Salida:      {fecha_a_texto(self.fecha_salida)}\n"
            f"  Días:        {self._dias}\n"
            f"  Personas:    {self._personas}\n"
            f"  Estado:      {self._estado}"
        )

    def a_dict(self):
        return {
            "codigo": self._codigo,
            "documento_huesped": self._huesped.documento,
            "numero_habitacion": self._habitacion.numero,
            "fecha_ingreso": fecha_a_texto(self._fecha_ingreso),
            "dias": self._dias,
            "personas": self._personas,
            "estado": self._estado,
        }

    @classmethod
    def desde_dict(cls, datos, huesped, habitacion):
        """Reconstruye una reserva guardada. No aplica la regla «no anterior a hoy»."""
        fecha = convertir_fecha(datos["fecha_ingreso"])
        dias = convertir_entero(datos["dias"], 1)
        personas = convertir_entero(datos["personas"], 1)
        if fecha is None or dias is None or personas is None:
            raise ValueError(f"reserva {datos.get('codigo')} con fecha, días o personas inválidos")
        return cls(datos["codigo"], huesped, habitacion, fecha, dias, personas, datos["estado"])

    def __repr__(self):
        return f"Reserva({self._codigo}, hab={self._habitacion.numero}, {self._estado})"
