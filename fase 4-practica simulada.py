"""
SOFTWARE FJ - Sistema Integral de Gestion de Clientes, Servicios y Reservas
UNAD - Ejercicio 1

Aplicacion de consola orientada a objetos. No utiliza bases de datos.
La informacion vive en listas mientras el programa esta en ejecucion.
Los eventos y errores se registran en el archivo software_fj.log.

Ejecucion:
    python software_fj.py
"""

from __future__ import annotations

import logging
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Callable, Optional


# ============================================================================
# 1. CONFIGURACION DEL REGISTRO DE EVENTOS Y ERRORES (LOGS)
# ============================================================================


def configurar_logger() -> logging.Logger:
    """Configura el archivo de registro sin duplicar manejadores."""
    logger = logging.getLogger("SoftwareFJ")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        manejador = logging.FileHandler("software_fj.log", encoding="utf-8")
        formato = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        manejador.setFormatter(formato)
        logger.addHandler(manejador)

    return logger


LOGGER = configurar_logger()


# ============================================================================
# 2. EXCEPCIONES PERSONALIZADAS
# ============================================================================


class SistemaFJError(Exception):
    """Excepcion base para los errores controlados del sistema."""


class ValidacionError(SistemaFJError):
    """Se presenta cuando un dato no cumple las reglas de validacion."""


class DatoInvalidoError(ValidacionError):
    """Se presenta cuando un dato tiene un formato o valor incorrecto."""


class ParametroFaltanteError(ValidacionError):
    """Se presenta cuando falta un parametro obligatorio."""


class OperacionNoPermitidaError(SistemaFJError):
    """Se presenta cuando se intenta realizar una operacion no permitida."""


class ServicioNoDisponibleError(OperacionNoPermitidaError):
    """Se presenta cuando un servicio esta desactivado o no disponible."""


class ClienteNoEncontradoError(SistemaFJError):
    """Se presenta cuando el cliente solicitado no existe en el sistema."""


class ServicioNoEncontradoError(SistemaFJError):
    """Se presenta cuando el servicio solicitado no existe en el sistema."""


class ReservaNoEncontradaError(SistemaFJError):
    """Se presenta cuando la reserva solicitada no existe."""


class ReservaError(SistemaFJError):
    """Se presenta ante problemas durante la creacion o procesamiento de reservas."""


class EstadoReservaError(ReservaError):
    """Se presenta cuando una reserva no permite la operacion solicitada."""


class CalculoCostoError(SistemaFJError):
    """Se presenta cuando no es posible calcular correctamente un costo."""


# ============================================================================
# 3. FUNCIONES GENERALES DE VALIDACION Y FORMATO
# ============================================================================


def validar_texto(valor: Any, nombre: str, minimo: int = 1) -> str:
    """Valida que un valor sea texto, no este vacio y cumpla una longitud."""
    if valor is None:
        raise ParametroFaltanteError(f"El campo '{nombre}' es obligatorio.")
    if not isinstance(valor, str):
        raise DatoInvalidoError(f"El campo '{nombre}' debe ser texto.")

    texto = valor.strip()
    if len(texto) < minimo:
        raise DatoInvalidoError(
            f"El campo '{nombre}' debe contener al menos {minimo} caracter(es)."
        )
    return texto


def convertir_decimal(valor: Any, nombre: str) -> Decimal:
    """Convierte un numero a Decimal y conserva la causa del error."""
    if valor is None:
        raise ParametroFaltanteError(f"El parametro '{nombre}' es obligatorio.")
    if isinstance(valor, bool):
        raise DatoInvalidoError(f"El parametro '{nombre}' no puede ser verdadero o falso.")

    try:
        numero = Decimal(str(valor).strip())
        if not numero.is_finite():
            raise DatoInvalidoError(f"El parametro '{nombre}' debe ser un numero finito.")
        return numero
    except (InvalidOperation, ValueError, TypeError) as exc:
        # Encadenamiento: la excepcion personalizada conserva el error original.
        raise DatoInvalidoError(
            f"El parametro '{nombre}' debe contener un valor numerico valido."
        ) from exc


def validar_entero(valor: Any, nombre: str, minimo: int = 1) -> int:
    """Valida cantidades enteras; no acepta decimales ni valores booleanos."""
    if valor is None:
        raise ParametroFaltanteError(f"El parametro '{nombre}' es obligatorio.")
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise DatoInvalidoError(f"El parametro '{nombre}' debe ser un numero entero.")
    if valor < minimo:
        raise DatoInvalidoError(f"El parametro '{nombre}' debe ser como minimo {minimo}.")
    return valor


