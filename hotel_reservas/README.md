# Proyecto 2 — Sistema de reservas de hotel

MVP local en Python 3 (sin librerías externas) con consola y GUI Tkinter sobre la misma lógica.
Implementa el diseño del documento «Proyecto 2 — análisis y diseño».

## Archivos

| Archivo | Capa | Contenido |
|---|---|---|
| `validaciones.py` | Modelo (apoyo) | `convertir_fecha`, `convertir_entero`, validación de documento, nombre, teléfono y correo |
| `modelo.py` | Modelo | Clases `Habitacion`, `Huesped`, `Reserva` (atributos privados + `@property`) |
| `almacenamiento.py` | Almacenamiento | `leer_datos`, `escribir_datos`, excepción `ErrorDeDatos` (solo `json` y `os`) |
| `hotel.py` | Gestión | Clase `Hotel`: colecciones, CRUD, reglas del negocio y guardado automático |
| `consola.py` | Interacción | Menú principal con 3 submenús y 19 opciones |
| `gui.py` | Interacción | Ventana Tkinter con 4 pestañas (Habitaciones, Huéspedes, Reservas, Disponibilidad) |
| `datos_demo.py` | Apoyo | Crea `datos_hotel.json` con los datos de demostración de la sección 11 |
| `pruebas.py` | Pruebas | Las 20 pruebas de la sección 11 con `unittest` |
| `datos_hotel.json` | Datos | Archivo de datos (ya trae los datos de demostración) |

## Cómo ejecutar

```bash
python consola.py              # interfaz de consola
python gui.py                  # interfaz gráfica
python datos_demo.py --forzar  # restaurar los datos de demostración
python -m unittest pruebas -v  # correr las 20 pruebas (usan hoy = 2026-10-15)
```

En Linux, si falta Tkinter: `sudo apt install python3-tk`. En Windows y macOS viene con Python.

## Decisiones de implementación

- Toda operación de `Hotel` devuelve `(exito, mensaje, dato)`; consola y GUI muestran el mismo mensaje.
- Una operación rechazada no cambia nada ni escribe el archivo. Si la escritura falla, el cambio se deshace.
- El JSON se escribe primero en un temporal y luego se reemplaza, para que un corte nunca deje el archivo a medias.
- La disponibilidad se calcula siempre desde las reservas ACTIVAS; la habitación no tiene atributo «ocupada».
- Al cargar se verifica la consistencia: reservas que apuntan a huéspedes/habitaciones inexistentes,
  duplicados, consecutivo menor que el último código o dos reservas ACTIVAS que se cruzan → `ErrorDeDatos`.
- `habitaciones_disponibles`, `registrar_reserva` y `finalizar_reserva` aceptan `hoy=` para probar con fechas fijas.
