from django.db import models
from productos.models import Producto


class HistorialDemanda(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE,
        verbose_name="Producto"
    )
    periodo = models.DateField(verbose_name="Período (mes)")
    cantidad_consumida = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Cantidad consumida"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Historial de Demanda"
        verbose_name_plural = "Historiales de Demanda"
        ordering = ['producto', 'periodo']
        unique_together = ('producto', 'periodo')

    def __str__(self):
        return f"{self.producto} | {self.periodo} | {self.cantidad_consumida}"


class PrediccionStock(models.Model):
    producto = models.ForeignKey(
        Producto, on_delete=models.CASCADE,
        verbose_name="Producto"
    )
    fecha_calculo = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de cálculo"
    )
    alpha_utilizado = models.DecimalField(
        max_digits=5, decimal_places=4,
        verbose_name="Alpha (SES)"
    )
    demanda_pronosticada = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Demanda pronosticada"
    )
    punto_reorden = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name="Punto de reorden (ROP)"
    )
    periodos_calculados = models.PositiveIntegerField(
        default=3,
        verbose_name="Períodos calculados"
    )

    class Meta:
        verbose_name = "Predicción de Stock"
        verbose_name_plural = "Predicciones de Stock"
        ordering = ['-fecha_calculo']

    def __str__(self):
        return f"Predicción {self.producto} | ROP: {self.punto_reorden}"