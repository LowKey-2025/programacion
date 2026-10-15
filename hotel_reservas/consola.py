import sys

from almacenamiento import ErrorDeDatos
from hotel import Hotel
from validaciones import fecha_a_texto

LINEA = "-" * 78


# ---------------------------------------------------------------------------
# Utilidades de impresión
# ---------------------------------------------------------------------------
def pedir(texto):
    try:
        return input(f"  {texto}: ")
    except (EOFError, KeyboardInterrupt):
        print("\n\n  Programa cerrado. Todos los cambios ya quedaron guardados.\n")
        sys.exit(0)


def confirmar(pregunta):
    while True:
        respuesta = pedir(f"{pregunta} (s/n)").strip().lower()
        if respuesta in ("s", "n"):
            return respuesta == "s"
        print("  Responda s o n.")


def mostrar_resultado(resultado):
    exito, mensaje, _ = resultado
    print(f"\n  {'✔' if exito else '✘'} {mensaje}\n")


def tabla(encabezados, filas, vacio):
    if not filas:
        print(f"\n  {vacio}\n")
        return
    anchos = [len(e) for e in encabezados]
    for fila in filas:
        for i, valor in enumerate(fila):
            anchos[i] = max(anchos[i], len(str(valor)))
    formato = "  " + "  ".join(f"{{:<{a}}}" for a in anchos)
    print()
    print(formato.format(*encabezados))
    print("  " + "  ".join("-" * a for a in anchos))
    for fila in filas:
        print(formato.format(*[str(v) for v in fila]))
    print(f"\n  Total: {len(filas)}\n")


def filas_habitaciones(habitaciones):
    return [(h.numero, h.piso, h.capacidad) for h in habitaciones]


def tabla_habitaciones(habitaciones, vacio="No hay habitaciones registradas"):
    tabla(("Número", "Piso", "Capacidad"), filas_habitaciones(habitaciones), vacio)


def tabla_huespedes(huespedes, vacio="No hay huéspedes registrados"):
    filas = [(h.documento, h.nombre, h.telefono, h.correo) for h in huespedes]
    tabla(("Documento", "Nombre", "Teléfono", "Correo"), filas, vacio)


def tabla_reservas(reservas, vacio="No hay reservas registradas"):
    filas = [
        (r.codigo, r.huesped.nombre, r.habitacion.numero, fecha_a_texto(r.fecha_ingreso),
         fecha_a_texto(r.fecha_salida), r.dias, r.personas, r.estado)
        for r in reservas
    ]
    tabla(("Código", "Huésped", "Hab.", "Ingreso", "Salida", "Días", "Pers.", "Estado"),
          filas, vacio)


def elegir(titulo, opciones):
    """Muestra un submenú con letras y devuelve la letra elegida."""
    print(LINEA)
    print(f"  {titulo}")
    print(LINEA)
    for letra, texto in opciones:
        print(f"  {letra}. {texto}")
    return pedir("Opción").strip().lower()


# ---------------------------------------------------------------------------
# Submenú 1: Habitaciones
# ---------------------------------------------------------------------------
def menu_habitaciones(hotel):
    opciones = [
        ("a", "Registrar habitación"), ("b", "Listar habitaciones"),
        ("c", "Buscar por número"), ("d", "Actualizar capacidad"),
        ("e", "Eliminar habitación"), ("f", "Volver"),
    ]
    while True:
        opcion = elegir("HABITACIONES", opciones)
        if opcion == "a":
            piso = pedir("Piso (1 a 4)")
            posicion = pedir("Posición en el piso (1 a 5)")
            capacidad = pedir("Capacidad (2, 4 o 6)")
            mostrar_resultado(hotel.registrar_habitacion(piso, posicion, capacidad))
        elif opcion == "b":
            tabla_habitaciones(hotel.listar_habitaciones())
        elif opcion == "c":
            numero = pedir("Número de habitación")
            habitacion = hotel.buscar_habitacion(numero)
            if habitacion is None:
                print(f"\n  No se encontró la habitación {numero.strip()}\n")
            else:
                tabla_habitaciones([habitacion])
        elif opcion == "d":
            numero = pedir("Número de habitación")
            capacidad = pedir("Nueva capacidad (2, 4 o 6)")
            mostrar_resultado(hotel.actualizar_habitacion(numero, capacidad))
        elif opcion == "e":
            numero = pedir("Número de habitación a eliminar")
            if confirmar(f"¿Eliminar la habitación {numero.strip()}?"):
                mostrar_resultado(hotel.eliminar_habitacion(numero))
            else:
                print("\n  Operación cancelada por el usuario.\n")
        elif opcion == "f":
            return
        else:
            print("\n  Opción no válida\n")