def validar_duracion(valor: Any) -> Decimal:
    duracion = convertir_decimal(valor, "duracion")
    if duracion <= 0:
        raise DatoInvalidoError("La duracion debe ser mayor que cero horas.")
    return duracion


def validar_porcentaje(valor: Any, nombre: str) -> Decimal:
    porcentaje = convertir_decimal(valor, nombre)
    if porcentaje < 0 or porcentaje > 100:
        raise DatoInvalidoError(f"El porcentaje de '{nombre}' debe estar entre 0 y 100.")
    return porcentaje


def formato_dinero(valor: Decimal) -> str:
    return f"$ {valor:,.2f} COP"


def generar_id() -> str:
    return uuid.uuid4().hex[:8].upper()


# ============================================================================
# 4. CLASE ABSTRACTA GENERAL: ENTIDAD
# ============================================================================


class Entidad(ABC):
    """Representa cualquier entidad general que tenga identificador."""

    def __init__(self, identificador: Optional[str] = None) -> None:
        self._identificador = validar_texto(identificador, "identificador") if identificador else generar_id()
        self._fecha_creacion = datetime.now()

    @property
    def identificador(self) -> str:
        return self._identificador

    @property
    def fecha_creacion(self) -> datetime:
        return self._fecha_creacion

    @abstractmethod
    def mostrar_info(self) -> str:
        """Cada clase hija debe definir como presentar su informacion."""
        raise NotImplementedError


# ============================================================================
# 5. CLASE CLIENTE: ENCAPSULACION Y VALIDACIONES
# ============================================================================


class Cliente(Entidad):
    def __init__(
        self,
        nombre: str,
        documento: str,
        correo: str,
        telefono: str,
        identificador: Optional[str] = None,
    ) -> None:
        super().__init__(identificador)
        self.__nombre = validar_texto(nombre, "nombre", minimo=2)
        self.__documento = self.__validar_documento(documento)
        self.__correo = self.__validar_correo(correo)
        self.__telefono = self.__validar_telefono(telefono)
        self.__activo = True

    @staticmethod
    def __validar_documento(documento: Any) -> str:
        documento = validar_texto(documento, "documento", minimo=5)
        if not re.fullmatch(r"[A-Za-z0-9-]{5,20}", documento):
            raise DatoInvalidoError(
                "El documento debe tener entre 5 y 20 caracteres alfanumericos o guiones."
            )
        return documento

    @staticmethod
    def __validar_correo(correo: Any) -> str:
        correo = validar_texto(correo, "correo")
        patron = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
        if not re.fullmatch(patron, correo):
            raise DatoInvalidoError("El correo electronico no tiene un formato valido.")
        return correo.lower()

    @staticmethod
    def __validar_telefono(telefono: Any) -> str:
        telefono = validar_texto(telefono, "telefono")
        limpio = re.sub(r"[\s()-]", "", telefono)
        if not re.fullmatch(r"\+?\d{7,15}", limpio):
            raise DatoInvalidoError("El telefono debe contener entre 7 y 15 digitos.")
        return limpio

    @property
    def nombre(self) -> str:
        return self.__nombre

    @property
    def documento(self) -> str:
        return self.__documento

    @property
    def correo(self) -> str:
        return self.__correo

    @property
    def telefono(self) -> str:
        return self.__telefono

    @property
    def activo(self) -> bool:
        return self.__activo

    def actualizar_correo(self, nuevo_correo: str) -> None:
        self.__correo = self.__validar_correo(nuevo_correo)
        LOGGER.info("Correo actualizado para el cliente %s.", self.identificador)

    def desactivar(self) -> None:
        self.__activo = False
        LOGGER.info("Cliente %s desactivado.", self.identificador)

    def mostrar_info(self) -> str:
        return (
            f"Cliente | ID: {self.identificador} | Nombre: {self.nombre} | "
            f"Documento: {self.documento} | Correo: {self.correo} | "
            f"Telefono: {self.telefono} | Activo: {self.activo}"
        )


# ============================================================================
# 6. CLASE ABSTRACTA SERVICIO Y METODOS POLIMORFICOS
# ============================================================================


