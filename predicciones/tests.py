from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from almacenes.models import Almacen
from movimientos.models import Movimiento
from productos.models import Producto, Unidad

from .models import PrediccionStock
from .services import (
    MINIMO_REGISTROS_HISTORICOS,
    calcular_pronostico_ses,
    calcular_punto_reorden,
    calcular_rop_para_producto,
    consolidado_prediccion,
    obtener_historial_mensual,
    ultimo_rop_por_producto,
)


class HistorialMensualTests(TestCase):
    """Serie de tiempo de entrada para SES: salidas mensuales del producto (HU007)."""

    def setUp(self):
        unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(codigo='P001', nombre='Tela', unidad=unidad)
        self.almacen = Almacen.objects.create(nombre='Bodega A')

    def _crear_salida(self, cantidad, fecha):
        mov = Movimiento.objects.create(
            tipo=Movimiento.SALIDA, producto=self.producto,
            almacen_origen=self.almacen, cantidad=Decimal(str(cantidad)),
        )
        Movimiento.objects.filter(pk=mov.pk).update(fecha=fecha)

    def test_sin_salidas_historial_vacio(self):
        self.assertEqual(obtener_historial_mensual(self.producto), [])

    def test_agrupa_por_mes_y_suma_cantidades(self):
        self._crear_salida(10, timezone.make_aware(datetime(2026, 1, 5)))
        self._crear_salida(5, timezone.make_aware(datetime(2026, 1, 20)))
        self._crear_salida(8, timezone.make_aware(datetime(2026, 2, 3)))

        totales = [total for _, total in obtener_historial_mensual(self.producto)]
        self.assertEqual(totales, [Decimal('15'), Decimal('8')])

    def test_solo_cuenta_movimientos_de_tipo_salida(self):
        Movimiento.objects.create(
            tipo=Movimiento.ENTRADA, producto=self.producto,
            almacen_destino=self.almacen, cantidad=Decimal('100'),
        )
        self.assertEqual(obtener_historial_mensual(self.producto), [])


class CalcularPronosticoSesTests(TestCase):
    """CP-PRED-01/02, HU007: cálculo de pronóstico con SES y aviso por datos insuficientes (RF011)."""

    def setUp(self):
        unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(
            codigo='P001', nombre='Tela', unidad=unidad, alpha=Decimal('0.5')
        )
        self.almacen = Almacen.objects.create(nombre='Bodega A')

    def _crear_salida(self, cantidad, fecha):
        mov = Movimiento.objects.create(
            tipo=Movimiento.SALIDA, producto=self.producto,
            almacen_origen=self.almacen, cantidad=Decimal(str(cantidad)),
        )
        Movimiento.objects.filter(pk=mov.pk).update(fecha=fecha)

    def test_menos_del_minimo_de_periodos_no_calcula(self):
        for mes, cantidad in [(1, 10), (2, 12)]:
            self._crear_salida(cantidad, timezone.make_aware(datetime(2026, mes, 5)))

        resultado = calcular_pronostico_ses(self.producto)
        self.assertFalse(resultado['suficiente'])
        self.assertIsNone(resultado['pronostico'])
        self.assertEqual(len(resultado['historial']), 2)
        self.assertLess(len(resultado['historial']), MINIMO_REGISTROS_HISTORICOS)

    def test_tres_o_mas_periodos_calcula_pronostico(self):
        for mes, cantidad in [(1, 10), (2, 12), (3, 14)]:
            self._crear_salida(cantidad, timezone.make_aware(datetime(2026, mes, 5)))

        resultado = calcular_pronostico_ses(self.producto)
        self.assertTrue(resultado['suficiente'])
        self.assertIsInstance(resultado['pronostico'], float)
        self.assertGreater(resultado['pronostico'], 0)
        self.assertEqual(resultado['alpha'], self.producto.alpha)

    def test_alpha_configurado_por_producto_afecta_el_resultado(self):
        for mes, cantidad in [(1, 10), (2, 15), (3, 30)]:
            self._crear_salida(cantidad, timezone.make_aware(datetime(2026, mes, 5)))

        self.producto.alpha = Decimal('0.9')
        self.producto.save()
        resultado_reactivo = calcular_pronostico_ses(self.producto)

        self.producto.alpha = Decimal('0.1')
        self.producto.save()
        resultado_estable = calcular_pronostico_ses(self.producto)

        self.assertNotEqual(resultado_reactivo['pronostico'], resultado_estable['pronostico'])