# ---------------------------------------------------------------------------
# Submenú 2: Huéspedes
# ---------------------------------------------------------------------------
def menu_huespedes(hotel):
    opciones = [
        ("a", "Registrar huésped"), ("b", "Listar huéspedes"),
        ("c", "Buscar por documento"), ("d", "Buscar por nombre"),
        ("e", "Actualizar datos de contacto"), ("f", "Eliminar huésped"), ("g", "Volver"),
    ]
    while True:
        opcion = elegir("HUÉSPEDES", opciones)
        if opcion == "a":
            documento = pedir("Documento (6 a 10 dígitos)")
            nombre = pedir("Nombre")
            telefono = pedir("Teléfono (7 a 10 dígitos)")
            correo = pedir("Correo")
            mostrar_resultado(hotel.registrar_huesped(documento, nombre, telefono, correo))
        elif opcion == "b":
            tabla_huespedes(hotel.listar_huespedes())
        elif opcion == "c":
            documento = pedir("Documento")
            huesped = hotel.buscar_huesped(documento)
            if huesped is None:
                print(f"\n  No se encontró el huésped {documento.strip()}\n")
            else:
                tabla_huespedes([huesped])
        elif opcion == "d":
            texto = pedir("Nombre o parte del nombre")
            tabla_huespedes(hotel.buscar_huespedes_por_nombre(texto),
                            vacio=f"No se encontró ningún huésped con «{texto.strip()}»")
        elif opcion == "e":
            documento = pedir("Documento del huésped")
            huesped = hotel.buscar_huesped(documento)
            if huesped is None:
                print(f"\n  No se encontró el huésped {documento.strip()}\n")
                continue
            print(f"  (Enter para conservar el valor actual)")
            nombre = pedir(f"Nombre [{huesped.nombre}]") or huesped.nombre
            telefono = pedir(f"Teléfono [{huesped.telefono}]") or huesped.telefono
            correo = pedir(f"Correo [{huesped.correo}]") or huesped.correo
            mostrar_resultado(hotel.actualizar_huesped(documento, nombre, telefono, correo))
        elif opcion == "f":
            documento = pedir("Documento del huésped a eliminar")
            if confirmar(f"¿Eliminar al huésped {documento.strip()}?"):
                mostrar_resultado(hotel.eliminar_huesped(documento))
            else:
                print("\n  Operación cancelada por el usuario.\n")
        elif opcion == "g":
            return
        else:
            print("\n  Opción no válida\n")


