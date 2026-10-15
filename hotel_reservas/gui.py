import sys
import tkinter as tk
from datetime import date
from tkinter import messagebox, ttk

from almacenamiento import ErrorDeDatos
from hotel import Hotel
from modelo import CAPACIDADES, ESTADOS
from validaciones import fecha_a_texto

FILA_VACIA = "__vacio__"


# ---------------------------------------------------------------------------
# Piezas reutilizables
# ---------------------------------------------------------------------------
def crear_tabla(padre, columnas, anchos):
    """Treeview con barra de desplazamiento. Devuelve (marco, tabla)."""
    marco = ttk.Frame(padre)
    tabla = ttk.Treeview(marco, columns=columnas, show="headings", selectmode="browse", height=16)
    for columna, ancho in zip(columnas, anchos):
        tabla.heading(columna, text=columna)
        tabla.column(columna, width=ancho, anchor="w", stretch=True)
    barra = ttk.Scrollbar(marco, orient="vertical", command=tabla.yview)
    tabla.configure(yscrollcommand=barra.set)
    tabla.grid(row=0, column=0, sticky="nsew")
    barra.grid(row=0, column=1, sticky="ns")
    marco.columnconfigure(0, weight=1)
    marco.rowconfigure(0, weight=1)
    tabla.tag_configure("vacio", foreground="gray")
    return marco, tabla


def llenar_tabla(tabla, filas):
    """Reemplaza las filas. Cada fila es (iid, valores). Sin filas: «Sin registros»."""
    tabla.delete(*tabla.get_children())
    if not filas:
        columnas = tabla["columns"]
        tabla.insert("", "end", iid=FILA_VACIA, values=["Sin registros"] + [""] * (len(columnas) - 1),
                     tags=("vacio",))
        return
    for iid, valores in filas:
        tabla.insert("", "end", iid=str(iid), values=valores)


def seleccion(tabla):
    """iid de la fila seleccionada, o None (la fila «Sin registros» no cuenta)."""
    elegidas = tabla.selection()
    if not elegidas or elegidas[0] == FILA_VACIA:
        return None
    return elegidas[0]


def campo(padre, fila, etiqueta, ancho=24, variable=None):
    ttk.Label(padre, text=etiqueta).grid(row=fila, column=0, sticky="w", padx=4, pady=3)
    variable = variable or tk.StringVar()
    entrada = ttk.Entry(padre, textvariable=variable, width=ancho)
    entrada.grid(row=fila, column=1, sticky="we", padx=4, pady=3)
    return variable, entrada


def ventana_lectura(padre, titulo, texto):
    """Ventana secundaria de solo lectura con un botón Cerrar."""
    ventana = tk.Toplevel(padre)
    ventana.title(titulo)
    ventana.transient(padre)
    lineas = texto.splitlines() or [""]
    caja = tk.Text(ventana, width=max(60, max(len(l) for l in lineas) + 2),
                   height=min(30, len(lineas) + 2), font=("Courier", 10), wrap="none")
    caja.insert("1.0", texto)
    caja.configure(state="disabled")
    caja.pack(fill="both", expand=True, padx=10, pady=(10, 4))
    ttk.Button(ventana, text="Cerrar", command=ventana.destroy).pack(pady=(0, 10))
    ventana.grab_set()
    ventana.focus_set()


def texto_historial(titulo, reservas, vacio):
    if not reservas:
        return f"{titulo}\n\n{vacio}"
    lineas = [titulo, "",
              f"{'Código':<7} {'Huésped':<22} {'Hab.':<5} {'Ingreso':<11} {'Salida':<11} "
              f"{'Días':<5} {'Pers.':<6} Estado",
              "-" * 82]
    for r in reservas:
        lineas.append(
            f"{r.codigo:<7} {r.huesped.nombre[:22]:<22} {r.habitacion.numero:<5} "
            f"{fecha_a_texto(r.fecha_ingreso):<11} {fecha_a_texto(r.fecha_salida):<11} "
            f"{r.dias:<5} {r.personas:<6} {r.estado}"
        )
    lineas += ["", f"Total: {len(reservas)}"]
    return "\n".join(lineas)


