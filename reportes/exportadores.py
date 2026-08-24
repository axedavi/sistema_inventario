from io import BytesIO

import openpyxl
from django.http import HttpResponse
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from movimientos.models import Movimiento

from .services import construir_filas_inventario

ENCABEZADO_ESTILO = TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3d3e')),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f2f2')]),
])


def _totales_por_tipo(movimientos):
    totales = {codigo: 0 for codigo, _ in Movimiento.TIPO_CHOICES}
    for m in movimientos:
        totales[m.tipo] = totales.get(m.tipo, 0) + m.cantidad
    etiquetas = dict(Movimiento.TIPO_CHOICES)
    return [(etiquetas[codigo], total) for codigo, total in totales.items() if total]


def _respuesta_pdf(nombre_archivo, titulo, filas_encabezado, filas_datos, filas_totales=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    estilos = getSampleStyleSheet()
    elementos = [Paragraph(titulo, estilos['Title']), Spacer(1, 12)]

    tabla = Table([filas_encabezado] + filas_datos, repeatRows=1)
    tabla.setStyle(ENCABEZADO_ESTILO)
    elementos.append(tabla)

    if filas_totales:
        elementos.append(Spacer(1, 16))
        elementos.append(Paragraph("Totales del período", estilos['Heading3']))
        tabla_totales = Table([["Tipo", "Cantidad total"]] + filas_totales)
        tabla_totales.setStyle(ENCABEZADO_ESTILO)
        elementos.append(tabla_totales)

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
    encabezado = ['Fecha', 'Tipo', 'Producto', 'Origen', 'Destino', 'Lote', 'Cantidad', 'Usuario']
    filas = [[
        m.fecha.strftime('%d/%m/%Y %H:%M'),
        m.get_tipo_display(),
        str(m.producto),
        str(m.almacen_origen or '—'),
        str(m.almacen_destino or '—'),
        str(m.lote or '—'),
        str(m.cantidad),
        str(m.usuario or '—'),
    ] for m in movimientos]
    totales = _totales_por_tipo(movimientos)

    if formato == 'excel':
        return _respuesta_excel('reporte_movimientos.xlsx', 'Movimientos', encabezado, filas, totales)
    return _respuesta_pdf('reporte_movimientos.pdf', 'Reporte de Movimientos de Inventario', encabezado, filas, totales)


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
    return _respuesta_pdf('reporte_inventario.pdf', 'Reporte de Estado del Inventario', encabezado, filas)
