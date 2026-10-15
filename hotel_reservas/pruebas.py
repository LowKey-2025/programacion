import os
import shutil
import tempfile
import unittest
from datetime import date

from almacenamiento import ErrorDeDatos
from datos_demo import crear_datos_demo
from hotel import Hotel
from modelo import ACTIVA, CANCELADA, FINALIZADA

HOY = date(2026, 10, 15)


class PruebasHotel(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        self.ruta = os.path.join(self.carpeta, "datos_hotel.json")
        self.hotel = crear_datos_demo(self.ruta)

    def tearDown(self):
        shutil.rmtree(self.carpeta)

    # Utilidades -------------------------------------------------------------
    def huella(self):
        """Contenido y fecha de modificación del archivo, para saber si se reescribió."""
        with open(self.ruta, "rb") as archivo:
            return archivo.read(), os.stat(self.ruta).st_mtime_ns

    def numeros(self, habitaciones):
        return [h.numero for h in habitaciones]

    # 1 -----------------------------------------------------------------------
    def test_01_registro_valido_de_huesped(self):
        exito, _, huesped = self.hotel.registrar_huesped(
            "52789456", "Carla Peña", "3001234567", "carla.pena@correo.com")
        self.assertTrue(exito)
        self.assertEqual(huesped.documento, "52789456")
        self.assertEqual(len(self.hotel.listar_huespedes()), 6)
        self.assertIsNotNone(Hotel(self.ruta).buscar_huesped("52789456"))  # se guardó

    # 2 -----------------------------------------------------------------------
    def test_02_huesped_duplicado(self):
        exito, mensaje, dato = self.hotel.registrar_huesped(
            "1116234567", "Otra Persona", "3000000000", "otra@correo.com")
        self.assertFalse(exito)
        self.assertIsNone(dato)
        self.assertIn("ya existe", mensaje.lower())
        self.assertEqual(len(self.hotel.listar_huespedes()), 5)
        self.assertEqual(self.hotel.buscar_huesped("1116234567").nombre, "Ana Ruiz")

    # 3 -----------------------------------------------------------------------
    def test_03_dato_invalido(self):
        exito, mensaje, _ = self.hotel.registrar_huesped(
            "52789456", "Carla Peña", "3001234567", "carla.correo")
        self.assertFalse(exito)
        self.assertIn("correo", mensaje.lower())
        self.assertIsNone(self.hotel.buscar_huesped("52789456"))

    # 4 -----------------------------------------------------------------------
    def test_04_busqueda_inexistente(self):
        self.assertIsNone(self.hotel.buscar_huesped("99999999"))

    # 5 -----------------------------------------------------------------------
    def test_05_lista_vacia_sin_archivo(self):
        ruta_nueva = os.path.join(self.carpeta, "no_existe.json")
        hotel = Hotel(ruta_nueva)
        self.assertEqual(hotel.listar_reservas(), [])
        self.assertEqual(hotel.listar_habitaciones(), [])
        self.assertFalse(os.path.exists(ruta_nueva))  # no se crea el archivo

    # 6 -----------------------------------------------------------------------
    def test_06_eliminacion_permitida(self):
        exito, _, _ = self.hotel.eliminar_habitacion("405")
        self.assertTrue(exito)
        self.assertEqual(len(self.hotel.listar_habitaciones()), 19)

    # 7 -----------------------------------------------------------------------
    def test_07_registro_valido_de_habitacion(self):
        self.hotel.eliminar_habitacion("405")
        exito, _, habitacion = self.hotel.registrar_habitacion("4", "5", "6")
        self.assertTrue(exito)
        self.assertEqual((habitacion.numero, habitacion.piso, habitacion.capacidad), (405, 4, 6))
        self.assertEqual(len(self.hotel.listar_habitaciones()), 20)

    # 8 -----------------------------------------------------------------------
    def test_08_habitacion_duplicada_y_fuera_de_rango(self):
        exito, mensaje, _ = self.hotel.registrar_habitacion("4", "5", "6")
        self.assertFalse(exito)
        self.assertIn("405 ya está registrada", mensaje)
        exito, mensaje, _ = self.hotel.registrar_habitacion("5", "1", "2")
        self.assertFalse(exito)
        self.assertIn("Piso", mensaje)
        self.assertEqual(len(self.hotel.listar_habitaciones()), 20)

    # 9 -----------------------------------------------------------------------
    def test_09_eliminacion_rechazada_por_historial(self):
        antes = self.huella()
        exito_hab, mensaje_hab, _ = self.hotel.eliminar_habitacion("301")
        exito_hue, mensaje_hue, _ = self.hotel.eliminar_huesped("1116234567")
        self.assertFalse(exito_hab)
        self.assertFalse(exito_hue)
        self.assertIn("historial", mensaje_hab)
        self.assertIn("historial", mensaje_hue)
        self.assertIsNotNone(self.hotel.buscar_habitacion("301"))
        self.assertEqual(self.huella(), antes)

    # 10 ----------------------------------------------------------------------
    def test_10_disponibilidad(self):
        exito, _, libres = self.hotel.habitaciones_disponibles("2026-10-20", "3", "4", hoy=HOY)
        self.assertTrue(exito)
        self.assertEqual(len(libres), 11)
        self.assertNotIn(203, self.numeros(libres))
        self.assertTrue(all(h.capacidad >= 4 for h in libres))

    # 11 ----------------------------------------------------------------------
    def test_11_reserva_valida(self):
        exito, mensaje, reserva = self.hotel.registrar_reserva(
            "31456789", "204", "2026-10-20", "2", "3", hoy=HOY)
        self.assertTrue(exito, mensaje)
        self.assertEqual(reserva.codigo, "R0004")
        self.assertEqual(reserva.estado, ACTIVA)
        self.assertEqual(reserva.fecha_salida, date(2026, 10, 22))
        self.assertEqual(self.hotel.siguiente_reserva, 5)
        self.assertEqual(mensaje, "Reserva R0004 registrada: habitación 204, salida 2026-10-22")

    # 12 ----------------------------------------------------------------------
    def test_12_conflicto_de_disponibilidad(self):
        antes = self.huella()
        exito, mensaje, dato = self.hotel.registrar_reserva(
            "94368120", "203", "2026-10-22", "2", "2", hoy=HOY)
        self.assertFalse(exito)
        self.assertIsNone(dato)
        self.assertIn("R0001", mensaje)
        self.assertEqual(self.hotel.siguiente_reserva, 4)
        self.assertEqual(len(self.hotel.listar_reservas()), 3)
        self.assertEqual(self.huella(), antes)

    # 13 ----------------------------------------------------------------------
    def test_13_borde_sin_conflicto(self):
        exito, mensaje, reserva = self.hotel.registrar_reserva(
            "94368120", "203", "2026-10-23", "2", "2", hoy=HOY)
        self.assertTrue(exito, mensaje)
        self.assertEqual(reserva.codigo, "R0004")

    # 14 ----------------------------------------------------------------------
    def test_14_capacidad_excedida(self):
        exito, mensaje, _ = self.hotel.registrar_reserva(
            "31456789", "101", "2026-10-25", "1", "3", hoy=HOY)
        self.assertFalse(exito)
        self.assertIn("supera la capacidad", mensaje)

    # 15 ----------------------------------------------------------------------
    def test_15_fecha_inexistente_y_fecha_pasada(self):
        exito_a, mensaje_a, _ = self.hotel.registrar_reserva(
            "31456789", "204", "2026-02-30", "2", "2", hoy=HOY)
        exito_b, mensaje_b, _ = self.hotel.registrar_reserva(
            "31456789", "204", "2026-10-01", "2", "2", hoy=HOY)
        self.assertFalse(exito_a)
        self.assertFalse(exito_b)
        self.assertIn("inválida", mensaje_a)
        self.assertIn("anterior a hoy", mensaje_b)
        self.assertNotEqual(mensaje_a, mensaje_b)

    # 16 ----------------------------------------------------------------------
    def test_16_cancelar_y_comprobar_disponibilidad(self):
        exito, mensaje, reserva = self.hotel.cancelar_reserva("R0001")
        self.assertTrue(exito)
        self.assertEqual(mensaje, "Reserva R0001 cancelada")
        self.assertEqual(reserva.estado, CANCELADA)
        self.assertIn(reserva, self.hotel.listar_reservas())
        _, _, libres = self.hotel.habitaciones_disponibles("2026-10-20", "3", "4", hoy=HOY)
        self.assertEqual(len(libres), 12)
        self.assertIn(203, self.numeros(libres))

    # 17 ----------------------------------------------------------------------
    def test_17_cancelacion_repetida(self):
        self.hotel.cancelar_reserva("R0001")
        antes = self.huella()
        exito, mensaje, _ = self.hotel.cancelar_reserva("R0001")
        self.assertFalse(exito)
        self.assertEqual(mensaje, "La reserva R0001 ya está CANCELADA")
        self.assertEqual(self.huella(), antes)  # el archivo no se reescribe

    # 18 ----------------------------------------------------------------------
    def test_18_finalizar_y_repetir(self):
        exito1, _, reserva = self.hotel.finalizar_reserva("R0002", hoy=HOY)
        self.assertTrue(exito1)
        self.assertEqual(reserva.estado, FINALIZADA)
        exito2, mensaje2, _ = self.hotel.finalizar_reserva("R0002", hoy=HOY)
        self.assertFalse(exito2)
        self.assertIn("FINALIZADA", mensaje2)
        _, _, futura = self.hotel.registrar_reserva(
            "31456789", "204", "2026-10-23", "2", "2", hoy=HOY)
        exito3, mensaje3, _ = self.hotel.finalizar_reserva(futura.codigo, hoy=HOY)
        self.assertFalse(exito3)
        self.assertIn("aún no llega", mensaje3)

    # 19 ----------------------------------------------------------------------
    def test_19_cambio_bloqueado_en_datos_principales(self):
        exito, mensaje, _ = self.hotel.actualizar_habitacion("105", "4")
        self.assertFalse(exito)
        self.assertIn("R0002", mensaje)
        self.assertEqual(self.hotel.buscar_habitacion("105").capacidad, 6)

    # 20 ----------------------------------------------------------------------
    def test_20a_persistencia(self):
        self.hotel.registrar_reserva("31456789", "204", "2026-10-20", "2", "3", hoy=HOY)
        self.hotel.cancelar_reserva("R0001")
        recargado = Hotel(self.ruta)
        self.assertEqual(recargado.siguiente_reserva, 5)
        estados = {r.codigo: r.estado for r in recargado.listar_reservas()}
        self.assertEqual(estados, {"R0001": CANCELADA, "R0002": ACTIVA,
                                   "R0003": CANCELADA, "R0004": ACTIVA})
        r4 = recargado.buscar_reserva("R0004")
        self.assertEqual(r4.huesped.nombre, "Marta Gil")
        # La relación es una referencia al mismo objeto huésped, no una copia
        self.assertIs(r4.huesped, recargado.buscar_huesped("31456789"))

    def test_20b_archivo_danado(self):
        with open(self.ruta, "r+", encoding="utf-8") as archivo:
            contenido = archivo.read()
            archivo.seek(0)
            archivo.write(contenido[: len(contenido) // 2])
            archivo.truncate()
        antes = self.huella()
        with self.assertRaises(ErrorDeDatos):
            Hotel(self.ruta)
        self.assertEqual(self.huella(), antes)

    # Extra: reserva que apunta a un huésped inexistente -----------------------
    def test_extra_reserva_huerfana(self):
        with open(self.ruta, encoding="utf-8") as archivo:
            contenido = archivo.read()
        with open(self.ruta, "w", encoding="utf-8") as archivo:
            archivo.write(contenido.replace('"documento_huesped": "94368120"',
                                            '"documento_huesped": "11111111"'))
        with self.assertRaises(ErrorDeDatos) as contexto:
            Hotel(self.ruta)
        self.assertIn("11111111", str(contexto.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)