class Pestana(ttk.Frame):
    """Base común: formulario (izq.), tabla (der.), acciones (abajo)."""

    def __init__(self, notebook, app):
        super().__init__(notebook, padding=10)
        self.app = app
        self.hotel = app.hotel
        self.formulario = ttk.LabelFrame(self, text="Datos", padding=8)
        self.formulario.grid(row=0, column=0, sticky="nw", padx=(0, 10))
        self.derecha = ttk.Frame(self)
        self.derecha.grid(row=0, column=1, rowspan=2, sticky="nsew")
        self.derecha.columnconfigure(0, weight=1)
        self.derecha.rowconfigure(1, weight=1)
        self.acciones = ttk.LabelFrame(self, text="Acciones", padding=8)
        self.acciones.grid(row=1, column=0, sticky="new", padx=(0, 10), pady=(10, 0))
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

    def boton(self, texto, comando):
        b = ttk.Button(self.acciones, text=texto, command=comando)
        b.pack(fill="x", pady=2)
        return b

    def ejecutar(self, resultado):
        """Muestra el mensaje de Hotel y recarga. Devuelve el dato."""
        exito, mensaje, dato = resultado
        self.app.mostrar_resultado(exito, mensaje)
        self.refrescar()
        return dato

    def refrescar(self):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Pestaña Habitaciones
# ---------------------------------------------------------------------------
class PestanaHabitaciones(Pestana):
    def __init__(self, notebook, app):
        super().__init__(notebook, app)
        self.piso, _ = campo(self.formulario, 0, "Piso (1 a 4)", 10)
        self.posicion, _ = campo(self.formulario, 1, "Posición (1 a 5)", 10)
        ttk.Label(self.formulario, text="Capacidad").grid(row=2, column=0, sticky="w", padx=4, pady=3)
        self.capacidad = tk.StringVar(value=str(CAPACIDADES[0]))
        ttk.Combobox(self.formulario, textvariable=self.capacidad, width=8, state="readonly",
                     values=[str(c) for c in CAPACIDADES]).grid(row=2, column=1, sticky="w", padx=4)
        ttk.Button(self.formulario, text="Limpiar", command=self.limpiar).grid(
            row=3, column=1, sticky="e", pady=(8, 0))

        self.boton("Registrar", self.registrar)
        self.boton("Actualizar capacidad", self.actualizar)
        self.boton("Eliminar", self.eliminar)
        self.boton("Ver historial", self.ver_historial)

        busqueda = ttk.Frame(self.derecha)
        busqueda.grid(row=0, column=0, sticky="we", pady=(0, 6))
        ttk.Label(busqueda, text="Buscar por número:").pack(side="left")
        self.buscado = tk.StringVar()
        entrada = ttk.Entry(busqueda, textvariable=self.buscado, width=10)
        entrada.pack(side="left", padx=4)
        entrada.bind("<Return>", lambda _e: self.buscar())
        ttk.Button(busqueda, text="Buscar", command=self.buscar).pack(side="left")
        ttk.Button(busqueda, text="Ver todas", command=self.refrescar).pack(side="left", padx=4)

        marco, self.tabla = crear_tabla(self.derecha, ("Número", "Piso", "Capacidad"), (120, 100, 120))
        marco.grid(row=1, column=0, sticky="nsew")
        self.tabla.bind("<<TreeviewSelect>>", self.al_seleccionar)

    def _filas(self, habitaciones):
        return [(h.numero, (h.numero, h.piso, h.capacidad)) for h in habitaciones]

    def refrescar(self):
        llenar_tabla(self.tabla, self._filas(self.hotel.listar_habitaciones()))

    def buscar(self):
        habitacion = self.hotel.buscar_habitacion(self.buscado.get())
        if habitacion is None:
            self.app.mostrar_resultado(False, f"No se encontró la habitación {self.buscado.get().strip()}")
            llenar_tabla(self.tabla, [])
        else:
            llenar_tabla(self.tabla, self._filas([habitacion]))
            self.app.barra.set(f"Habitación {habitacion.numero} encontrada.")

    def al_seleccionar(self, _evento=None):
        numero = seleccion(self.tabla)
        habitacion = self.hotel.buscar_habitacion(numero) if numero else None
        if habitacion:
            self.piso.set(str(habitacion.piso))
            self.posicion.set(str(habitacion.posicion))
            self.capacidad.set(str(habitacion.capacidad))

    def limpiar(self):
        self.piso.set("")
        self.posicion.set("")
        self.capacidad.set(str(CAPACIDADES[0]))
        self.tabla.selection_remove(*self.tabla.selection())

    def _numero_seleccionado(self):
        numero = seleccion(self.tabla)
        if numero is None:
            self.app.mostrar_resultado(False, "Seleccione una habitación en la tabla.")
        return numero

    def registrar(self):
        self.ejecutar(self.hotel.registrar_habitacion(self.piso.get(), self.posicion.get(),
                                                      self.capacidad.get()))

    def actualizar(self):
        numero = self._numero_seleccionado()
        if numero:
            self.ejecutar(self.hotel.actualizar_habitacion(numero, self.capacidad.get()))

    def eliminar(self):
        numero = self._numero_seleccionado()
        if numero and self.app.confirmar(f"¿Eliminar la habitación {numero}?"):
            self.ejecutar(self.hotel.eliminar_habitacion(numero))
            self.limpiar()

    def ver_historial(self):
        numero = self._numero_seleccionado()
        if numero:
            ventana_lectura(self, f"Historial de la habitación {numero}",
                            texto_historial(f"Historial de la habitación {numero}",
                                            self.hotel.reservas_de_habitacion(numero),
                                            f"La habitación {numero} no tiene reservas"))


