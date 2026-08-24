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


# El pronóstico SES es mensual (ver obtener_historial_mensual); el ROP necesita
# demanda diaria, así que se prorratea usando un mes estándar de 30 días.
DIAS_POR_PERIODO = 30


def calcular_rop_para_producto(producto, periodos=1, guardar=True):
    """
    Calcula el pronóstico SES y, a partir de él, el Punto de Reorden del
    producto (RF012, HU008). Si `guardar` es True y hay datos suficientes,
    persiste el resultado en PrediccionStock para que el panel de inventario
    pueda leer el último ROP calculado sin volver a ejecutar SES en cada
    carga (RNF Desempeño).
    """
    from .models import PrediccionStock  # import local: evita ciclo con productos/movimientos

    resultado_ses = calcular_pronostico_ses(producto, periodos=periodos)
    if not resultado_ses['suficiente']:
        return {'suficiente': False, 'rop': None, 'ses': resultado_ses}

    demanda_diaria = resultado_ses['pronostico'] / DIAS_POR_PERIODO
    rop = calcular_punto_reorden(demanda_diaria, producto.lead_time_dias, float(producto.stock_seguridad))
    rop = round(rop, 2)

    if guardar:
        PrediccionStock.objects.create(
            producto=producto,
            alpha_utilizado=resultado_ses['alpha'],
            demanda_pronosticada=resultado_ses['pronostico'],
            punto_reorden=rop,
            periodos_calculados=periodos,
        )

    return {
        'suficiente': True,
        'rop': rop,
        'demanda_diaria': round(demanda_diaria, 4),
        'ses': resultado_ses,
    }


def ultimo_rop_por_producto():
    """
    Último Punto de Reorden calculado por producto (uno por producto, el más
    reciente), para el panel de inventario. Devuelve {producto_id: rop}.
    """
    from .models import PrediccionStock

    filas = (
        PrediccionStock.objects
        .order_by('producto_id', '-fecha_calculo')
        .distinct('producto_id')
        .values_list('producto_id', 'punto_reorden')
    )
    return dict(filas)
