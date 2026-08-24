from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from almacenes.models import Almacen, StockAlmacen
from movimientos.models import Movimiento

from .models import Producto, Unidad


class DetalleProductoTests(TestCase):
    """HU007/RF014: vista del producto con stock actual y pronóstico de demanda."""

    def setUp(self):
        User.objects.create_user('operador', password='Cl4v3Segura#88')
        self.client.login(username='operador', password='Cl4v3Segura#88')

        unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(codigo='P001', nombre='Tela algodón', unidad=unidad)
        self.almacen_a = Almacen.objects.create(nombre='Bodega A')
        self.almacen_b = Almacen.objects.create(nombre='Bodega B')
        StockAlmacen.objects.create(producto=self.producto, almacen=self.almacen_a, cantidad=Decimal('12'))
        StockAlmacen.objects.create(producto=self.producto, almacen=self.almacen_b, cantidad=Decimal('8'))

    def test_acceso_sin_login_redirige_a_login(self):
        self.client.logout()
        respuesta = self.client.get(reverse('productos:detalle', args=[self.producto.pk]))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta.url)

    def test_producto_inexistente_devuelve_404(self):
        respuesta = self.client.get(reverse('productos:detalle', args=[9999]))
        self.assertEqual(respuesta.status_code, 404)

    def test_muestra_stock_total_sumado_entre_almacenes(self):
        respuesta = self.client.get(reverse('productos:detalle', args=[self.producto.pk]))
        self.assertEqual(respuesta.context['stock_total'], Decimal('20'))

    def test_avisa_datos_insuficientes_sin_historial_de_salidas(self):
        respuesta = self.client.get(reverse('productos:detalle', args=[self.producto.pk]))
        self.assertFalse(respuesta.context['prediccion']['suficiente'])
        self.assertContains(respuesta, "Se necesitan al menos")

    def test_muestra_pronostico_con_historial_suficiente(self):
        for mes, cantidad in [(1, 5), (2, 6), (3, 7)]:
            mov = Movimiento.objects.create(
                tipo=Movimiento.SALIDA, producto=self.producto,
                almacen_origen=self.almacen_a, cantidad=Decimal(str(cantidad)),
            )
            Movimiento.objects.filter(pk=mov.pk).update(fecha=timezone.make_aware(datetime(2026, mes, 5)))

        respuesta = self.client.get(reverse('productos:detalle', args=[self.producto.pk]))
        self.assertTrue(respuesta.context['prediccion']['suficiente'])
        self.assertContains(respuesta, "Demanda pronosticada")