# ---------------------------------------------------------------------------
# Pestaña Huéspedes
# ---------------------------------------------------------------------------
class PestanaHuespedes(Pestana):
    def __init__(self, notebook, app):
        super().__init__(notebook, app)
        self.documento, self.entrada_documento = campo(self.formulario, 0, "Documento")
        self.nombre, _ = campo(self.formulario, 1, "Nombre")
        self.telefono, _ = campo(self.formulario, 2, "Teléfono")
        self.correo, _ = campo(self.formulario, 3, "Correo")
        ttk.Button(self.formulario, text="Limpiar", command=self.limpiar).grid(
            row=4, column=1, sticky="e", pady=(8, 0))

        self.boton("Registrar", self.registrar)
        self.boton("Actualizar", self.actualizar)
        self.boton("Eliminar", self.eliminar)
        self.boton("Ver historial", self.ver_historial)

        busqueda = ttk.Frame(self.derecha)
        busqueda.grid(row=0, column=0, sticky="we", pady=(0, 6))
        ttk.Label(busqueda, text="Buscar:").pack(side="left")
        self.buscado = tk.StringVar()
        ttk.Entry(busqueda, textvariable=self.buscado, width=20).pack(side="left", padx=4)
        ttk.Button(busqueda, text="Por documento", command=self.buscar_documento).pack(side="left")
        ttk.Button(busqueda, text="Por nombre", command=self.buscar_nombre).pack(side="left", padx=4)
        ttk.Button(busqueda, text="Ver todos", command=self.refrescar).pack(side="left")

        marco, self.tabla = crear_tabla(self.derecha, ("Documento", "Nombre", "Teléfono", "Correo"),
                                        (110, 180, 110, 220))
        marco.grid(row=1, column=0, sticky="nsew")
        self.tabla.bind("<<TreeviewSelect>>", self.al_seleccionar)

    def _filas(self, huespedes):
        return [(h.documento, (h.documento, h.nombre, h.telefono, h.correo)) for h in huespedes]

    def refrescar(self):
        llenar_tabla(self.tabla, self._filas(self.hotel.listar_huespedes()))

    def buscar_documento(self):
        huesped = self.hotel.buscar_huesped(self.buscado.get())
        if huesped is None:
            self.app.mostrar_resultado(False, f"No se encontró el huésped {self.buscado.get().strip()}")
            llenar_tabla(self.tabla, [])
        else:
            llenar_tabla(self.tabla, self._filas([huesped]))
            self.app.barra.set(f"Huésped {huesped.nombre} encontrado.")

    def buscar_nombre(self):
        encontrados = self.hotel.buscar_huespedes_por_nombre(self.buscado.get())
        llenar_tabla(self.tabla, self._filas(encontrados))
        if encontrados:
            self.app.barra.set(f"{len(encontrados)} huésped(es) encontrados.")
        else:
            self.app.mostrar_resultado(False, f"No se encontró ningún huésped con «{self.buscado.get().strip()}»")

    def al_seleccionar(self, _evento=None):
        documento = seleccion(self.tabla)
        huesped = self.hotel.buscar_huesped(documento) if documento else None
        if huesped:
            self.entrada_documento.configure(state="normal")
            self.documento.set(huesped.documento)
            self.entrada_documento.configure(state="readonly")  # el documento no se modifica
            self.nombre.set(huesped.nombre)
            self.telefono.set(huesped.telefono)
            self.correo.set(huesped.correo)

    def limpiar(self):
        self.entrada_documento.configure(state="normal")
        for variable in (self.documento, self.nombre, self.telefono, self.correo):
            variable.set("")
        self.tabla.selection_remove(*self.tabla.selection())

    def registrar(self):
        huesped = self.ejecutar(self.hotel.registrar_huesped(
            self.documento.get(), self.nombre.get(), self.telefono.get(), self.correo.get()))
        if huesped:
            self.limpiar()

    def actualizar(self):
        self.ejecutar(self.hotel.actualizar_huesped(
            self.documento.get(), self.nombre.get(), self.telefono.get(), self.correo.get()))

    def eliminar(self):
        documento = self.documento.get().strip()
        if not documento:
            self.app.mostrar_resultado(False, "Seleccione un huésped en la tabla.")
            return
        if self.app.confirmar(f"¿Eliminar al huésped {documento}?"):
            exito, mensaje, _ = self.hotel.eliminar_huesped(documento)
            self.app.mostrar_resultado(exito, mensaje)
            if exito:
                self.limpiar()
            self.refrescar()

    def ver_historial(self):
        documento = seleccion(self.tabla) or self.documento.get().strip()
        huesped = self.hotel.buscar_huesped(documento)
        if huesped is None:
            self.app.mostrar_resultado(False, "Seleccione un huésped en la tabla.")
            return
        titulo = f"Historial de {huesped.nombre} ({huesped.documento})"
        ventana_lectura(self, titulo, texto_historial(
            titulo, self.hotel.reservas_de_huesped(huesped.documento),
            f"{huesped.nombre} no tiene reservas"))


