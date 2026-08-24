from datetime import date

from django.db import models
from django.contrib.auth.models import User
from productos.models import Producto, Proveedor
from almacenes.models import Almacen


class Lote(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE,
        verbose_name="Producto"
    )
    numero_lote = models.CharField(max_length=100, verbose_name="Número de lote")
    fecha_ingreso = models.DateField(verbose_name="Fecha de ingreso")
    fecha_vencimiento = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha de vencimiento"
    )
    cantidad_inicial = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Cantidad inicial"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ['-fecha_ingreso']
        unique_together = ('producto', 'numero_lote')

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.producto}"

    @property
    def cantidad_consumida(self):
        total = self.movimiento_set.filter(
            tipo__in=[Movimiento.SALIDA, Movimiento.TRANSFERENCIA]
        ).aggregate(total=models.Sum('cantidad'))['total']
        return total or 0

    @property
    def cantidad_disponible(self):
        return self.cantidad_inicial - self.cantidad_consumida

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - date.today()).days

    @property
    def esta_vencido(self):
        dias = self.dias_para_vencer
        return dias is not None and dias < 0

    def proximo_a_vencer(self, umbral_dias=30):
        dias = self.dias_para_vencer
        return dias is not None and 0 <= dias <= umbral_dias


class Movimiento(models.Model):
    ENTRADA = 'E'
    SALIDA = 'S'
    TRANSFERENCIA = 'T'
    AJUSTE = 'A'
    TIPO_CHOICES = [
        (ENTRADA, 'Entrada'),
        (SALIDA, 'Salida'),
        (TRANSFERENCIA, 'Transferencia'),
        (AJUSTE, 'Ajuste'),
    ]

    tipo = models.CharField(
        max_length=1, choices=TIPO_CHOICES,
        verbose_name="Tipo de movimiento"
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT,
        verbose_name="Producto"
    )
    almacen_origen = models.ForeignKey(
        Almacen, on_delete=models.PROTECT,
        related_name='salidas',
        null=True, blank=True,
        verbose_name="Almacén origen"
    )
    almacen_destino = models.ForeignKey(
        Almacen, on_delete=models.PROTECT,
        related_name='entradas',
        null=True, blank=True,
        verbose_name="Almacén destino"
    )
    lote = models.ForeignKey(
        Lote, on_delete=models.PROTECT,
        null=True, blank=True,
        verbose_name="Lote"
    )
    cantidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Cantidad"
    )
    motivo = models.TextField(blank=True, verbose_name="Motivo / Observación")
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, verbose_name="Usuario"
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha")

    class Meta:
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.get_tipo_display()} | {self.producto} | {self.cantidad}"