class CalcularRopTests(TestCase):
    """CP-PRED-03/HU008: cálculo del Punto de Reorden y su persistencia (RF012)."""

    def setUp(self):
        unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(
            codigo='P001', nombre='Tela', unidad=unidad,
            alpha=Decimal('0.5'), lead_time_dias=6, stock_seguridad=Decimal('4'),
        )
        self.almacen = Almacen.objects.create(nombre='Bodega A')

    def _crear_salida(self, cantidad, fecha):
        mov = Movimiento.objects.create(
            tipo=Movimiento.SALIDA, producto=self.producto,
            almacen_origen=self.almacen, cantidad=Decimal(str(cantidad)),
        )
        Movimiento.objects.filter(pk=mov.pk).update(fecha=fecha)

    def test_formula_rop(self):
        self.assertEqual(calcular_punto_reorden(2.5, 6, 4), 19.0)

    def test_sin_historial_suficiente_no_calcula_ni_guarda(self):
        resultado = calcular_rop_para_producto(self.producto)
        self.assertFalse(resultado['suficiente'])
        self.assertIsNone(resultado['rop'])
        self.assertFalse(PrediccionStock.objects.exists())

    def test_calcula_y_guarda_rop_con_historial_suficiente(self):
        for mes, cantidad in [(1, 30), (2, 30), (3, 30)]:
            self._crear_salida(cantidad, timezone.make_aware(datetime(2026, mes, 5)))

        resultado = calcular_rop_para_producto(self.producto)
        self.assertTrue(resultado['suficiente'])
        # demanda mensual pronosticada = 30 -> diaria = 1.0 -> ROP = 1.0*6 + 4 = 10.0
        self.assertEqual(resultado['demanda_diaria'], 1.0)
        self.assertEqual(resultado['rop'], 10.0)

        prediccion = PrediccionStock.objects.get()
        self.assertEqual(prediccion.producto, self.producto)
        self.assertEqual(prediccion.punto_reorden, Decimal('10.0'))

    def test_guardar_false_no_persiste(self):
        for mes, cantidad in [(1, 30), (2, 30), (3, 30)]:
            self._crear_salida(cantidad, timezone.make_aware(datetime(2026, mes, 5)))
        calcular_rop_para_producto(self.producto, guardar=False)
        self.assertFalse(PrediccionStock.objects.exists())


class UltimoRopPorProductoTests(TestCase):
    """El panel de inventario debe leer el último ROP calculado por producto (HU004 + HU008)."""

    def setUp(self):
        unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(codigo='P001', nombre='Tela', unidad=unidad)

    def test_sin_predicciones_no_hay_entrada_para_el_producto(self):
        self.assertEqual(ultimo_rop_por_producto(), {})

    def test_devuelve_el_rop_mas_reciente_por_producto(self):
        antigua = PrediccionStock.objects.create(
            producto=self.producto, alpha_utilizado=Decimal('0.3'),
            demanda_pronosticada=Decimal('10'), punto_reorden=Decimal('20'),
        )
        PrediccionStock.objects.filter(pk=antigua.pk).update(
            fecha_calculo=timezone.now() - timezone.timedelta(days=5)
        )
        PrediccionStock.objects.create(
            producto=self.producto, alpha_utilizado=Decimal('0.3'),
            demanda_pronosticada=Decimal('12'), punto_reorden=Decimal('25'),
        )

        resultado = ultimo_rop_por_producto()
        self.assertEqual(resultado[self.producto.id], Decimal('25'))


class ConsolidadoPrediccionTests(TestCase):
    """CP-PRED (HU010): reporte consolidado con recomendación de reabastecimiento (RF016)."""

    def setUp(self):
        unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.almacen = Almacen.objects.create(nombre='Bodega A')

        self.con_historial = Producto.objects.create(
            codigo='P001', nombre='Con historial', unidad=unidad,
            alpha=Decimal('0.5'), lead_time_dias=6, stock_seguridad=Decimal('4'),
        )
        self.sin_historial = Producto.objects.create(codigo='P002', nombre='Sin historial', unidad=unidad)

    def _crear_salida(self, producto, cantidad, fecha):
        mov = Movimiento.objects.create(
            tipo=Movimiento.SALIDA, producto=producto,
            almacen_origen=self.almacen, cantidad=Decimal(str(cantidad)),
        )
        Movimiento.objects.filter(pk=mov.pk).update(fecha=fecha)

    def test_producto_sin_historial_suficiente_marca_datos_insuficientes(self):
        filas = {f['producto'].codigo: f for f in consolidado_prediccion()}
        self.assertFalse(filas['P002']['suficiente'])
        self.assertEqual(filas['P002']['recomendacion'], 'Datos insuficientes')

    def test_recomienda_reponer_cuando_stock_es_menor_o_igual_al_rop(self):
        from almacenes.models import StockAlmacen
        StockAlmacen.objects.create(producto=self.con_historial, almacen=self.almacen, cantidad=Decimal('5'))
        for mes, cantidad in [(1, 30), (2, 30), (3, 30)]:
            self._crear_salida(self.con_historial, cantidad, timezone.make_aware(datetime(2026, mes, 5)))

        filas = {f['producto'].codigo: f for f in consolidado_prediccion()}
        fila = filas['P001']
        # demanda diaria pronosticada = 1.0, ROP = 1.0*6+4 = 10; stock = 5 <= 10.
        self.assertEqual(fila['rop'], 10.0)
        self.assertEqual(fila['recomendacion'], 'Reponer')
        self.assertEqual(fila['dias_hasta_reorden'], 0)

    def test_recomienda_stock_suficiente_y_calcula_dias_hasta_reorden(self):
        from almacenes.models import StockAlmacen
        StockAlmacen.objects.create(producto=self.con_historial, almacen=self.almacen, cantidad=Decimal('40'))
        for mes, cantidad in [(1, 30), (2, 30), (3, 30)]:
            self._crear_salida(self.con_historial, cantidad, timezone.make_aware(datetime(2026, mes, 5)))

        filas = {f['producto'].codigo: f for f in consolidado_prediccion()}
        fila = filas['P001']
        # ROP=10, stock=40, demanda_diaria=1.0 -> dias = (40-10)/1.0 = 30.0
        self.assertEqual(fila['recomendacion'], 'Stock suficiente')
        self.assertEqual(fila['dias_hasta_reorden'], 30.0)

    def test_consolidado_no_persiste_en_prediccionstock(self):
        for mes, cantidad in [(1, 30), (2, 30), (3, 30)]:
            self._crear_salida(self.con_historial, cantidad, timezone.make_aware(datetime(2026, mes, 5)))
        consolidado_prediccion()
        self.assertFalse(PrediccionStock.objects.exists())
