import os
import sys

from almacenamiento import escribir_datos
from hotel import RUTA_POR_DEFECTO, Hotel

CAPACIDAD_POR_POSICION = {1: 2, 2: 2, 3: 4, 4: 4, 5: 6}


def datos_demostracion():
    habitaciones = [
        {"numero": piso * 100 + pos, "piso": piso, "capacidad": CAPACIDAD_POR_POSICION[pos]}
        for piso in range(1, 5)
        for pos in range(1, 6)
    ]
    huespedes = [
        {"documento": "1116234567", "nombre": "Ana Ruiz",
         "telefono": "3104567890", "correo": "ana.ruiz@correo.com"},
        {"documento": "94368120", "nombre": "Luis Mora",
         "telefono": "3157654321", "correo": "luis.mora@correo.com"},
        {"documento": "31456789", "nombre": "Marta Gil",
         "telefono": "3209876543", "correo": "marta.gil@correo.com"},
        {"documento": "1094567321", "nombre": "Jorge Díaz",
         "telefono": "3112223344", "correo": "jorge.diaz@correo.com"},
        {"documento": "66987123", "nombre": "Sofía Lara",
         "telefono": "3185556677", "correo": "sofia.lara@correo.com"},
    ]
    reservas = [
        {"codigo": "R0001", "documento_huesped": "1116234567", "numero_habitacion": 203,
         "fecha_ingreso": "2026-10-20", "dias": 3, "personas": 2, "estado": "ACTIVA"},
        {"codigo": "R0002", "documento_huesped": "94368120", "numero_habitacion": 105,
         "fecha_ingreso": "2026-10-12", "dias": 4, "personas": 5, "estado": "ACTIVA"},
        {"codigo": "R0003", "documento_huesped": "1116234567", "numero_habitacion": 301,
         "fecha_ingreso": "2026-10-18", "dias": 2, "personas": 1, "estado": "CANCELADA"},
    ]
    return {"siguiente_reserva": 4, "habitaciones": habitaciones,
            "huespedes": huespedes, "reservas": reservas}


def crear_datos_demo(ruta=RUTA_POR_DEFECTO):
    """Escribe los datos de demostración y comprueba que carguen sin errores."""
    escribir_datos(ruta, datos_demostracion())
    return Hotel(ruta)


if __name__ == "__main__":
    ruta = RUTA_POR_DEFECTO
    if os.path.exists(ruta) and "--forzar" not in sys.argv:
        respuesta = input(f"«{ruta}» ya existe. ¿Reemplazarlo por los datos de demostración? (s/n): ")
        if respuesta.strip().lower() != "s":
            print("No se modificó el archivo.")
            sys.exit(0)
    hotel = crear_datos_demo(ruta)
    print(f"Datos de demostración creados en «{ruta}»: "
          f"{len(hotel.listar_habitaciones())} habitaciones, "
          f"{len(hotel.listar_huespedes())} huéspedes, {len(hotel.listar_reservas())} reservas.")
