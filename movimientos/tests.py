from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from almacenes.models import Almacen, StockAlmacen
from productos.models import Producto, Unidad

from .models import Movimiento


class RegistrarMovimientoTests(TestCase):
    """CP-INV-01/HU003: registro de entradas, salidas y transferencias con validación de stock (RF005)."""

    def setUp(self):
        self.usuario = User.objects.create_user('operador', password='Cl4v3Segura#88')
        self.client.login(username='operador', password='Cl4v3Segura#88')

        self.unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(codigo='P001', nombre='Tela algodón', unidad=self.unidad)
        self.bodega_a = Almacen.objects.create(nombre='Bodega A')
        self.bodega_b = Almacen.objects.create(nombre='Bodega B')

    def _post(self, data):
        return self.client.post(reverse('movimientos:registrar'), data, follow=True)

    def test_entrada_incrementa_stock(self):
        respuesta = self._post({
            'tipo': Movimiento.ENTRADA, 'producto': self.producto.id,
            'almacen_destino': self.bodega_a.id, 'cantidad': '50',
        })
        self.assertContains(respuesta, "Movimiento registrado")
        stock = StockAlmacen.objects.get(producto=self.producto, almacen=self.bodega_a)
        self.assertEqual(stock.cantidad, Decimal('50'))

    def test_salida_mayor_a_stock_es_rechazada_y_no_modifica_stock(self):
        StockAlmacen.objects.create(producto=self.producto, almacen=self.bodega_a, cantidad=Decimal('10'))
        respuesta = self._post({
            'tipo': Movimiento.SALIDA, 'producto': self.producto.id,
            'almacen_origen': self.bodega_a.id, 'cantidad': '25',
        })
        self.assertContains(respuesta, "Stock insuficiente")
        stock = StockAlmacen.objects.get(producto=self.producto, almacen=self.bodega_a)
        self.assertEqual(stock.cantidad, Decimal('10'), "El stock no debe cambiar si la salida se rechaza")
        self.assertFalse(Movimiento.objects.exists(), "No debe guardarse el movimiento rechazado")

    def test_salida_valida_descuenta_stock(self):
        StockAlmacen.objects.create(producto=self.producto, almacen=self.bodega_a, cantidad=Decimal('10'))
        respuesta = self._post({
            'tipo': Movimiento.SALIDA, 'producto': self.producto.id,
            'almacen_origen': self.bodega_a.id, 'cantidad': '4',
        })
        self.assertContains(respuesta, "Movimiento registrado")
        stock = StockAlmacen.objects.get(producto=self.producto, almacen=self.bodega_a)
        self.assertEqual(stock.cantidad, Decimal('6'))

    def test_transferencia_mueve_stock_entre_almacenes(self):
        StockAlmacen.objects.create(producto=self.producto, almacen=self.bodega_a, cantidad=Decimal('20'))
        respuesta = self._post({
            'tipo': Movimiento.TRANSFERENCIA, 'producto': self.producto.id,
            'almacen_origen': self.bodega_a.id, 'almacen_destino': self.bodega_b.id,
            'cantidad': '8',
        })
        self.assertContains(respuesta, "Movimiento registrado")
        origen = StockAlmacen.objects.get(producto=self.producto, almacen=self.bodega_a)
        destino = StockAlmacen.objects.get(producto=self.producto, almacen=self.bodega_b)
        self.assertEqual(origen.cantidad, Decimal('12'))
        self.assertEqual(destino.cantidad, Decimal('8'))

    def test_transferencia_mismo_almacen_origen_y_destino_es_rechazada(self):
        StockAlmacen.objects.create(producto=self.producto, almacen=self.bodega_a, cantidad=Decimal('20'))
        respuesta = self._post({
            'tipo': Movimiento.TRANSFERENCIA, 'producto': self.producto.id,
            'almacen_origen': self.bodega_a.id, 'almacen_destino': self.bodega_a.id,
            'cantidad': '5',
        })
        self.assertContains(respuesta, "debe ser distinto")
        self.assertFalse(Movimiento.objects.exists())

    def test_movimiento_queda_vinculado_a_usuario_y_fecha(self):
        self._post({
            'tipo': Movimiento.ENTRADA, 'producto': self.producto.id,
            'almacen_destino': self.bodega_a.id, 'cantidad': '3',
        })
        movimiento = Movimiento.objects.get()
        self.assertEqual(movimiento.usuario, self.usuario)
        self.assertIsNotNone(movimiento.fecha)

    def test_acceso_sin_login_redirige_a_login(self):
        self.client.logout()
        respuesta = self.client.get(reverse('movimientos:registrar'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta.url)
