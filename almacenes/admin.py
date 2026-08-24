from django.contrib import admin

from .models import Almacen, StockAlmacen


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ubicacion', 'responsable', 'activo']
    search_fields = ['nombre']
    list_filter = ['activo']


@admin.register(StockAlmacen)
class StockAlmacenAdmin(admin.ModelAdmin):
    list_display = ['producto', 'almacen', 'cantidad', 'actualizado_en']
    list_filter = ['almacen']
    search_fields = ['producto__nombre', 'producto__codigo']
    autocomplete_fields = ['producto', 'almacen']
