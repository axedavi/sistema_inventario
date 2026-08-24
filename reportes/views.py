from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest
from django.shortcuts import render

from .exportadores import exportar_inventario, exportar_movimientos
from .forms import FiltroInventarioForm, FiltroMovimientosForm
from .services import construir_filas_inventario


@login_required
def panel_reportes(request):
    """Punto de entrada a los reportes de inventario y de movimientos (HU009, RF015)."""
    form_movimientos = FiltroMovimientosForm(request.GET or None)
    form_inventario = FiltroInventarioForm(request.GET or None)

    movimientos = list(form_movimientos.filtrar()[:500])
    filas_inventario = construir_filas_inventario(form_inventario.filtrar())

    contexto = {
        'form_movimientos': form_movimientos,
        'form_inventario': form_inventario,
        'movimientos': movimientos,
        'filas_inventario': filas_inventario,
    }
    return render(request, 'reportes/panel.html', contexto)


@login_required
def exportar_movimientos_vista(request):
    formato = request.GET.get('formato')
    if formato not in ('pdf', 'excel'):
        return HttpResponseBadRequest("Formato de exportación no soportado.")
    form = FiltroMovimientosForm(request.GET or None)
    movimientos = form.filtrar()[:500]
    return exportar_movimientos(movimientos, formato)


@login_required
def exportar_inventario_vista(request):
    formato = request.GET.get('formato')
    if formato not in ('pdf', 'excel'):
        return HttpResponseBadRequest("Formato de exportación no soportado.")
    form = FiltroInventarioForm(request.GET or None)
    productos = form.filtrar()
    return exportar_inventario(productos, formato)