# ---------------------------------------------------------------------------
# Submenú 3: Reservas
# ---------------------------------------------------------------------------
def menu_reservas(hotel):
    opciones = [
        ("a", "Consultar habitaciones disponibles"), ("b", "Registrar reserva"),
        ("c", "Listar reservas (todas, activas, canceladas o finalizadas)"),
        ("d", "Buscar por código"), ("e", "Historial de un huésped"),
        ("f", "Historial de una habitación"), ("g", "Cancelar reserva"),
        ("h", "Finalizar reserva (check-out)"), ("i", "Volver"),
    ]
    while True:
        opcion = elegir("RESERVAS", opciones)
        if opcion == "a":
            fecha = pedir("Fecha de ingreso (AAAA-MM-DD)")
            dias = pedir("Días de estadía (1 a 30)")
            personas = pedir("Personas")
            exito, mensaje, libres = hotel.habitaciones_disponibles(fecha, dias, personas)
            print(f"\n  {'✔' if exito else '✘'} {mensaje}")
            if exito and libres:
                tabla_habitaciones(libres)
            else:
                print()
        elif opcion == "b":
            documento = pedir("Documento del huésped")
            numero = pedir("Número de habitación")
            fecha = pedir("Fecha de ingreso (AAAA-MM-DD)")
            dias = pedir("Días de estadía (1 a 30)")
            personas = pedir("Personas")
            mostrar_resultado(hotel.registrar_reserva(documento, numero, fecha, dias, personas))
        elif opcion == "c":
            print("  Filtro: 1. Todas  2. Activas  3. Canceladas  4. Finalizadas")
            filtro = pedir("Opción").strip()
            estados = {"1": None, "2": "ACTIVA", "3": "CANCELADA", "4": "FINALIZADA"}
            if filtro not in estados:
                print("\n  Opción no válida\n")
                continue
            estado = estados[filtro]
            vacio = ("No hay reservas registradas" if estado is None
                     else f"No hay reservas en estado {estado}")
            tabla_reservas(hotel.listar_reservas(estado), vacio)
        elif opcion == "d":
            codigo = pedir("Código de reserva (ej. R0001)")
            reserva = hotel.buscar_reserva(codigo)
            if reserva is None:
                print(f"\n  No se encontró la reserva {codigo.strip().upper()}\n")
            else:
                print("\n" + "\n".join("  " + l for l in reserva.detalle().splitlines()) + "\n")
        elif opcion == "e":
            documento = pedir("Documento del huésped")
            huesped = hotel.buscar_huesped(documento)
            if huesped is None:
                print(f"\n  No se encontró el huésped {documento.strip()}\n")
            else:
                print(f"\n  Historial de {huesped.nombre} ({huesped.documento})")
                tabla_reservas(hotel.reservas_de_huesped(documento),
                               f"{huesped.nombre} no tiene reservas")
        elif opcion == "f":
            numero = pedir("Número de habitación")
            habitacion = hotel.buscar_habitacion(numero)
            if habitacion is None:
                print(f"\n  No se encontró la habitación {numero.strip()}\n")
            else:
                print(f"\n  Historial de la habitación {habitacion.numero}")
                tabla_reservas(hotel.reservas_de_habitacion(numero),
                               f"La habitación {habitacion.numero} no tiene reservas")
        elif opcion == "g":
            codigo = pedir("Código de la reserva a cancelar")
            if confirmar(f"¿Cancelar la reserva {codigo.strip().upper()}?"):
                mostrar_resultado(hotel.cancelar_reserva(codigo))
            else:
                print("\n  Operación cancelada por el usuario.\n")
        elif opcion == "h":
            codigo = pedir("Código de la reserva a finalizar")
            if confirmar(f"¿Finalizar (check-out) la reserva {codigo.strip().upper()}?"):
                mostrar_resultado(hotel.finalizar_reserva(codigo))
            else:
                print("\n  Operación cancelada por el usuario.\n")
        elif opcion == "i":
            return
        else:
            print("\n  Opción no válida\n")


# ---------------------------------------------------------------------------
# Menú principal
# ---------------------------------------------------------------------------
def main(ruta=None):
    try:
        hotel = Hotel(ruta) if ruta else Hotel()
    except ErrorDeDatos as error:
        print(f"\nNo se pudieron cargar los datos.\n{error}")
        print("El archivo no se modificó. Revíselo o renómbrelo y vuelva a iniciar el programa.")
        sys.exit(1)

    menus = {"1": menu_habitaciones, "2": menu_huespedes, "3": menu_reservas}
    while True:
        print("=" * 78)
        print("  SISTEMA DE RESERVAS DE HOTEL")
        print("=" * 78)
        print("  1. Habitaciones\n  2. Huéspedes\n  3. Reservas\n  0. Salir")
        opcion = pedir("Opción").strip()
        if opcion == "0":
            print("\n  Hasta luego. Todos los cambios ya quedaron guardados.\n")
            return
        if opcion in menus:
            menus[opcion](hotel)
        else:
            print("\n  Opción no válida\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