class Servicio(Entidad, ABC):
    """Clase abstracta para todos los servicios ofrecidos por Software FJ."""

    def __init__(
        self,
        nombre: str,
        descripcion: str,
        tarifa_base: Any,
        disponible: bool = True,
        identificador: Optional[str] = None,
    ) -> None:
        super().__init__(identificador)
        self._nombre = validar_texto(nombre, "nombre del servicio", minimo=3)
        self._descripcion = validar_texto(descripcion, "descripcion del servicio", minimo=5)
        self._tarifa_base = convertir_decimal(tarifa_base, "tarifa base")
        if self._tarifa_base <= 0:
            raise DatoInvalidoError("La tarifa base del servicio debe ser mayor que cero.")
        if not isinstance(disponible, bool):
            raise DatoInvalidoError("La disponibilidad debe ser verdadera o falsa.")
        self._disponible = disponible

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def descripcion(self) -> str:
        return self._descripcion

    @property
    def tarifa_base(self) -> Decimal:
        return self._tarifa_base

    @property
    def disponible(self) -> bool:
        return self._disponible

    def activar(self) -> None:
        self._disponible = True
        LOGGER.info("Servicio %s activado.", self.identificador)

    def desactivar(self) -> None:
        self._disponible = False
        LOGGER.info("Servicio %s desactivado.", self.identificador)

    def validar_disponibilidad(self) -> None:
        if not self._disponible:
            raise ServicioNoDisponibleError(
                f"El servicio '{self.nombre}' no se encuentra disponible."
            )

    @staticmethod
    def aplicar_impuesto_descuento(
        subtotal: Decimal, impuesto: Any = 0, descuento: Any = 0
    ) -> Decimal:
        """Calcula descuento e impuesto sobre el subtotal."""
        porcentaje_impuesto = validar_porcentaje(impuesto, "impuesto")
        porcentaje_descuento = validar_porcentaje(descuento, "descuento")
        despues_descuento = subtotal * (Decimal("1") - porcentaje_descuento / Decimal("100"))
        total = despues_descuento * (Decimal("1") + porcentaje_impuesto / Decimal("100"))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @abstractmethod
    def calcular_costo(
        self, duracion: Any, impuesto: Any = 0, descuento: Any = 0, **opciones: Any
    ) -> Decimal:
        """Cada servicio calcula su costo de forma especializada."""
        raise NotImplementedError

    @abstractmethod
    def mostrar_info(self) -> str:
        raise NotImplementedError


class ReservaSala(Servicio):
    """Servicio especializado para reservar salas por hora."""

    def __init__(
        self,
        tarifa_hora: Any = 50000,
        capacidad_maxima: int = 20,
        disponible: bool = True,
        identificador: Optional[str] = None,
    ) -> None:
        self.__capacidad_maxima = validar_entero(capacidad_maxima, "capacidad maxima")
        super().__init__(
            "Reserva de salas",
            "Alquiler de salas para reuniones, clases y eventos.",
            tarifa_hora,
            disponible,
            identificador,
        )

    @property
    def capacidad_maxima(self) -> int:
        return self.__capacidad_maxima

    def calcular_costo(
        self,
        duracion: Any,
        impuesto: Any = 0,
        descuento: Any = 0,
        personas: int = 1,
        **opciones: Any,
    ) -> Decimal:
        self.validar_disponibilidad()
        horas = validar_duracion(duracion)
        cantidad_personas = validar_entero(personas, "personas")
        if cantidad_personas > self.capacidad_maxima:
            raise DatoInvalidoError(
                f"La sala admite maximo {self.capacidad_maxima} personas; "
                f"se solicitaron {cantidad_personas}."
            )
        subtotal = self.tarifa_base * horas
        return self.aplicar_impuesto_descuento(subtotal, impuesto, descuento)

    def mostrar_info(self) -> str:
        return (
            f"Servicio: {self.nombre} | ID: {self.identificador} | "
            f"Tarifa por hora: {formato_dinero(self.tarifa_base)} | "
            f"Capacidad: {self.capacidad_maxima} personas | Disponible: {self.disponible}"
        )


