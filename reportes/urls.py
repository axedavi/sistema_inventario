from django.urls import path

from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.panel_reportes, name='panel'),
    path('movimientos/exportar/', views.exportar_movimientos_vista, name='exportar_movimientos'),
    path('inventario/exportar/', views.exportar_inventario_vista, name='exportar_inventario'),
    path('consolidado/', views.reporte_consolidado, name='consolidado'),
    path('consolidado/exportar/', views.exportar_consolidado_vista, name='exportar_consolidado'),
]
