from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Unidad(models.Model):
    nombre = models.CharField(max_length=50, verbose_name="Nombre")
    abreviatura = models.CharField(max_length=10, verbose_name="Abreviatura")

    class Meta:
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.abreviatura})"


class Proveedor(models.Model):
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    ruc = models.CharField(max_length=13, unique=True, verbose_name="RUC")
    telefono = models.CharField(max_length=20, blank=True, verbose_name="Teléfono")
    correo = models.EmailField(blank=True, verbose_name="Correo electrónico")
    direccion = models.TextField(blank=True, verbose_name="Dirección")
    tiempo_entrega_dias = models.PositiveIntegerField(
        default=1, verbose_name="Tiempo de entrega (días)"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Categoría"
    )
    unidad = models.ForeignKey(
        Unidad, on_delete=models.SET_NULL,
        null=True, verbose_name="Unidad de medida"
    )
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Proveedor principal"
    )
    precio_costo = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0, verbose_name="Precio de costo"
    )
    stock_minimo = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0, verbose_name="Stock mínimo"
    )
    stock_seguridad = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0, verbose_name="Stock de seguridad"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"