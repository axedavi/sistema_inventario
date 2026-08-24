from django.core.exceptions import ValidationError
from django.db import transaction

from almacenes.models import StockAlmacen

from .models import Movimiento


class StockInsuficienteError(ValidationError):
    """Se intentó registrar una salida/transferencia mayor al stock disponible (RF005)."""


def _bloquear_o_crear_stock(producto, almacen):
    stock, _ = StockAlmacen.objects.select_for_update().get_or_create(
        producto=producto, almacen=almacen, defaults={'cantidad': 0}
    )
    return stock


@transaction.atomic
def aplicar_movimiento(movimiento: Movimiento) -> Movimiento:
    """
    Guarda `movimiento` (instancia sin pk) y aplica su efecto sobre StockAlmacen
    de forma atomica: si no hay stock suficiente para una salida o transferencia,
    no se guarda nada (RF005, HU003).
    """
    if movimiento.tipo == Movimiento.ENTRADA:
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
        origen.cantidad -= movimiento.cantidad
        origen.save()

    elif movimiento.tipo == Movimiento.TRANSFERENCIA:
        origen = _bloquear_o_crear_stock(movimiento.producto, movimiento.almacen_origen)
        if movimiento.cantidad > origen.cantidad:
            raise StockInsuficienteError(
                f"Stock insuficiente en {movimiento.almacen_origen}: "
                f"disponible {origen.cantidad}, solicitado {movimiento.cantidad}."
            )
        destino = _bloquear_o_crear_stock(movimiento.producto, movimiento.almacen_destino)
        origen.cantidad -= movimiento.cantidad
        destino.cantidad += movimiento.cantidad
        origen.save()
        destino.save()

    movimiento.save()
    return movimiento
