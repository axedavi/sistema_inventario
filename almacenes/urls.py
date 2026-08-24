from django.urls import path

from . import views

app_name = 'almacenes'

urlpatterns = [
    path('', views.panel_inventario, name='panel'),
]