class AlquilerEquipos(Servicio):
    """Servicio especializado para alquilar equipos por hora y cantidad."""

    def __init__(
        self,
        tarifa_hora_equipo: Any = 25000,
        inventario: int = 15,
        disponible: bool = True,
        identificador: Optional[str] = None,
    ) -> None:
        self.__inventario = validar_entero(inventario, "inventario")
        super().__init__(
            "Alquiler de equipos",
            "Alquiler de computadores, proyectores y equipos audiovisuales.",
            tarifa_hora_equipo,
            disponible,
            identificador,
        )

    @property
    def inventario(self) -> int:
        return self.__inventario

    def calcular_costo(
        self,
        duracion: Any,
        impuesto: Any = 0,
        descuento: Any = 0,
        cantidad: int = 1,
        **opciones: Any,
    ) -> Decimal:
        self.validar_disponibilidad()
        horas = validar_duracion(duracion)
        unidades = validar_entero(cantidad, "cantidad de equipos")
        if unidades > self.inventario:
            raise ServicioNoDisponibleError(
                f"Inventario insuficiente: hay {self.inventario} equipos y se solicitaron {unidades}."
            )
        subtotal = self.tarifa_base * horas * unidades
        return self.aplicar_impuesto_descuento(subtotal, impuesto, descuento)

    def mostrar_info(self) -> str:
        return (
            f"Servicio: {self.nombre} | ID: {self.identificador} | "
            f"Tarifa por equipo/hora: {formato_dinero(self.tarifa_base)} | "
            f"Inventario: {self.inventario} | Disponible: {self.disponible}"
        )


class AsesoriaEspecializada(Servicio):
    """Servicio especializado para asesorias profesionales."""

    def __init__(
        self,
        tarifa_hora: Any = 80000,
        disponible: bool = True,
        identificador: Optional[str] = None,
    ) -> None:
        super().__init__(
            "Asesorias especializadas",
            "Acompanamiento y orientacion profesional en areas especializadas.",
            tarifa_hora,
            disponible,
            identificador,
        )

    def calcular_costo(
        self,
        duracion: Any,
        impuesto: Any = 0,
        descuento: Any = 0,
        area: str = "General",
        **opciones: Any,
    ) -> Decimal:
        self.validar_disponibilidad()
        horas = validar_duracion(duracion)
        validar_texto(area, "area de asesoria")
        subtotal = self.tarifa_base * horas
        return self.aplicar_impuesto_descuento(subtotal, impuesto, descuento)

    def mostrar_info(self) -> str:
        return (
            f"Servicio: {self.nombre} | ID: {self.identificador} | "
            f"Tarifa por hora: {formato_dinero(self.tarifa_base)} | "
            f"Disponible: {self.disponible}"
        )


# ============================================================================
# 7. CLASE RESERVA: CLIENTE + SERVICIO + DURACION + ESTADO
# ============================================================================


class Reserva(Entidad):
    ESTADO_PENDIENTE = "Pendiente"
    ESTADO_CONFIRMADA = "Confirmada"
    ESTADO_CANCELADA = "Cancelada"

    def __init__(
        self,
        cliente: Cliente,
        servicio: Servicio,
        duracion: Any,
        parametros_servicio: Optional[dict[str, Any]] = None,
        fecha_hora: Optional[datetime] = None,
        identificador: Optional[str] = None,
    ) -> None:
        super().__init__(identificador)
        if not isinstance(cliente, Cliente):
            raise DatoInvalidoError("La reserva debe estar asociada a un objeto Cliente valido.")
        if not isinstance(servicio, Servicio):
            raise DatoInvalidoError("La reserva debe estar asociada a un objeto Servicio valido.")
        if not cliente.activo:
            raise OperacionNoPermitidaError("No se puede reservar con un cliente inactivo.")
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion = validar_duracion(duracion)
        if parametros_servicio is None:
            parametros_servicio = {}
        if not isinstance(parametros_servicio, dict):
            raise DatoInvalidoError("Los parametros del servicio deben enviarse en un diccionario.")
        self.__parametros_servicio = dict(parametros_servicio)
        if fecha_hora is not None and not isinstance(fecha_hora, datetime):
            raise DatoInvalidoError("La fecha de la reserva debe ser un objeto datetime.")
        self.__fecha_hora = fecha_hora or datetime.now()
        self.__estado = self.ESTADO_PENDIENTE
        self.__costo = None

    @property
    def cliente(self) -> Cliente:
        return self.__cliente

    @property
    def servicio(self) -> Servicio:
        return self.__servicio

    @property
    def duracion(self) -> Decimal:
        return self.__duracion

    @property
    def estado(self) -> str:
        return self.__estado

    @property
    def costo(self) -> Optional[Decimal]:
        return self.__costo

    @property
    def fecha_hora(self) -> datetime:
        return self.__fecha_hora

    def confirmar(self) -> Decimal:
        """Confirma la reserva solo si el servicio puede procesarla."""
        if self.__estado != self.ESTADO_PENDIENTE:
            raise EstadoReservaError(
                f"Solo se pueden confirmar reservas pendientes. Estado actual: {self.__estado}."
            )

        try:
            costo_calculado = self.__servicio.calcular_costo(
                self.__duracion, **self.__parametros_servicio
            )
        except Exception as exc:
            # Se encadena el error concreto para conservar su causa original.
            raise ReservaError(
                f"No fue posible confirmar la reserva {self.identificador}: {exc}"
            ) from exc

        self.__costo = costo_calculado
        self.__estado = self.ESTADO_CONFIRMADA
        LOGGER.info(
            "Reserva %s confirmada. Cliente=%s Servicio=%s Costo=%s",
            self.identificador,
            self.cliente.identificador,
            self.servicio.identificador,
            self.__costo,
        )
        return self.__costo

    def cancelar(self) -> None:
        if self.__estado == self.ESTADO_CANCELADA:
            raise EstadoReservaError("La reserva ya se encuentra cancelada.")
        self.__estado = self.ESTADO_CANCELADA
        LOGGER.info("Reserva %s cancelada.", self.identificador)

    def mostrar_info(self) -> str:
        costo_texto = formato_dinero(self.__costo) if self.__costo is not None else "Pendiente de calculo"
        return (
            f"Reserva | ID: {self.identificador} | Cliente: {self.cliente.nombre} | "
            f"Servicio: {self.servicio.nombre} | Duracion: {self.duracion} hora(s) | "
            f"Fecha: {self.fecha_hora:%Y-%m-%d %H:%M} | Estado: {self.estado} | "
            f"Costo: {costo_texto}"
        )


