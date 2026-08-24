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
    """
    Solo lectura: los movimientos deben registrarse desde /movimientos/registrar/,
    que actualiza StockAlmacen de forma atómica (RF005). Crear/editar aquí
    descuadraría el stock porque el admin no pasa por movimientos.services.
    """
    list_display = ['fecha', 'tipo', 'producto', 'almacen_origen', 'almacen_destino', 'lote', 'cantidad', 'usuario']
    list_filter = ['tipo', 'almacen_origen', 'almacen_destino']
    search_fields = ['producto__nombre', 'producto__codigo', 'lote__numero_lote']
    autocomplete_fields = ['producto', 'almacen_origen', 'almacen_destino', 'lote']
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
