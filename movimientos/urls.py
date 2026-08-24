from django.urls import path

from . import views

app_name = 'movimientos'

urlpatterns = [
    path('', views.lista_movimientos, name='lista'),
    path('registrar/', views.registrar_movimiento, name='registrar'),
    path('lotes/', views.lista_lotes, name='lotes'),
]