# ============================================================================
# 8. CLASE PRINCIPAL: ADMINISTRA LAS LISTAS INTERNAS DEL SISTEMA
# ============================================================================


class SistemaGestion:
    """Administra clientes, servicios y reservas usando listas en memoria."""

    def __init__(self) -> None:
        self.__clientes: list[Cliente] = []
        self.__servicios: list[Servicio] = []
        self.__reservas: list[Reserva] = []
        LOGGER.info("Sistema de gestion Software FJ iniciado.")

    @property
    def clientes(self) -> list[Cliente]:
        return self.__clientes.copy()

    @property
    def servicios(self) -> list[Servicio]:
        return self.__servicios.copy()

    @property
    def reservas(self) -> list[Reserva]:
        return self.__reservas.copy()

    def registrar_cliente(self, cliente: Cliente) -> Cliente:
        if not isinstance(cliente, Cliente):
            raise DatoInvalidoError("Solo se pueden registrar objetos de la clase Cliente.")
        if any(c.documento.lower() == cliente.documento.lower() for c in self.__clientes):
            raise OperacionNoPermitidaError(
                f"Ya existe un cliente con documento {cliente.documento}."
            )
        if any(c.identificador == cliente.identificador for c in self.__clientes):
            raise OperacionNoPermitidaError("Ya existe un cliente con ese identificador.")
        self.__clientes.append(cliente)
        LOGGER.info("Cliente registrado: %s - %s.", cliente.identificador, cliente.nombre)
        return cliente

    def registrar_servicio(self, servicio: Servicio) -> Servicio:
        if not isinstance(servicio, Servicio):
            raise DatoInvalidoError("Solo se pueden registrar objetos de la clase Servicio.")
        if any(s.identificador == servicio.identificador for s in self.__servicios):
            raise OperacionNoPermitidaError("Ya existe un servicio con ese identificador.")
        if any(s.nombre.lower() == servicio.nombre.lower() for s in self.__servicios):
            raise OperacionNoPermitidaError(f"El servicio '{servicio.nombre}' ya esta registrado.")
        self.__servicios.append(servicio)
        LOGGER.info("Servicio registrado: %s - %s.", servicio.identificador, servicio.nombre)
        return servicio

    def buscar_cliente(self, identificador: str) -> Cliente:
        identificador = validar_texto(identificador, "identificador del cliente")
        for cliente in self.__clientes:
            if cliente.identificador == identificador:
                return cliente
        raise ClienteNoEncontradoError(
            f"No se encontro el cliente con identificador {identificador}."
        )

    def buscar_servicio(self, identificador: str) -> Servicio:
        identificador = validar_texto(identificador, "identificador del servicio")
        for servicio in self.__servicios:
            if servicio.identificador == identificador:
                return servicio
        raise ServicioNoEncontradoError(
            f"No se encontro el servicio con identificador {identificador}."
        )

    def buscar_reserva(self, identificador: str) -> Reserva:
        identificador = validar_texto(identificador, "identificador de la reserva")
        for reserva in self.__reservas:
            if reserva.identificador == identificador:
                return reserva
        raise ReservaNoEncontradaError(
            f"No se encontro la reserva con identificador {identificador}."
        )

    def crear_reserva(
        self,
        identificador_cliente: str,
        identificador_servicio: str,
        duracion: Any,
        parametros_servicio: Optional[dict[str, Any]] = None,
    ) -> Reserva:
        cliente = self.buscar_cliente(identificador_cliente)
        servicio = self.buscar_servicio(identificador_servicio)
        try:
            reserva = Reserva(cliente, servicio, duracion, parametros_servicio)
        except (TypeError, KeyError) as exc:
            # Ejemplo de encadenamiento para parametros mal entregados.
            raise ParametroFaltanteError(
                "Faltan parametros requeridos para crear la reserva."
            ) from exc
        self.__reservas.append(reserva)
        LOGGER.info("Reserva %s creada en estado pendiente.", reserva.identificador)
        return reserva

    def confirmar_reserva(self, identificador_reserva: str) -> Decimal:
        reserva = self.buscar_reserva(identificador_reserva)
        return reserva.confirmar()

    def cancelar_reserva(self, identificador_reserva: str) -> None:
        reserva = self.buscar_reserva(identificador_reserva)
        reserva.cancelar()

    def listar_clientes(self) -> None:
        print("\n--- CLIENTES REGISTRADOS ---")
        if not self.__clientes:
            print("No hay clientes registrados.")
        for cliente in self.__clientes:
            print(cliente.mostrar_info())

    def listar_servicios(self) -> None:
        print("\n--- SERVICIOS REGISTRADOS ---")
        if not self.__servicios:
            print("No hay servicios registrados.")
        for servicio in self.__servicios:
            print(servicio.mostrar_info())

    def listar_reservas(self) -> None:
        print("\n--- RESERVAS REGISTRADAS ---")
        if not self.__reservas:
            print("No hay reservas registradas.")
        for reserva in self.__reservas:
            print(reserva.mostrar_info())

    def mostrar_resumen(self) -> None:
        confirmadas = sum(1 for r in self.__reservas if r.estado == Reserva.ESTADO_CONFIRMADA)
        pendientes = sum(1 for r in self.__reservas if r.estado == Reserva.ESTADO_PENDIENTE)
        canceladas = sum(1 for r in self.__reservas if r.estado == Reserva.ESTADO_CANCELADA)
        print("\n========== RESUMEN DEL SISTEMA SOFTWARE FJ ==========")
        print(f"Clientes registrados: {len(self.__clientes)}")
        print(f"Servicios registrados: {len(self.__servicios)}")
        print(f"Reservas registradas: {len(self.__reservas)}")
        print(f"Reservas confirmadas: {confirmadas}")
        print(f"Reservas pendientes: {pendientes}")
        print(f"Reservas canceladas: {canceladas}")
        print("=====================================================\n")


