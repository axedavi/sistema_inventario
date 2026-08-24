from django.contrib import admin

from .models import Lote, Movimiento


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ['numero_lote', 'producto', 'fecha_ingreso', 'fecha_vencimiento', 'cantidad_inicial']
    search_fields = ['numero_lote', 'producto__nombre', 'producto__codigo']
    list_filter = ['fecha_ingreso']
    autocomplete_fields = ['producto']


@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'tipo', 'producto', 'almacen_origen', 'almacen_destino', 'lote', 'cantidad', 'usuario']
    list_filter = ['tipo', 'almacen_origen', 'almacen_destino']
    search_fields = ['producto__nombre', 'producto__codigo', 'lote__numero_lote']
    autocomplete_fields = ['producto', 'almacen_origen', 'almacen_destino', 'lote']
    date_hierarchy = 'fecha'
