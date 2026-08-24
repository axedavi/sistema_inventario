from django import forms
from django.db.models import Q

from almacenes.models import Almacen
from movimientos.models import Movimiento
from productos.models import Categoria, Producto


def _aplicar_estilo(form):
    for field in form.fields.values():
        css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
        field.widget.attrs['class'] = css


class FiltroMovimientosForm(forms.Form):
    """RF015: reporte de movimientos filtrable por producto, almacén y rango de fechas."""
    producto = forms.ModelChoiceField(queryset=Producto.objects.all(), required=False, label="Producto")
    almacen = forms.ModelChoiceField(queryset=Almacen.objects.all(), required=False, label="Almacén")
    fecha_desde = forms.DateField(required=False, label="Desde", widget=forms.DateInput(attrs={'type': 'date'}))
    fecha_hasta = forms.DateField(required=False, label="Hasta", widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_estilo(self)

    def filtrar(self):
        qs = Movimiento.objects.select_related('producto', 'almacen_origen', 'almacen_destino', 'lote', 'usuario')
        if not self.is_valid():
            return qs.order_by('-fecha')

        producto = self.cleaned_data.get('producto')
        almacen = self.cleaned_data.get('almacen')
        fecha_desde = self.cleaned_data.get('fecha_desde')
        fecha_hasta = self.cleaned_data.get('fecha_hasta')

        if producto:
            qs = qs.filter(producto=producto)
        if almacen:
            qs = qs.filter(Q(almacen_origen=almacen) | Q(almacen_destino=almacen))
        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)

        return qs.order_by('-fecha')


class FiltroInventarioForm(forms.Form):
    """RF015: reporte del estado actual del inventario filtrable por producto/almacén/categoría."""
    almacen = forms.ModelChoiceField(queryset=Almacen.objects.all(), required=False, label="Almacén")
    categoria = forms.ModelChoiceField(queryset=Categoria.objects.all(), required=False, label="Categoría")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_estilo(self)

    def filtrar(self):
        qs = Producto.objects.filter(activo=True).select_related('categoria', 'unidad').prefetch_related(
            'stockalmacen_set__almacen'
        )
        if not self.is_valid():
            return qs

        almacen = self.cleaned_data.get('almacen')
        categoria = self.cleaned_data.get('categoria')
        if almacen:
            qs = qs.filter(stockalmacen__almacen=almacen).distinct()
        if categoria:
            qs = qs.filter(categoria=categoria)
        return qs
