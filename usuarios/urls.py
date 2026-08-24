from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('registro/', views.registro_usuario, name='registro'),
    path('', views.lista_usuarios, name='lista'),
]
