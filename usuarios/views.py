from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.shortcuts import redirect, render

from .decorators import administrador_requerido
from .forms import LoginForm, RegistroUsuarioForm
from .models import RegistroSesion


def _obtener_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class CustomLoginView(LoginView):
    """Inicio de sesión (HU002). No revela cuál credencial es incorrecta."""
    template_name = 'usuarios/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        RegistroSesion.objects.create(
            usuario=self.request.user,
            direccion_ip=_obtener_ip(self.request),
        )
        return response


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('usuarios:login')


@administrador_requerido
def registro_usuario(request):
    """Registro de usuarios con rol asignado (HU001, RF001)."""
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f"Usuario '{usuario.username}' registrado correctamente.")
            return redirect('usuarios:lista')
    else:
        form = RegistroUsuarioForm()
    return render(request, 'usuarios/registro.html', {'form': form})


@administrador_requerido
def lista_usuarios(request):
    usuarios = User.objects.select_related('perfil').order_by('first_name', 'username')
    return render(request, 'usuarios/lista.html', {'usuarios': usuarios})