# ---------------------------------------------------------------------------
# Pestaña Reservas
# ---------------------------------------------------------------------------
class PestanaReservas(Pestana):
    def __init__(self, notebook, app):
        super().__init__(notebook, app)
        self.documento, self.entrada_documento = campo(self.formulario, 0, "Documento huésped", 16)
        self.numero, _ = campo(self.formulario, 1, "Número habitación", 16)
        self.fecha, _ = campo(self.formulario, 2, "Ingreso (AAAA-MM-DD)", 16)
        self.dias, _ = campo(self.formulario, 3, "Días (1 a 30)", 16)
        self.personas, _ = campo(self.formulario, 4, "Personas", 16)
        self.fecha.set(fecha_a_texto(date.today()))
        ttk.Button(self.formulario, text="Limpiar", command=self.limpiar).grid(
            row=5, column=1, sticky="e", pady=(8, 0))

        self.boton("Registrar", self.registrar)
        self.boton("Ver detalle", self.ver_detalle)
        self.boton("Finalizar (check-out)", self.finalizar)
        self.boton("Cancelar reserva", self.cancelar)

        filtros = ttk.Frame(self.derecha)
        filtros.grid(row=0, column=0, sticky="we", pady=(0, 6))
        ttk.Label(filtros, text="Estado:").pack(side="left")
        self.filtro = tk.StringVar(value="TODAS")
        combo = ttk.Combobox(filtros, textvariable=self.filtro, width=12, state="readonly",
                             values=("TODAS",) + ESTADOS)
        combo.pack(side="left", padx=4)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refrescar())
        ttk.Label(filtros, text="   Buscar código:").pack(side="left")
        self.buscado = tk.StringVar()
        entrada = ttk.Entry(filtros, textvariable=self.buscado, width=8)
        entrada.pack(side="left", padx=4)
        entrada.bind("<Return>", lambda _e: self.buscar())
        ttk.Button(filtros, text="Buscar", command=self.buscar).pack(side="left")
        ttk.Button(filtros, text="Ver todas", command=self.ver_todas).pack(side="left", padx=4)

        columnas = ("Código", "Huésped", "Habitación", "Ingreso", "Salida", "Días", "Personas", "Estado")
        marco, self.tabla = crear_tabla(self.derecha, columnas, (65, 160, 80, 90, 90, 45, 65, 95))
        marco.grid(row=1, column=0, sticky="nsew")
        self.tabla.bind("<Double-1>", lambda _e: self.ver_detalle())

    def _filas(self, reservas):
        return [
            (r.codigo, (r.codigo, r.huesped.nombre, r.habitacion.numero,
                        fecha_a_texto(r.fecha_ingreso), fecha_a_texto(r.fecha_salida),
                        r.dias, r.personas, r.estado))
            for r in reservas
        ]

    def refrescar(self):
        llenar_tabla(self.tabla, self._filas(self.hotel.listar_reservas(self.filtro.get())))

    def ver_todas(self):
        self.filtro.set("TODAS")
        self.buscado.set("")
        self.refrescar()

    def buscar(self):
        reserva = self.hotel.buscar_reserva(self.buscado.get())
        if reserva is None:
            self.app.mostrar_resultado(False, f"No se encontró la reserva {self.buscado.get().strip().upper()}")
            llenar_tabla(self.tabla, [])
        else:
            llenar_tabla(self.tabla, self._filas([reserva]))
            self.tabla.selection_set(reserva.codigo)
            self.app.barra.set(f"Reserva {reserva.codigo} encontrada.")

    def precargar(self, numero, fecha, dias, personas):
        """Usado por «Reservar esta habitación»: solo falta el documento."""
        self.documento.set("")
        self.numero.set(str(numero))
        self.fecha.set(fecha)
        self.dias.set(dias)
        self.personas.set(personas)
        self.entrada_documento.focus_set()
        self.app.barra.set(f"Habitación {numero} precargada: escriba el documento del huésped y pulse Registrar.")

    def limpiar(self):
        for variable in (self.documento, self.numero, self.dias, self.personas):
            variable.set("")
        self.fecha.set(fecha_a_texto(date.today()))

    def _codigo_seleccionado(self):
        codigo = seleccion(self.tabla)
        if codigo is None:
            self.app.mostrar_resultado(False, "Seleccione una reserva en la tabla.")
        return codigo

    def registrar(self):
        reserva = self.ejecutar(self.hotel.registrar_reserva(
            self.documento.get(), self.numero.get(), self.fecha.get(),
            self.dias.get(), self.personas.get()))
        if reserva:
            self.limpiar()
            if self.tabla.exists(reserva.codigo):
                self.tabla.selection_set(reserva.codigo)
                self.tabla.see(reserva.codigo)

    def ver_detalle(self):
        codigo = self._codigo_seleccionado()
        reserva = self.hotel.buscar_reserva(codigo) if codigo else None
        if reserva:
            ventana_lectura(self, f"Detalle de la reserva {reserva.codigo}", reserva.detalle())

    def cancelar(self):
        codigo = self._codigo_seleccionado()
        if codigo and self.app.confirmar(f"¿Cancelar la reserva {codigo}?"):
            self.ejecutar(self.hotel.cancelar_reserva(codigo))

    def finalizar(self):
        codigo = self._codigo_seleccionado()
        if codigo and self.app.confirmar(f"¿Finalizar (check-out) la reserva {codigo}?"):
            self.ejecutar(self.hotel.finalizar_reserva(codigo))


