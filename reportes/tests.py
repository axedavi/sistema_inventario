from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from almacenes.models import Almacen, StockAlmacen
from movimientos.models import Movimiento
from productos.models import Producto, Unidad


class ReportesTestBase(TestCase):
    def setUp(self):
        User.objects.create_user('operador', password='Cl4v3Segura#88')
        self.client.login(username='operador', password='Cl4v3Segura#88')

        self.unidad = Unidad.objects.create(nombre='Unidad', abreviatura='u')
        self.producto = Producto.objects.create(codigo='P001', nombre='Tela algodón', unidad=self.unidad)
        self.otro_producto = Producto.objects.create(codigo='P002', nombre='Hilo', unidad=self.unidad)
        self.bodega_a = Almacen.objects.create(nombre='Bodega A')
        self.bodega_b = Almacen.objects.create(nombre='Bodega B')

    def _crear_movimiento(self, tipo, producto, cantidad, fecha, **kwargs):
        mov = Movimiento.objects.create(tipo=tipo, producto=producto, cantidad=Decimal(str(cantidad)), **kwargs)
        Movimiento.objects.filter(pk=mov.pk).update(fecha=fecha)
        return mov


class PanelReportesTests(ReportesTestBase):
    """CP-REP-01/HU009: reportes filtrables por producto, almacén y rango de fechas (RF015)."""

    def test_acceso_sin_login_redirige_a_login(self):
        self.client.logout()
        respuesta = self.client.get(reverse('reportes:panel'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse('usuarios:login'), respuesta.url)

    def test_filtra_movimientos_por_producto(self):
        self._crear_movimiento(
            Movimiento.ENTRADA, self.producto, 10,
            timezone.make_aware(datetime(2026, 1, 5)), almacen_destino=self.bodega_a,
        )
        self._crear_movimiento(
            Movimiento.ENTRADA, self.otro_producto, 20,
            timezone.make_aware(datetime(2026, 1, 6)), almacen_destino=self.bodega_a,
        )

        respuesta = self.client.get(reverse('reportes:panel'), {'producto': self.producto.id})
        movimientos = respuesta.context['movimientos']
        self.assertEqual(len(movimientos), 1)
        self.assertEqual(movimientos[0].producto, self.producto)

    def test_filtra_movimientos_por_rango_de_fechas(self):
        self._crear_movimiento(
            Movimiento.ENTRADA, self.producto, 10,
            timezone.make_aware(datetime(2026, 1, 5)), almacen_destino=self.bodega_a,
        )
        self._crear_movimiento(
            Movimiento.ENTRADA, self.producto, 15,
            timezone.make_aware(datetime(2026, 3, 5)), almacen_destino=self.bodega_a,
        )

        respuesta = self.client.get(reverse('reportes:panel'), {
            'fecha_desde': '2026-02-01', 'fecha_hasta': '2026-03-31',
        })
        movimientos = respuesta.context['movimientos']
        self.assertEqual(len(movimientos), 1)
        self.assertEqual(movimientos[0].cantidad, Decimal('15'))

    def test_filtra_movimientos_por_almacen_origen_o_destino(self):
        self._crear_movimiento(
            Movimiento.ENTRADA, self.producto, 10,
            timezone.make_aware(datetime(2026, 1, 5)), almacen_destino=self.bodega_a,
        )
        self._crear_movimiento(
            Movimiento.ENTRADA, self.producto, 5,
            timezone.make_aware(datetime(2026, 1, 6)), almacen_destino=self.bodega_b,
        )

        respuesta = self.client.get(reverse('reportes:panel'), {'almacen': self.bodega_b.id})
        movimientos = respuesta.context['movimientos']
        self.assertEqual(len(movimientos), 1)
        self.assertEqual(movimientos[0].almacen_destino, self.bodega_b)

    def test_reporte_de_inventario_muestra_stock_total_y_alerta(self):
        StockAlmacen.objects.create(producto=self.producto, almacen=self.bodega_a, cantidad=Decimal('2'))
        self.producto.stock_minimo = Decimal('10')
        self.producto.save()

        respuesta = self.client.get(reverse('reportes:panel'))
        filas = {f['producto'].codigo: f for f in respuesta.context['filas_inventario']}
        self.assertEqual(filas['P001']['stock_total'], Decimal('2'))
        self.assertTrue(filas['P001']['en_alerta'])


class ExportarMovimientosTests(ReportesTestBase):
    """CP-REP-01/HU009: exportación de movimientos en PDF y Excel (RF017)."""

    def setUp(self):
        super().setUp()
        self._crear_movimiento(
            Movimiento.ENTRADA, self.producto, 10,
            timezone.make_aware(datetime(2026, 1, 5)), almacen_destino=self.bodega_a,
        )
        self._crear_movimiento(
            Movimiento.SALIDA, self.producto, 4,
            timezone.make_aware(datetime(2026, 1, 6)), almacen_origen=self.bodega_a,
        )

    def test_exportar_pdf_devuelve_content_type_correcto(self):
        respuesta = self.client.get(reverse('reportes:exportar_movimientos'), {'formato': 'pdf'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')
        self.assertIn('attachment', respuesta['Content-Disposition'])
        self.assertGreater(len(respuesta.content), 0)

    def test_exportar_excel_devuelve_content_type_correcto(self):
        respuesta = self.client.get(reverse('reportes:exportar_movimientos'), {'formato': 'excel'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        self.assertGreater(len(respuesta.content), 0)

    def test_formato_invalido_devuelve_400(self):
        respuesta = self.client.get(reverse('reportes:exportar_movimientos'), {'formato': 'txt'})
        self.assertEqual(respuesta.status_code, 400)

    def test_exportacion_respeta_filtros_aplicados(self):
        respuesta = self.client.get(
            reverse('reportes:exportar_movimientos'),
            {'formato': 'excel', 'producto': self.otro_producto.id},
        )
        # Sin movimientos del otro producto, el archivo debe generarse igual (vacío) sin error.
        self.assertEqual(respuesta.status_code, 200)


class ExportarInventarioTests(ReportesTestBase):
    """CP-REP-02/HU009: exportación del estado del inventario en PDF y Excel."""

    def setUp(self):
        super().setUp()
        StockAlmacen.objects.create(producto=self.producto, almacen=self.bodega_a, cantidad=Decimal('20'))

    def test_exportar_pdf_devuelve_content_type_correcto(self):
        respuesta = self.client.get(reverse('reportes:exportar_inventario'), {'formato': 'pdf'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta['Content-Type'], 'application/pdf')

    def test_exportar_excel_devuelve_content_type_correcto(self):
        respuesta = self.client.get(reverse('reportes:exportar_inventario'), {'formato': 'excel'})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    def test_formato_invalido_devuelve_400(self):
        respuesta = self.client.get(reverse('reportes:exportar_inventario'), {'formato': ''})
        self.assertEqual(respuesta.status_code, 400)
