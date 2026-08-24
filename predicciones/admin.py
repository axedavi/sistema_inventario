from django.contrib import admin

from .models import HistorialDemanda, PrediccionStock


@admin.register(HistorialDemanda)
class HistorialDemandaAdmin(admin.ModelAdmin):
    list_display = ['producto', 'periodo', 'cantidad_consumida']
    list_filter = ['periodo']
    search_fields = ['producto__nombre', 'producto__codigo']
    autocomplete_fields = ['producto']


@admin.register(PrediccionStock)
class PrediccionStockAdmin(admin.ModelAdmin):
    list_display = ['producto', 'fecha_calculo', 'demanda_pronosticada', 'punto_reorden', 'alpha_utilizado']
    list_filter = ['fecha_calculo']
    search_fields = ['producto__nombre', 'producto__codigo']