# ---------------------------------------------------------------------------
# Pestaña Disponibilidad
# ---------------------------------------------------------------------------
class PestanaDisponibilidad(Pestana):
    def __init__(self, notebook, app):
        super().__init__(notebook, app)
        self.fecha, _ = campo(self.formulario, 0, "Ingreso (AAAA-MM-DD)", 14)
        self.dias, _ = campo(self.formulario, 1, "Días (1 a 30)", 14)
        self.personas, _ = campo(self.formulario, 2, "Personas", 14)
        self.fecha.set(fecha_a_texto(date.today()))
        self.dias.set("1")
        self.personas.set("1")
        self._ultima = None  # última consulta aceptada (fecha, días, personas)

        self.boton("Consultar", self.consultar)
        self.boton("Reservar esta habitación", self.reservar)

        self.resumen = tk.StringVar(value="Escriba la estadía y pulse Consultar.")
        ttk.Label(self.derecha, textvariable=self.resumen).grid(row=0, column=0, sticky="w", pady=(0, 6))
        marco, self.tabla = crear_tabla(self.derecha, ("Número", "Piso", "Capacidad"), (120, 100, 120))
        marco.grid(row=1, column=0, sticky="nsew")
        self.tabla.bind("<Double-1>", lambda _e: self.reservar())
        llenar_tabla(self.tabla, [])

    def _consultar(self, fecha, dias, personas, mostrar):
        exito, mensaje, libres = self.hotel.habitaciones_disponibles(fecha, dias, personas)
        if mostrar:
            self.app.mostrar_resultado(exito, mensaje)
        if exito:
            self._ultima = (fecha, dias, personas)
            self.resumen.set(mensaje)
            llenar_tabla(self.tabla, [(h.numero, (h.numero, h.piso, h.capacidad)) for h in libres])
        else:
            self._ultima = None
            self.resumen.set("Corrija los datos y vuelva a consultar.")
            llenar_tabla(self.tabla, [])

    def consultar(self):
        self._consultar(self.fecha.get(), self.dias.get(), self.personas.get(), mostrar=True)

    def refrescar(self):
        # Al volver a la pestaña se repite la última consulta, por si algo cambió.
        if self._ultima:
            self._consultar(*self._ultima, mostrar=False)

    def reservar(self):
        numero = seleccion(self.tabla)
        if numero is None or self._ultima is None:
            self.app.mostrar_resultado(False, "Consulte y seleccione una habitación disponible.")
            return
        fecha, dias, personas = self._ultima
        self.app.pestana_reservas.precargar(numero, fecha, dias, personas)
        self.app.notebook.select(self.app.pestana_reservas)


