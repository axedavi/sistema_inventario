from django.db import models
from productos.models import Producto


class Almacen(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    ubicacion = models.TextField(blank=True, verbose_name="Ubicación")
    responsable = models.CharField(max_length=150, blank=True, verbose_name="Responsable")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Almacén"
        verbose_name_plural = "Almacenes"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class StockAlmacen(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE,
        verbose_name="Producto"
    )
    almacen = models.ForeignKey(
        Almacen, on_delete=models.CASCADE,
        verbose_name="Almacén"
    )
    cantidad = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0, verbose_name="Cantidad disponible"
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock en Almacén"
        verbose_name_plural = "Stock en Almacenes"
        unique_together = ('producto', 'almacen')

    def __str__(self):
        return f"{self.producto} | {self.almacen} | {self.cantidad}"