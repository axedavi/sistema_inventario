from io import BytesIO
from xml.sax.saxutils import escape

import openpyxl
from django.http import HttpResponse
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from movimientos.models import Movimiento

from .services import construir_filas_inventario

MARGEN = 36

ENCABEZADO_ESTILO = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3d3e')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
])

CELDA = ParagraphStyle('celda', fontName='Helvetica', fontSize=7, leading=8.5)
CELDA_ENCABEZADO = ParagraphStyle(
    'celda_encabezado', fontName='Helvetica-Bold', fontSize=7.5, leading=9, textColor=colors.white
)


def _tabla_ajustada(encabezado, filas, pesos, ancho_disponible):
    """
    Arma la tabla con anchos de columna que suman exactamente el ancho útil de
    la hoja. Sin esto ReportLab calcula el ancho según el texto más largo y,
    como además centra la tabla, lo que no cabe se recorta por ambos lados y
    desaparecen las columnas de los extremos.
    """
    factor = ancho_disponible / sum(pesos)
    anchos = [peso * factor for peso in pesos]

    datos = [[Paragraph(escape(str(celda)), CELDA_ENCABEZADO) for celda in encabezado]]
    datos += [[Paragraph(escape(str(celda)), CELDA) for celda in fila] for fila in filas]

    tabla = Table(datos, colWidths=anchos, repeatRows=1, hAlign='LEFT')
    tabla.setStyle(ENCABEZADO_ESTILO)
    return tabla


def _totales_por_tipo(movimientos):
    totales = {codigo: 0 for codigo, _ in Movimiento.TIPO_CHOICES}
    for m in movimientos:
        totales[m.tipo] = totales.get(m.tipo, 0) + m.cantidad
    etiquetas = dict(Movimiento.TIPO_CHOICES)
    return [(etiquetas[codigo], total) for codigo, total in totales.items() if total]


def _respuesta_pdf(nombre_archivo, titulo, filas_encabezado, filas_datos, filas_totales=None,
                   pesos=None, horizontal=False):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter) if horizontal else letter,
        leftMargin=MARGEN, rightMargin=MARGEN, topMargin=MARGEN, bottomMargin=MARGEN,
    )
    estilos = getSampleStyleSheet()
    elementos = [Paragraph(titulo, estilos['Title']), Spacer(1, 12)]

    pesos = pesos or [1] * len(filas_encabezado)
    elementos.append(_tabla_ajustada(filas_encabezado, filas_datos, pesos, doc.width))

    if filas_totales:
        elementos.append(Spacer(1, 16))
        elementos.append(Paragraph("Totales del período", estilos['Heading3']))
        elementos.append(
            _tabla_ajustada(["Tipo", "Cantidad total"], filas_totales, [3, 2], doc.width / 2)
        )

    doc.build(elementos)
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


def _respuesta_excel(nombre_archivo, titulo_hoja, filas_encabezado, filas_datos, filas_totales=None):
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = titulo_hoja

    hoja.append(filas_encabezado)
    for celda in hoja[1]:
        celda.font = Font(bold=True)
    for fila in filas_datos:
        hoja.append(fila)

    if filas_totales:
        hoja.append([])
        hoja.append(["Totales del período"])
        hoja.append(["Tipo", "Cantidad total"])
        for fila in filas_totales:
            hoja.append(list(fila))

    for columna in hoja.columns:
        ancho = max(len(str(c.value)) if c.value is not None else 0 for c in columna) + 2
        hoja.column_dimensions[columna[0].column_letter].width = min(ancho, 40)

    buffer = BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response


def exportar_movimientos(movimientos, formato):
    """RF015/RF017: reporte de movimientos con totales por tipo, en PDF o Excel."""
    encabezado = ['Fecha', 'Tipo', 'Producto', 'Origen', 'Destino', 'Lote', 'Cantidad', 'Motivo', 'Usuario']
    filas = [[
        m.fecha.strftime('%d/%m/%Y %H:%M'),
        m.get_tipo_display(),
        str(m.producto),
        str(m.almacen_origen or '—'),
        str(m.almacen_destino or '—'),
        # Solo el número: el __str__ del lote repite el producto, que ya tiene su columna.
        m.lote.numero_lote if m.lote else '—',
        str(m.cantidad),
        m.get_motivo_display() or '—',
        str(m.usuario or '—'),
    ] for m in movimientos]
    totales = _totales_por_tipo(movimientos)

    if formato == 'excel':
        return _respuesta_excel('reporte_movimientos.xlsx', 'Movimientos', encabezado, filas, totales)
    return _respuesta_pdf(
        'reporte_movimientos.pdf', 'Reporte de Movimientos de Inventario', encabezado, filas, totales,
        pesos=[10, 7, 18, 9, 9, 10, 6, 12, 9], horizontal=True,
    )


def exportar_inventario(productos, formato):
    """RF015/RF017: reporte del estado actual del inventario, con ROP, en PDF o Excel."""
    encabezado = ['Código', 'Producto', 'Categoría', 'Stock total', 'Punto de Reorden', 'Estado']

    filas = []
    for fila in construir_filas_inventario(productos):
        producto = fila['producto']
        rop = fila['rop']
        filas.append([
            producto.codigo,
            producto.nombre,
            str(producto.categoria or '—'),
            str(fila['stock_total']),
            str(rop) if rop is not None else f"{producto.stock_minimo} (mínimo)",
            'Reabastecer' if fila['en_alerta'] else 'Normal',
        ])

    if formato == 'excel':
        return _respuesta_excel('reporte_inventario.xlsx', 'Inventario', encabezado, filas)
    return _respuesta_pdf(
        'reporte_inventario.pdf', 'Reporte de Estado del Inventario', encabezado, filas,
        pesos=[8, 20, 12, 8, 10, 9],
    )


def exportar_consolidado(filas_prediccion, formato):
    """RF016/RF017: reporte consolidado de predicción de stock, en PDF o Excel (HU010)."""
    encabezado = [
        'Código', 'Producto', 'Stock actual', 'Pronóstico SES',
        'Punto de Reorden', 'Días hasta reorden', 'Recomendación',
    ]

    filas = []
    for fila in filas_prediccion:
        producto = fila['producto']
        filas.append([
            producto.codigo,
            producto.nombre,
            str(fila['stock_actual']),
            str(fila['pronostico']) if fila['suficiente'] else '—',
            str(fila['rop']) if fila['suficiente'] else '—',
            str(fila['dias_hasta_reorden']) if fila['dias_hasta_reorden'] is not None else '—',
            fila['recomendacion'],
        ])

    if formato == 'excel':
        return _respuesta_excel('reporte_consolidado_prediccion.xlsx', 'Predicción', encabezado, filas)
    return _respuesta_pdf(
        'reporte_consolidado_prediccion.pdf', 'Reporte Consolidado de Predicción de Stock', encabezado, filas,
        pesos=[8, 22, 9, 10, 10, 10, 12], horizontal=True,
    )
