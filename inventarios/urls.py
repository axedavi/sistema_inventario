"""
URL configuration for inventarios project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='almacenes:panel', permanent=False)),
    path('usuarios/', include('usuarios.urls')),
    path('inventario/', include('almacenes.urls')),
    path('productos/', include('productos.urls')),
    path('movimientos/', include('movimientos.urls')),
    path('prediccion/', include('predicciones.urls')),
    path('reportes/', include('reportes.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
