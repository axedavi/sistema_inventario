from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from almacenes.models import Almacen, StockAlmacen
from productos.models import Producto, Unidad

from .models import Lote, Movimiento


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


class RegistroLoteTests(TestCase):
    """CP-LOT-01/HU005: registro de lotes vinculado a movimientos de entrada (RF008)."""

    def setUp(self):
        self.usuario = User.objects.create_user('operador', password='Cl4v3Segura#88')
        self.client.login(username='operador', password='Cl4v3Segura#88')

        self.unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(codigo='P001', nombre='Tela algodón', unidad=self.unidad)
        self.bodega_a = Almacen.objects.create(nombre='Bodega A')

    def _post(self, data):
        return self.client.post(reverse('movimientos:registrar'), data, follow=True)

    def test_entrada_con_numero_de_lote_crea_el_lote_vinculado(self):
        respuesta = self._post({
            'tipo': Movimiento.ENTRADA, 'producto': self.producto.id,
            'almacen_destino': self.bodega_a.id, 'cantidad': '30',
            'nuevo_lote_numero': 'L-2026-001',
            'nuevo_lote_vencimiento': '2027-01-01',
        })
        self.assertContains(respuesta, "Movimiento registrado")
        lote = Lote.objects.get(producto=self.producto, numero_lote='L-2026-001')
        self.assertEqual(lote.cantidad_inicial, Decimal('30'))
        self.assertEqual(lote.fecha_ingreso, date.today())
        movimiento = Movimiento.objects.get()
        self.assertEqual(movimiento.lote, lote)

    def test_no_permite_dos_lotes_con_el_mismo_numero_para_un_producto(self):
        Lote.objects.create(
            producto=self.producto, numero_lote='L-DUP', fecha_ingreso=date.today(), cantidad_inicial=10
        )
        respuesta = self._post({
            'tipo': Movimiento.ENTRADA, 'producto': self.producto.id,
            'almacen_destino': self.bodega_a.id, 'cantidad': '5',
            'nuevo_lote_numero': 'L-DUP',
        })
        self.assertContains(respuesta, "Ya existe un lote con ese número")
        self.assertEqual(Lote.objects.filter(numero_lote='L-DUP').count(), 1)

    def test_salida_sin_lote_asigna_automaticamente_el_mas_antiguo_fifo(self):
        StockAlmacen.objects.create(producto=self.producto, almacen=self.bodega_a, cantidad=Decimal('30'))
        lote_viejo = Lote.objects.create(
            producto=self.producto, numero_lote='L-VIEJO',
            fecha_ingreso=date.today() - timedelta(days=10), cantidad_inicial=Decimal('20'),
        )
        Lote.objects.create(
            producto=self.producto, numero_lote='L-NUEVO',
            fecha_ingreso=date.today(), cantidad_inicial=Decimal('10'),
        )
        respuesta = self._post({
            'tipo': Movimiento.SALIDA, 'producto': self.producto.id,
            'almacen_origen': self.bodega_a.id, 'cantidad': '15',
        })
        self.assertContains(respuesta, "Movimiento registrado")
        movimiento = Movimiento.objects.get()
        self.assertEqual(movimiento.lote, lote_viejo)

    def test_no_se_puede_eliminar_un_lote_con_movimientos_asociados(self):
        StockAlmacen.objects.create(producto=self.producto, almacen=self.bodega_a, cantidad=Decimal('10'))
        self._post({
            'tipo': Movimiento.SALIDA, 'producto': self.producto.id,
            'almacen_origen': self.bodega_a.id, 'cantidad': '5',
            'lote': '',
        })
        lote = Lote.objects.create(
            producto=self.producto, numero_lote='L-PROTEGIDO', fecha_ingreso=date.today(), cantidad_inicial=100
        )
        Movimiento.objects.filter(lote__isnull=True).update(lote=lote)
        with self.assertRaises(ProtectedError):
            lote.delete()


class LoteVencimientoTests(TestCase):
    """CP-LOT: alerta de lotes próximos a vencer con umbral configurable (RF010)."""

    def setUp(self):
        self.unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(codigo='P001', nombre='Tela algodón', unidad=self.unidad)

    def test_esta_vencido_si_la_fecha_ya_paso(self):
        lote = Lote.objects.create(
            producto=self.producto, numero_lote='L1', fecha_ingreso=date.today(),
            fecha_vencimiento=date.today() - timedelta(days=1), cantidad_inicial=10,
        )
        self.assertTrue(lote.esta_vencido)
        self.assertFalse(lote.proximo_a_vencer(30))

    def test_proximo_a_vencer_dentro_del_umbral(self):
        lote = Lote.objects.create(
            producto=self.producto, numero_lote='L2', fecha_ingreso=date.today(),
            fecha_vencimiento=date.today() + timedelta(days=5), cantidad_inicial=10,
        )
        self.assertFalse(lote.esta_vencido)
        self.assertTrue(lote.proximo_a_vencer(umbral_dias=10))
        self.assertFalse(lote.proximo_a_vencer(umbral_dias=2))

    def test_sin_fecha_de_vencimiento_no_genera_alertas(self):
        lote = Lote.objects.create(
            producto=self.producto, numero_lote='L3', fecha_ingreso=date.today(), cantidad_inicial=10
        )
        self.assertFalse(lote.esta_vencido)
        self.assertFalse(lote.proximo_a_vencer(30))
