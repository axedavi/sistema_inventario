from django.conf import settings
from django.db import models


class Perfil(models.Model):
    ADMINISTRADOR = 'ADMIN'
    OPERADOR = 'OPERADOR'
    ROL_CHOICES = [
        (ADMINISTRADOR, 'Administrador'),
        (OPERADOR, 'Operador de Bodega'),
    ]

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='perfil', verbose_name="Usuario"
    )
    rol = models.CharField(
        max_length=10, choices=ROL_CHOICES,
        default=OPERADOR, verbose_name="Rol"
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

    def __str__(self):
        nombre = self.usuario.get_full_name() or self.usuario.username
        return f"{nombre} ({self.get_rol_display()})"

    @property
    def es_administrador(self):
        return self.usuario.is_superuser or self.rol == self.ADMINISTRADOR


class RegistroSesion(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sesiones', verbose_name="Usuario"
    )
    fecha_inicio = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y hora")
    direccion_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")

    class Meta:
        verbose_name = "Registro de Sesión"
        verbose_name_plural = "Registros de Sesión"
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.usuario} - {self.fecha_inicio:%Y-%m-%d %H:%M}"
