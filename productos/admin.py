from django.contrib import admin

from .models import Categoria, Producto, Proveedor, Unidad


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'creado_en']
    search_fields = ['nombre']


@admin.register(Unidad)
class UnidadAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'abreviatura']
    search_fields = ['nombre', 'abreviatura']


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruc', 'telefono', 'tiempo_entrega_dias', 'activo']
    search_fields = ['nombre', 'ruc']
    list_filter = ['activo']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'categoria', 'unidad', 'proveedor', 'stock_minimo', 'activo']
    search_fields = ['codigo', 'nombre']
    list_filter = ['categoria', 'activo']
    autocomplete_fields = ['categoria', 'unidad', 'proveedor']
