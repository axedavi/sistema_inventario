from collections import defaultdict

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


def obtener_historial_mensual_todos():
    """
    Igual que obtener_historial_mensual(), pero para todos los productos a la
    vez en una sola consulta (HU010: "consolidar datos... en una sola
    consulta"). Devuelve {producto_id: [(mes, total), ...]}.
    """
    filas = (
        Movimiento.objects
        .filter(tipo=Movimiento.SALIDA)
        .annotate(mes=TruncMonth('fecha'))
        .values('producto_id', 'mes')
        .annotate(total=Sum('cantidad'))
        .order_by('producto_id', 'mes')
    )
    resultado = defaultdict(list)
    for fila in filas:
        resultado[fila['producto_id']].append((fila['mes'], fila['total']))
    return resultado


def _ajustar_ses(historial, alpha, periodos):
    """Corre SimpleExpSmoothing sobre un historial ya obtenido y devuelve el pronóstico redondeado."""
    serie = [float(total) for _, total in historial]
    modelo = SimpleExpSmoothing(serie).fit(smoothing_level=float(alpha), optimized=False)
    return round(float(modelo.forecast(periodos)[0]), 2)


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

    return {
        'suficiente': True,
        'historial': historial,
        'pronostico': _ajustar_ses(historial, producto.alpha, periodos),
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


def consolidado_prediccion():
    """
    Para cada producto activo: stock actual, pronóstico SES, ROP, días
    estimados hasta llegar al ROP y una recomendación de acción (HU010,
    RF016). El historial de salidas de todos los productos se trae en una
    sola consulta; el ajuste SES en sí es, por naturaleza estadística,
    siempre por producto. No persiste en PrediccionStock (se generaría una
    fila por producto en cada clic; el registro histórico queda para
    cuando se consulta un producto puntual, Sprint 7).
    """
    from productos.models import Producto

    productos = Producto.objects.filter(activo=True).select_related('proveedor').prefetch_related('stockalmacen_set')
    historiales = obtener_historial_mensual_todos()

    filas = []
    for producto in productos:
        historial = historiales.get(producto.id, [])
        stock_actual = sum((s.cantidad for s in producto.stockalmacen_set.all()), start=0)

        if len(historial) < MINIMO_REGISTROS_HISTORICOS:
            filas.append({
                'producto': producto,
                'stock_actual': stock_actual,
                'suficiente': False,
                'pronostico': None,
                'rop': None,
                'dias_hasta_reorden': None,
                'recomendacion': 'Datos insuficientes',
            })
            continue

        pronostico = _ajustar_ses(historial, producto.alpha, periodos=1)
        demanda_diaria = pronostico / DIAS_POR_PERIODO
        rop = round(
            calcular_punto_reorden(demanda_diaria, producto.lead_time_dias, float(producto.stock_seguridad)), 2
        )

        if stock_actual <= rop:
            dias_hasta_reorden = 0
            recomendacion = 'Reponer'
        elif demanda_diaria > 0:
            dias_hasta_reorden = round((float(stock_actual) - rop) / demanda_diaria, 1)
            recomendacion = 'Stock suficiente'
        else:
            dias_hasta_reorden = None
            recomendacion = 'Stock suficiente'

        filas.append({
            'producto': producto,
            'stock_actual': stock_actual,
            'suficiente': True,
            'pronostico': pronostico,
            'rop': rop,
            'dias_hasta_reorden': dias_hasta_reorden,
            'recomendacion': recomendacion,
        })

    return filas
