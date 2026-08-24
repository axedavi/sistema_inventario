from django.urls import path

from . import views

app_name = 'productos'

urlpatterns = [
    path('<int:pk>/', views.detalle_producto, name='detalle'),
]
