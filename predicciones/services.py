from django.db.models import Sum
from django.db.models.functions import TruncMonth
from statsmodels.tsa.holtwinters import SimpleExpSmoothing

from movimientos.models import Movimiento

MINIMO_REGISTROS_HISTORICOS = 3


def obtener_historial_mensual(producto):
    """
    Serie de tiempo con el total de salidas por mes del producto, en orden
    cronológico (HU007: "el modelo debe utilizar el historial de salidas
    del producto como serie de tiempo de entrada").
    """
    filas = (
        Movimiento.objects
        .filter(producto=producto, tipo=Movimiento.SALIDA)
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(total=Sum('cantidad'))
        .order_by('mes')
    )
    return [(fila['mes'], fila['total']) for fila in filas]


def calcular_pronostico_ses(producto, periodos=1):
    """
    Calcula la demanda pronosticada del producto con Suavizamiento Exponencial
    Simple (RF011, HU007). Devuelve un dict con el resultado; si hay menos de
    MINIMO_REGISTROS_HISTORICOS períodos, 'pronostico' es None y 'suficiente'
    es False, tal como exige el criterio de aceptación.
    """
    historial = obtener_historial_mensual(producto)

    if len(historial) < MINIMO_REGISTROS_HISTORICOS:
        return {
            'suficiente': False,
            'historial': historial,
            'pronostico': None,
            'alpha': producto.alpha,
        }

    serie = [float(total) for _, total in historial]
    alpha = float(producto.alpha)
    modelo = SimpleExpSmoothing(serie).fit(smoothing_level=alpha, optimized=False)
    pronostico = modelo.forecast(periodos)

    return {
        'suficiente': True,
        'historial': historial,
        'pronostico': round(float(pronostico[0]), 2),
        'alpha': producto.alpha,
    }


def calcular_punto_reorden(demanda_diaria_promedio, tiempo_entrega_dias, stock_seguridad):
    """ROP = demanda_diaria_promedio * tiempo_entrega + stock_seguridad (RF012)."""
    return demanda_diaria_promedio * tiempo_entrega_dias + stock_seguridad
