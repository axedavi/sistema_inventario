from django import forms

from almacenes.models import StockAlmacen

from .models import Lote, Movimiento


class MovimientoForm(forms.ModelForm):
    nuevo_lote_numero = forms.CharField(
        label="Número de lote nuevo", max_length=100, required=False,
        help_text="Solo para entradas: crea un lote nuevo con esta entrada como cantidad inicial."
    )
    nuevo_lote_vencimiento = forms.DateField(
        label="Fecha de vencimiento del lote nuevo", required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Movimiento
        fields = ['tipo', 'producto', 'almacen_origen', 'almacen_destino', 'lote', 'cantidad', 'motivo']
        widgets = {
            'motivo': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre, field in self.fields.items():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = css
        # RF005 / HU003 cubren entrada, salida y transferencia; "Ajuste" queda
        # reservado para correcciones administrativas fuera de este alcance.
        self.fields['tipo'].choices = [
            c for c in Movimiento.TIPO_CHOICES if c[0] != Movimiento.AJUSTE
        ]
        self.fields['almacen_origen'].required = False
        self.fields['almacen_destino'].required = False
        self.fields['lote'].required = False
        self.fields['lote'].label = "Lote existente"
        self.fields['motivo'].required = False

    def clean_cantidad(self):
        cantidad = self.cleaned_data['cantidad']
        if cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")
        return cantidad

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo')
        origen = cleaned.get('almacen_origen')
        destino = cleaned.get('almacen_destino')
        cantidad = cleaned.get('cantidad')
        producto = cleaned.get('producto')
        lote = cleaned.get('lote')

        if tipo == Movimiento.ENTRADA:
            if not destino:
                self.add_error('almacen_destino', "Selecciona el almacén de destino para una entrada.")
            cleaned['almacen_origen'] = None

        elif tipo == Movimiento.SALIDA:
            if not origen:
                self.add_error('almacen_origen', "Selecciona el almacén de origen para una salida.")
            cleaned['almacen_destino'] = None

        elif tipo == Movimiento.TRANSFERENCIA:
            if not origen:
                self.add_error('almacen_origen', "Selecciona el almacén de origen.")
            if not destino:
                self.add_error('almacen_destino', "Selecciona el almacén de destino.")
            if origen and destino and origen == destino:
                self.add_error('almacen_destino', "El almacén de destino debe ser distinto al de origen.")

        if lote and producto and lote.producto_id != producto.id:
            self.add_error('lote', "El lote seleccionado no corresponde al producto elegido.")

        # HU005 / RF008: registrar un lote nuevo junto con la entrada, o
        # reutilizar uno existente, pero no ambos a la vez.
        nuevo_numero = cleaned.get('nuevo_lote_numero')
        if nuevo_numero and tipo != Movimiento.ENTRADA:
            self.add_error('nuevo_lote_numero', "Solo se puede crear un lote nuevo en una entrada.")
        if nuevo_numero and lote:
            self.add_error('nuevo_lote_numero', "Elige un lote existente o crea uno nuevo, no ambos.")
        if nuevo_numero and producto and Lote.objects.filter(producto=producto, numero_lote=nuevo_numero).exists():
            self.add_error('nuevo_lote_numero', "Ya existe un lote con ese número para este producto.")

        # RF005 / HU003: rechazar salidas o transferencias mayores al stock disponible.
        if tipo in (Movimiento.SALIDA, Movimiento.TRANSFERENCIA) and origen and producto and cantidad:
            disponible = StockAlmacen.objects.filter(
                producto=producto, almacen=origen
            ).values_list('cantidad', flat=True).first() or 0
            if cantidad > disponible:
                self.add_error(
                    'cantidad',
                    f"Stock insuficiente en {origen}: disponible {disponible}, solicitado {cantidad}."
                )

        return cleaned
