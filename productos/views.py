from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, render

from almacenes.models import StockAlmacen
from predicciones.services import MINIMO_REGISTROS_HISTORICOS, calcular_rop_para_producto

from .models import Producto


@login_required
def detalle_producto(request, pk):
    """Vista del producto: stock actual, pronóstico SES y Punto de Reorden (HU007/HU008, RF011/RF012/RF014)."""
    producto = get_object_or_404(Producto.objects.select_related('categoria', 'unidad', 'proveedor'), pk=pk)

    stock_total = StockAlmacen.objects.filter(producto=producto).aggregate(
        total=Sum('cantidad')
    )['total'] or 0
    stocks_por_almacen = StockAlmacen.objects.filter(producto=producto).select_related('almacen')

    resultado_rop = calcular_rop_para_producto(producto)
    en_alerta = resultado_rop['suficiente'] and stock_total <= resultado_rop['rop']

    contexto = {
        'producto': producto,
        'stock_total': stock_total,
        'stocks_por_almacen': stocks_por_almacen,
        'resultado_rop': resultado_rop,
        'en_alerta': en_alerta,
        'minimo_registros': MINIMO_REGISTROS_HISTORICOS,
    }
    return render(request, 'productos/detalle.html', contexto)
