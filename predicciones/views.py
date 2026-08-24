from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import PrediccionStock


@login_required
def lista_predicciones(request):
    """El registro histórico de cálculos de ROP se alimenta desde el Sprint 7 (HU008)."""
    predicciones = PrediccionStock.objects.select_related('producto')[:200]
    return render(request, 'predicciones/lista.html', {'predicciones': predicciones})
