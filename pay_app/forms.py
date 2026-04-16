from decimal import Decimal, InvalidOperation

from django.forms import ModelForm
from django import forms
from pay_app.models import Pay, Cabinet, Tag


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
            'cabinet',
            'groups',
            'create_date',
            'service',
            'type_source',
            'price_per_month',
            'currency',
            'pay_sys',
            'paid_up_to',
            'status',
            'email_login',
            'password',
            'ip',
            'note_pay',
        ]
        widgets = {
            'service': forms.TextInput(attrs={'class': 'form-control'}),
            'pay_sys': forms.TextInput(attrs={'class': 'form-control'}),
            'create_date': DateInput(),
            'paid_up_to': DateInput(),
            'price_per_month': forms.NumberInput(attrs={'class': 'form-control'}),
            'ip': forms.TextInput(attrs={'placeholder': '192.168.100.1', 'class': 'form-control'}),
        }


class CabinetForm(ModelForm):
    class Meta:
        model = Cabinet
        fields = '__all__'
        widgets = {
            'link': forms.URLInput(attrs={'class': 'form-control'}),
            'email_login': forms.EmailInput(attrs={'class': 'form-control'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'currency': forms.Select(attrs={'class': 'form-control'}),
        }


class TagForm(ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'note']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Напр. Немає сервісів'}),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Необовʼязково'}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError('Назва тегу обовʼязкова.')
        return name


class CabinetTagAssignForm(forms.Form):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Теги кабінету',
    )