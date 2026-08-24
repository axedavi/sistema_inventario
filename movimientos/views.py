from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import MovimientoForm
from .models import Lote, Movimiento
from .services import StockInsuficienteError, aplicar_movimiento


@login_required
def lista_movimientos(request):
    """Historial de movimientos de inventario (RF005)."""
    movimientos = Movimiento.objects.select_related(
        'producto', 'almacen_origen', 'almacen_destino', 'lote', 'usuario'
    )[:200]
    return render(request, 'movimientos/lista.html', {'movimientos': movimientos})


@login_required
def registrar_movimiento(request):
    """Registro de entradas, salidas y transferencias con validación de stock (HU003, RF005)."""
    if request.method == 'POST':
        form = MovimientoForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.usuario = request.user
            try:
                aplicar_movimiento(movimiento)
            except StockInsuficienteError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, "Movimiento registrado y stock actualizado correctamente.")
                return redirect('movimientos:lista')
    else:
        form = MovimientoForm()
    return render(request, 'movimientos/registrar.html', {'form': form})


@login_required
def lista_lotes(request):
    """Trazabilidad de lotes (HU005/HU006, en construcción)."""
    lotes = Lote.objects.select_related('producto')[:200]
    return render(request, 'movimientos/lotes.html', {'lotes': lotes})
