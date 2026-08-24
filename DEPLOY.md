# Guía de despliegue — PrediStock Loja

Despliegue en dos servicios gratuitos: **Neon** (PostgreSQL, no expira) + **Render** (aplicación Django).

## 1. Crear la base de datos en Neon

1. Entra a [neon.tech](https://neon.tech) y crea una cuenta (con GitHub es lo más rápido).
2. **New Project** → nombre `sistema-inventario` → región más cercana (o la que ofrezca por defecto) → **Create**.
3. En el dashboard del proyecto, ve a **Connection Details** / **Connect** y copia el **Connection string** (formato `postgresql://usuario:clave@ep-xxxx.neon.tech/nombre_db?sslmode=require`). Guárdalo, lo vas a necesitar en el paso 3.

## 2. Crear el servicio web en Render

1. Entra a [render.com](https://render.com) y crea una cuenta (con GitHub es lo más rápido — así Render ya tiene acceso a tus repos).
2. **New** → **Blueprint**.
3. Selecciona el repositorio `axedavi/sistema_inventario`. Render detecta automáticamente el archivo `render.yaml` de la raíz del proyecto y propone crear el servicio `predistock-loja`.
4. Antes de confirmar, Render te va a pedir el valor de la variable `DATABASE_URL` (está marcada como secreta en `render.yaml`, por eso no viaja en el repo) — pega ahí el connection string de Neon del paso 1.
5. **Apply** / **Deploy**. Render va a:
   - Instalar dependencias (`build.sh`)
   - Correr `collectstatic` y `migrate` automáticamente
   - Levantar la app con `gunicorn`

El primer build tarda varios minutos (instala pandas/statsmodels/scipy). Los despliegues siguientes son más rápidos.

## 3. Crear el primer usuario administrador

Una vez que el servicio esté "Live" en Render:

1. En el dashboard del servicio, pestaña **Shell** (consola remota).
2. Ejecuta:
   ```
   python manage.py createsuperuser
   ```
3. Sigue las instrucciones (usuario, correo, contraseña).

## 4. Verificar

Abre la URL que te da Render (algo como `https://predistock-loja.onrender.com`), inicia sesión con el usuario del paso 3, y confirma que el panel de inventario carga.

## Notas

- El plan gratuito de Render "duerme" el servicio tras 15 minutos sin tráfico; la primera visita después de eso tarda ~30 segundos en responder mientras despierta. Es un compromiso aceptable para un entorno de pruebas/demo, no para producción con usuarios reales.
- El plan gratuito de Neon incluye 0.5 GB de almacenamiento y no expira, a diferencia del PostgreSQL gratuito de Render (que sí se borra a los 30-90 días).
- Para desarrollo local seguimos usando PostgreSQL local vía las variables `DB_*` del archivo `.env` (ver `.env.example`); `DATABASE_URL` solo se usa en producción.
