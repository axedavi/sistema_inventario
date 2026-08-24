from django.urls import path

from . import views

app_name = 'movimientos'

urlpatterns = [
    path('', views.lista_movimientos, name='lista'),
    path('lotes/', views.lista_lotes, name='lotes'),
]
