from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from productos.models import Categoria, Producto, Unidad

from .models import Almacen, StockAlmacen


class PanelInventarioTests(TestCase):
    """CP-INV-02/HU004: vista unificada de stock con alertas de reorden (RF006)."""

    def setUp(self):
        self.usuario = User.objects.create_user('operador', password='Cl4v3Segura#88')
        self.client.login(username='operador', password='Cl4v3Segura#88')

        self.unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.categoria = Categoria.objects.create(nombre='Telas')
        self.bodega_a = Almacen.objects.create(nombre='Bodega A')
        self.bodega_b = Almacen.objects.create(nombre='Bodega B')

        self.producto_en_alerta = Producto.objects.create(
            codigo='P001', nombre='Tela algodón', unidad=self.unidad,
            categoria=self.categoria, stock_minimo=Decimal('10'),
        )
        StockAlmacen.objects.create(producto=self.producto_en_alerta, almacen=self.bodega_a, cantidad=Decimal('3'))

        self.producto_normal = Producto.objects.create(
            codigo='P002', nombre='Hilo poliéster', unidad=self.unidad, stock_minimo=Decimal('5'),
        )
        StockAlmacen.objects.create(producto=self.producto_normal, almacen=self.bodega_a, cantidad=Decimal('20'))
        StockAlmacen.objects.create(producto=self.producto_normal, almacen=self.bodega_b, cantidad=Decimal('15'))

    def test_acceso_sin_login_redirige_a_login(self):
        self.client.logout()
        respuesta = self.client.get(reverse('almacenes:panel'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta.url)

    def test_panel_marca_en_alerta_cuando_stock_es_menor_o_igual_al_minimo(self):
        respuesta = self.client.get(reverse('almacenes:panel'))
        filas = {f['producto'].codigo: f for f in respuesta.context['filas']}
        self.assertTrue(filas['P001']['en_alerta'])
        self.assertFalse(filas['P002']['en_alerta'])

    def test_panel_suma_stock_total_de_todos_los_almacenes(self):
        respuesta = self.client.get(reverse('almacenes:panel'))
        filas = {f['producto'].codigo: f for f in respuesta.context['filas']}
        self.assertEqual(filas['P002']['stock_total'], Decimal('35'))

    def test_panel_expone_datos_para_filtrado_por_almacen_y_categoria(self):
        respuesta = self.client.get(reverse('almacenes:panel'))
        contenido = respuesta.content.decode('utf-8')
        self.assertIn(f'data-almacenes="{self.bodega_a.id}"', contenido)
        self.assertIn(f'data-categoria="{self.categoria.id}"', contenido)
