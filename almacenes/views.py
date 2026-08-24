from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from predicciones.services import ultimo_rop_por_producto
from productos.models import Categoria, Producto

from .models import Almacen


@login_required
def panel_inventario(request):
    """Vista unificada de stock por almacén con alertas de reorden (HU004, RF006, RF007)."""
    almacenes = Almacen.objects.filter(activo=True)
    categorias = Categoria.objects.all()

    productos = Producto.objects.filter(activo=True).select_related(
        'categoria', 'unidad'
    ).prefetch_related('stockalmacen_set__almacen')

    # RF012/HU008: el ROP calculado (persistido en PrediccionStock) manda
    # sobre stock_minimo en cuanto existe al menos un cálculo para el producto.
    rop_por_producto = ultimo_rop_por_producto()

    filas = []
    for producto in productos:
        stocks_por_almacen = list(producto.stockalmacen_set.all())
        stock_total = sum((s.cantidad for s in stocks_por_almacen), start=0)
        rop = rop_por_producto.get(producto.id)
        umbral_alerta = rop if rop is not None else producto.stock_minimo
        filas.append({
            'producto': producto,
            'stock_total': stock_total,
            'stocks_por_almacen': stocks_por_almacen,
            'almacenes_ids': ','.join(str(s.almacen_id) for s in stocks_por_almacen),
            'rop': rop,
            'en_alerta': stock_total <= umbral_alerta,
        })

    contexto = {
        'almacenes': almacenes,
        'categorias': categorias,
        'filas': filas,
    }
    return render(request, 'almacenes/panel.html', contexto)