# ============================================================================
# 9. EJECUTOR SEGURO DE OPERACIONES: TRY / EXCEPT / ELSE / FINALLY
# ============================================================================


def ejecutar_operacion(
    numero: int, descripcion: str, accion: Callable[[], Any]
) -> Any:
    """Ejecuta cada operacion sin detener el resto de la demostracion."""
    print(f"\n[OPERACION {numero:02d}] {descripcion}")
    try:
        resultado = accion()
    except SistemaFJError as exc:
        LOGGER.exception("Operacion %02d fallida: %s", numero, descripcion)
        print(f"ERROR CONTROLADO: {exc}")
        resultado = None
    except Exception as exc:
        # Captura final para que un error inesperado no cierre la aplicacion.
        LOGGER.exception("Error inesperado en operacion %02d: %s", numero, descripcion)
        print(f"ERROR INESPERADO CONTROLADO: {type(exc).__name__}: {exc}")
        resultado = None
    else:
        LOGGER.info("Operacion %02d realizada correctamente: %s", numero, descripcion)
        print("Resultado: operacion realizada correctamente.")
    finally:
        print(f"Fin de la operacion {numero:02d}. La aplicacion continua activa.")
    return resultado


# ============================================================================
# 10. DEMOSTRACION: MAS DE DIEZ OPERACIONES VALIDAS E INVALIDAS
# ============================================================================


