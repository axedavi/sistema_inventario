from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def administrador_requerido(view_func):
    """Restringe el acceso a usuarios con rol Administrador (RF002)."""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        perfil = getattr(request.user, 'perfil', None)
        es_admin = request.user.is_superuser or (perfil and perfil.es_administrador)
        if not es_admin:
            messages.error(request, "No tienes permisos de administrador para acceder a esta sección.")
            return redirect('almacenes:panel')
        return view_func(request, *args, **kwargs)
    return wrapper