# ---------------------------------------------------------------------------
# Ventana principal
# ---------------------------------------------------------------------------
class AplicacionHotel(tk.Tk):
    def __init__(self, hotel):
        super().__init__()
        self.hotel = hotel
        self.title("Sistema de reservas de hotel")
        self.geometry("1180x620")
        self.minsize(980, 520)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        self.pestana_habitaciones = PestanaHabitaciones(self.notebook, self)
        self.pestana_huespedes = PestanaHuespedes(self.notebook, self)
        self.pestana_reservas = PestanaReservas(self.notebook, self)
        self.pestana_disponibilidad = PestanaDisponibilidad(self.notebook, self)
        self.notebook.add(self.pestana_habitaciones, text="  Habitaciones  ")
        self.notebook.add(self.pestana_huespedes, text="  Huéspedes  ")
        self.notebook.add(self.pestana_reservas, text="  Reservas  ")
        self.notebook.add(self.pestana_disponibilidad, text="  Disponibilidad  ")
        self.notebook.bind("<<NotebookTabChanged>>", self._al_cambiar_pestana)

        self.barra = tk.StringVar(value=f"Datos cargados desde «{hotel.ruta}».")
        ttk.Label(self, textvariable=self.barra, relief="sunken", anchor="w", padding=(8, 4)).pack(
            fill="x", side="bottom", padx=8, pady=8)

        self.notebook.select(self.pestana_reservas)  # abre en Reservas
        self.pestana_reservas.refrescar()

    def _al_cambiar_pestana(self, _evento=None):
        pestana = self.nametowidget(self.notebook.select())
        pestana.refrescar()

    def mostrar_resultado(self, exito, mensaje):
        self.barra.set(("✔ " if exito else "✘ ") + mensaje)
        if not exito:
            messagebox.showwarning("Operación rechazada", mensaje, parent=self)

    def confirmar(self, pregunta):
        return messagebox.askyesno("Confirmar", pregunta, parent=self)


def main(ruta=None):
    try:
        hotel = Hotel(ruta) if ruta else Hotel()
    except ErrorDeDatos as error:
        raiz = tk.Tk()
        raiz.withdraw()
        messagebox.showerror(
            "No se pudieron cargar los datos",
            f"{error}\n\nEl archivo no se modificó. Revíselo o renómbrelo y vuelva a iniciar.")
        raiz.destroy()
        sys.exit(1)
    AplicacionHotel(hotel).mainloop()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