def demostracion() -> None:
    print("\n" + "=" * 72)
    print(" SOFTWARE FJ - SISTEMA INTEGRAL DE CLIENTES, SERVICIOS Y RESERVAS")
    print(" Ejecucion de demostracion solicitada en el ejercicio de la UNAD")
    print("=" * 72)

    sistema = SistemaGestion()

    # Operacion 1: registro valido de cliente.
    cliente_ana = ejecutar_operacion(
        1,
        "Registrar un cliente con todos sus datos validos.",
        lambda: sistema.registrar_cliente(
            Cliente("Ana Maria Torres", "1032456789", "ana.torres@email.com", "+573001112233")
        ),
    )

    # Operacion 2: registro de un segundo cliente valido.
    cliente_carlos = ejecutar_operacion(
        2,
        "Registrar un segundo cliente valido.",
        lambda: sistema.registrar_cliente(
            Cliente("Carlos Perez", "987654321", "carlos.perez@email.com", "3105556677")
        ),
    )

    # Operacion 3: intento de registro con correo incorrecto.
    ejecutar_operacion(
        3,
        "Intentar registrar un cliente con correo invalido (debe generar excepcion).",
        lambda: sistema.registrar_cliente(
            Cliente("Laura Gomez", "1122334455", "correo-no-valido", "3201234567")
        ),
    )

    # Operacion 4: crear y registrar el servicio de salas.
    sala = ejecutar_operacion(
        4,
        "Crear y registrar el servicio de reserva de salas.",
        lambda: sistema.registrar_servicio(
            ReservaSala(tarifa_hora=50000, capacidad_maxima=15)
        ),
    )

    # Operacion 5: crear y registrar el servicio de alquiler de equipos.
    equipos = ejecutar_operacion(
        5,
        "Crear y registrar el servicio de alquiler de equipos.",
        lambda: sistema.registrar_servicio(
            AlquilerEquipos(tarifa_hora_equipo=25000, inventario=10)
        ),
    )

    # Operacion 6: crear y registrar el servicio de asesoria.
    asesoria = ejecutar_operacion(
        6,
        "Crear y registrar el servicio de asesorias especializadas.",
        lambda: sistema.registrar_servicio(
            AsesoriaEspecializada(tarifa_hora=80000)
        ),
    )

    # Operacion 7: creacion incorrecta de servicio con tarifa negativa.
    ejecutar_operacion(
        7,
        "Intentar crear un servicio con tarifa negativa (debe rechazarse).",
        lambda: sistema.registrar_servicio(ReservaSala(tarifa_hora=-10000)),
    )

    # Operacion 8: crear reserva valida de sala.
    reserva_sala = None
    if cliente_ana is not None and sala is not None:
        reserva_sala = ejecutar_operacion(
            8,
            "Crear una reserva valida de sala para cinco personas durante dos horas.",
            lambda: sistema.crear_reserva(
                cliente_ana.identificador,
                sala.identificador,
                2,
                {"personas": 5},
            ),
        )

    # Operacion 9: confirmar reserva de sala y calcular costo.
    if reserva_sala is not None:
        ejecutar_operacion(
            9,
            "Confirmar la reserva de sala y calcular su costo.",
            lambda: sistema.confirmar_reserva(reserva_sala.identificador),
        )

    # Operacion 10: crear reserva de equipos.
    reserva_equipos = None
    if cliente_carlos is not None and equipos is not None:
        reserva_equipos = ejecutar_operacion(
            10,
            "Crear reserva de dos equipos durante tres horas.",
            lambda: sistema.crear_reserva(
                cliente_carlos.identificador,
                equipos.identificador,
                3,
                {"cantidad": 2},
            ),
        )

    # Operacion 11: confirmar reserva de equipos.
    if reserva_equipos is not None:
        ejecutar_operacion(
            11,
            "Confirmar la reserva de equipos y calcular su costo.",
            lambda: sistema.confirmar_reserva(reserva_equipos.identificador),
        )

    # Operacion 12: crear y confirmar una asesoria especializada.
    reserva_asesoria = None
    if cliente_ana is not None and asesoria is not None:
        reserva_asesoria = ejecutar_operacion(
            12,
            "Crear una reserva de asesoria especializada por una hora.",
            lambda: sistema.crear_reserva(
                cliente_ana.identificador,
                asesoria.identificador,
                1,
                {"area": "Programacion orientada a objetos"},
            ),
        )
    if reserva_asesoria is not None:
        ejecutar_operacion(
            13,
            "Confirmar la reserva de asesoria.",
            lambda: sistema.confirmar_reserva(reserva_asesoria.identificador),
        )

    # Operacion 14: cliente inexistente.
    ejecutar_operacion(
        14,
        "Intentar reservar con un identificador de cliente inexistente.",
        lambda: sistema.crear_reserva("CLIENTE-NO-EXISTE", sala.identificador, 1, {"personas": 2}),
    )

    # Operacion 15: duracion invalida.
    if cliente_ana is not None and sala is not None:
        ejecutar_operacion(
            15,
            "Intentar crear una reserva con duracion negativa.",
            lambda: sistema.crear_reserva(
                cliente_ana.identificador, sala.identificador, -2, {"personas": 2}
            ),
        )

    # Operacion 16: servicio desactivado; la reserva se crea, pero no se confirma.
    reserva_no_disponible = None
    if cliente_ana is not None and asesoria is not None:
        ejecutar_operacion(
            16,
            "Desactivar temporalmente el servicio de asesoria.",
            lambda: asesoria.desactivar(),
        )
        reserva_no_disponible = ejecutar_operacion(
            17,
            "Crear una reserva pendiente para el servicio desactivado.",
            lambda: sistema.crear_reserva(
                cliente_ana.identificador, asesoria.identificador, 1, {"area": "Finanzas"}
            ),
        )
    if reserva_no_disponible is not None:
        ejecutar_operacion(
            18,
            "Intentar confirmar una reserva cuyo servicio no esta disponible.",
            lambda: sistema.confirmar_reserva(reserva_no_disponible.identificador),
        )

    # Operacion 19: cancelar una reserva confirmada.
    if reserva_sala is not None:
        ejecutar_operacion(
            19,
            "Cancelar una reserva de sala que ya habia sido confirmada.",
            lambda: sistema.cancelar_reserva(reserva_sala.identificador),
        )

    # Operacion 20: intentar confirmar una reserva cancelada.
    if reserva_sala is not None:
        ejecutar_operacion(
            20,
            "Intentar confirmar una reserva que ya fue cancelada.",
            lambda: sistema.confirmar_reserva(reserva_sala.identificador),
        )

    # Operacion 21: variante del calculo con impuesto y descuento.
    if sala is not None:
        ejecutar_operacion(
            21,
            "Calcular costo con parametros opcionales: impuesto 19% y descuento 10%.",
            lambda: print(
                "Costo final:",
                formato_dinero(
                    sala.calcular_costo(2, impuesto=19, descuento=10, personas=5)
                ),
            ),
        )

    # Restaurar disponibilidad para dejar los datos en un estado claro.
    if asesoria is not None:
        ejecutar_operacion(
            22,
            "Reactivar el servicio de asesoria.",
            lambda: asesoria.activar(),
        )

    sistema.listar_clientes()
    sistema.listar_servicios()
    sistema.listar_reservas()
    sistema.mostrar_resumen()

    print("La demostracion termino. El sistema no se detuvo por los errores controlados.")
    print("Revise el archivo 'software_fj.log' para consultar el historial de eventos y errores.")
    LOGGER.info("Demostracion finalizada. Clientes=%d Servicios=%d Reservas=%d",
                len(sistema.clientes), len(sistema.servicios), len(sistema.reservas))


# ============================================================================
# 11. PUNTO DE ENTRADA DEL PROGRAMA
# ============================================================================


if __name__ == "__main__":
    try:
        demostracion()
    except KeyboardInterrupt:
        LOGGER.warning("Ejecucion interrumpida manualmente por el usuario.")
        print("\nLa ejecucion fue interrumpida por el usuario.")
    except Exception as exc:
        # Ultima barrera de seguridad: registra el error y muestra un mensaje.
        LOGGER.exception("Error critico no previsto en el punto de entrada.")
        print(f"Se presento un error critico controlado: {exc}")
    finally:
        print("\nPrograma Software FJ finalizado.")
