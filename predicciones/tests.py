from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from almacenes.models import Almacen
from movimientos.models import Movimiento
from productos.models import Producto, Unidad

from .services import MINIMO_REGISTROS_HISTORICOS, calcular_pronostico_ses, obtener_historial_mensual


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
