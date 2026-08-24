from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Lote, Movimiento


@login_required
def lista_movimientos(request):
    """Historial de movimientos de inventario. El registro (HU003) llega en el Sprint 2."""
    movimientos = Movimiento.objects.select_related(
        'producto', 'almacen_origen', 'almacen_destino', 'lote', 'usuario'
    )[:200]
    return render(request, 'movimientos/lista.html', {'movimientos': movimientos})


@login_required
def lista_lotes(request):
    """Trazabilidad de lotes (HU005/HU006, en construcción)."""
    lotes = Lote.objects.select_related('producto')[:200]
    return render(request, 'movimientos/lotes.html', {'lotes': lotes})
