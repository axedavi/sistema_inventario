from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from productos.models import Producto

from .models import Almacen, StockAlmacen


@login_required
def panel_inventario(request):
    """Vista unificada de stock por almacén con alertas de reorden (HU004, RF006)."""
    almacenes = Almacen.objects.filter(activo=True)

    almacen_id = request.GET.get('almacen')
    productos = Producto.objects.filter(activo=True).select_related('categoria', 'unidad')
    if almacen_id:
        productos = productos.filter(stockalmacen__almacen_id=almacen_id).distinct()

    filas = []
    for producto in productos:
        stock_total = StockAlmacen.objects.filter(producto=producto).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        stocks_por_almacen = StockAlmacen.objects.filter(producto=producto).select_related('almacen')
        en_alerta = stock_total <= producto.stock_minimo
        filas.append({
            'producto': producto,
            'stock_total': stock_total,
            'stocks_por_almacen': stocks_por_almacen,
            'en_alerta': en_alerta,
        })

    contexto = {
        'almacenes': almacenes,
        'filas': filas,
        'almacen_seleccionado': almacen_id,
    }
    return render(request, 'almacenes/panel.html', contexto)
