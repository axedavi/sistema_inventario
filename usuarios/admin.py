from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Perfil, RegistroSesion


class PerfilInline(admin.StackedInline):
    model = Perfil
    can_delete = False
    verbose_name_plural = "Perfil"


class CustomUserAdmin(UserAdmin):
    inlines = [PerfilInline]
    list_display = ['username', 'first_name', 'last_name', 'email', 'get_rol', 'is_active']

    @admin.display(description='Rol')
    def get_rol(self, obj):
        return getattr(obj.perfil, 'get_rol_display', lambda: '—')()


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(RegistroSesion)
class RegistroSesionAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'fecha_inicio', 'direccion_ip']
    list_filter = ['usuario']
    date_hierarchy = 'fecha_inicio'
