from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Perfil


class RegistroUsuarioTests(TestCase):
    """CP-AUT-01: Registro de usuario con rol válido (RF001, HU001)."""

    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@test.local', 'AdminClave#2026')

    def test_administrador_puede_registrar_usuario_con_rol(self):
        self.client.login(username='admin', password='AdminClave#2026')
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'operador1',
            'first_name': 'Juan',
            'last_name': 'Perez',
            'email': 'operador1@test.local',
            'rol': Perfil.OPERADOR,
            'password1': 'Cl4v3Segura#88',
            'password2': 'Cl4v3Segura#88',
        })
        self.assertRedirects(respuesta, reverse('usuarios:lista'))
        usuario = User.objects.get(username='operador1')
        self.assertEqual(usuario.perfil.rol, Perfil.OPERADOR)

    def test_correo_duplicado_es_rechazado(self):
        self.client.login(username='admin', password='AdminClave#2026')
        User.objects.create_user('existente', email='dup@test.local', password='x')
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo',
            'first_name': 'Ana',
            'last_name': 'Lopez',
            'email': 'dup@test.local',
            'rol': Perfil.OPERADOR,
            'password1': 'Cl4v3Segura#88',
            'password2': 'Cl4v3Segura#88',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(User.objects.filter(username='nuevo').exists())

    def test_operador_no_puede_registrar_usuarios(self):
        """RF002: el acceso a módulos se restringe según el rol asignado."""
        operador = User.objects.create_user('operador2', password='Cl4v3Segura#88')
        Perfil.objects.create(usuario=operador, rol=Perfil.OPERADOR)
        self.client.login(username='operador2', password='Cl4v3Segura#88')
        respuesta = self.client.get(reverse('usuarios:registro'))
        self.assertRedirects(respuesta, reverse('almacenes:panel'))


class LoginTests(TestCase):
    """CP-AUT-02: Inicio de sesión con credenciales inválidas (RF002, HU002)."""

    def setUp(self):
        self.usuario = User.objects.create_user('carlos', password='Cl4v3Segura#88')
        Perfil.objects.create(usuario=self.usuario, rol=Perfil.OPERADOR)

    def test_login_con_credenciales_invalidas_no_autentica(self):
        respuesta = self.client.post(reverse('usuarios:login'), {
            'username': 'carlos', 'password': 'incorrecta',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.wsgi_request.user.is_authenticated)

    def test_login_correcto_registra_sesion(self):
        respuesta = self.client.post(reverse('usuarios:login'), {
            'username': 'carlos', 'password': 'Cl4v3Segura#88',
        }, follow=True)
        self.assertTrue(respuesta.context['user'].is_authenticated)
        self.assertEqual(self.usuario.sesiones.count(), 1)

    def test_acceso_sin_login_redirige_a_login(self):
        respuesta = self.client.get(reverse('almacenes:panel'))
        self.assertRedirects(
            respuesta,
            f"{reverse('usuarios:login')}?next={reverse('almacenes:panel')}"
        )
