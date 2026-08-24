from predicciones.services import ultimo_rop_por_producto


def construir_filas_inventario(productos):
    """
    Arma, para cada producto, el stock total y el Punto de Reorden vigente.
    La usan tanto la vista previa en pantalla como los exportadores PDF/Excel
    (HU009), para no calcular el ROP dos veces con lógica distinta.
    """
    rop_por_producto = ultimo_rop_por_producto()
    filas = []
    for producto in productos:
        stocks = list(producto.stockalmacen_set.all())
        stock_total = sum((s.cantidad for s in stocks), start=0)
        rop = rop_por_producto.get(producto.id)
        umbral = rop if rop is not None else producto.stock_minimo
        filas.append({
            'producto': producto,
            'stock_total': stock_total,
            'rop': rop,
            'en_alerta': stock_total <= umbral,
        })
    return filas
