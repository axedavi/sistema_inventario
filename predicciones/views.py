from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

from .models import PrediccionStock


def calcular_ses(historial_demanda, alpha=0.3, periodos=3):
    """
    historial_demanda: lista de cantidades vendidas por período.
    alpha: parámetro de suavizamiento (0-1).
    periodos: cuántos períodos futuros predecir.
    """
    modelo = SimpleExpSmoothing(historial_demanda).fit(
        smoothing_level=alpha, optimized=True
    )
    prediccion = modelo.forecast(periodos)
    return prediccion.tolist()


def calcular_punto_reorden(demanda_promedio, tiempo_entrega, stock_seguridad):
    """ROP = demanda_promedio * tiempo_entrega + stock_seguridad."""
    return demanda_promedio * tiempo_entrega + stock_seguridad


@login_required
def lista_predicciones(request):
    """El cálculo automático de SES y ROP (HU007/HU008) se implementa en los Sprints 6-7."""
    predicciones = PrediccionStock.objects.select_related('producto')[:200]
    return render(request, 'predicciones/lista.html', {'predicciones': predicciones})
