from django.urls import path

from . import views

app_name = 'predicciones'

urlpatterns = [
    path('', views.lista_predicciones, name='lista'),
]
