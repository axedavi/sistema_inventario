from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from almacenes.models import StockAlmacen

from .models import Lote, Movimiento


class StockInsuficienteError(ValidationError):
    """Se intentó registrar una salida/transferencia mayor al stock disponible (RF005)."""


def _bloquear_o_crear_stock(producto, almacen):
    stock, _ = StockAlmacen.objects.select_for_update().get_or_create(
        producto=producto, almacen=almacen, defaults={'cantidad': 0}
    )
    return stock


def _asignar_lote_fifo(movimiento):
    """
    HU005: si el operador no eligió un lote manualmente, asocia automáticamente
    el lote más antiguo del producto que tenga unidades suficientes disponibles.
    Si ningún lote individual alcanza, el movimiento queda sin lote (la
    trazabilidad por lote es opcional; nunca bloquea la salida de stock).
    """
    candidatos = Lote.objects.select_for_update().filter(
        producto=movimiento.producto
    ).order_by('fecha_ingreso')
    for lote in candidatos:
        if lote.cantidad_disponible >= movimiento.cantidad:
            movimiento.lote = lote
            return


def _crear_lote_de_entrada(movimiento, numero, vencimiento):
    return Lote.objects.create(
        producto=movimiento.producto,
        numero_lote=numero,
        fecha_ingreso=date.today(),
        fecha_vencimiento=vencimiento,
        cantidad_inicial=movimiento.cantidad,
    )


@transaction.atomic
def aplicar_movimiento(movimiento: Movimiento, nuevo_lote_numero=None, nuevo_lote_vencimiento=None) -> Movimiento:
    """
    Guarda `movimiento` (instancia sin pk) y aplica su efecto sobre StockAlmacen
    de forma atomica: si no hay stock suficiente para una salida o transferencia,
    no se guarda nada (RF005, HU003). En entradas, opcionalmente crea el lote
    (RF008); en salidas/transferencias sin lote explícito, lo asigna por FIFO
    (HU005).
    """
    if movimiento.tipo == Movimiento.ENTRADA:
        if nuevo_lote_numero:
            movimiento.lote = _crear_lote_de_entrada(movimiento, nuevo_lote_numero, nuevo_lote_vencimiento)
        destino = _bloquear_o_crear_stock(movimiento.producto, movimiento.almacen_destino)
        destino.cantidad += movimiento.cantidad
        destino.save()

    elif movimiento.tipo == Movimiento.SALIDA:
        origen = _bloquear_o_crear_stock(movimiento.producto, movimiento.almacen_origen)
        if movimiento.cantidad > origen.cantidad:
            raise StockInsuficienteError(
                f"Stock insuficiente en {movimiento.almacen_origen}: "
                f"disponible {origen.cantidad}, solicitado {movimiento.cantidad}."
            )
        if not movimiento.lote:
            _asignar_lote_fifo(movimiento)
        origen.cantidad -= movimiento.cantidad
        origen.save()

    elif movimiento.tipo == Movimiento.TRANSFERENCIA:
        origen = _bloquear_o_crear_stock(movimiento.producto, movimiento.almacen_origen)
        if movimiento.cantidad > origen.cantidad:
            raise StockInsuficienteError(
                f"Stock insuficiente en {movimiento.almacen_origen}: "
                f"disponible {origen.cantidad}, solicitado {movimiento.cantidad}."
            )
        if not movimiento.lote:
            _asignar_lote_fifo(movimiento)
        destino = _bloquear_o_crear_stock(movimiento.producto, movimiento.almacen_destino)
        origen.cantidad -= movimiento.cantidad
        destino.cantidad += movimiento.cantidad
        origen.save()
        destino.save()

    movimiento.save()
    return movimiento
