from decimal import Decimal, InvalidOperation

from django import forms
from django.forms import ModelForm

from apps.cabinets.models import Cabinet
from apps.services.models import Pay


class DateInput(forms.DateInput):
    input_type = 'date'


class PayForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['groups'].widget.attrs.update({
            'class': 'form-control',
            'list': 'groups-list',
            'autocomplete': 'off',
            'placeholder': 'Натисніть ↓ для вибору зі списку',
        })
        self.fields['cabinet'].queryset = Cabinet.objects.order_by('id')

    def clean_price_per_month(self):
        raw_value = self.cleaned_data.get('price_per_month')
        try:
            value = Decimal(str(raw_value)).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError):
            raise forms.ValidationError('Вкажіть коректну суму.')
        if value <= 0:
            raise forms.ValidationError('Сума має бути більшою за 0.')
        return float(value)

    class Meta:
        model = Pay
        fields = [
            'cabinet', 'groups', 'create_date', 'service', 'type_source', 'price_per_month',
            'currency', 'pay_sys', 'paid_up_to', 'status', 'email_login', 'password', 'ip', 'note_pay',
        ]
        widgets = {
            'service': forms.TextInput(attrs={'class': 'form-control'}),
            'pay_sys': forms.TextInput(attrs={'class': 'form-control'}),
            'create_date': DateInput(),
            'paid_up_to': DateInput(),
            'price_per_month': forms.NumberInput(attrs={'class': 'form-control'}),
            'ip': forms.TextInput(attrs={'placeholder': '192.168.100.1', 'class': 'form-control'}),
        }
