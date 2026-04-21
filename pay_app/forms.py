from decimal import Decimal, InvalidOperation
from typing import Any

from django.forms import ModelForm
from django import forms
from pay_app.models import Pay, Cabinet, Tag


class DateInput(forms.DateInput):
    """HTML5 date widget with stable ISO format."""
    input_type = 'date'

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize date widget with explicit `%Y-%m-%d` format."""
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(*args, **kwargs)


class PayForm(ModelForm):
    """Model form for pay CRUD with normalized money/date inputs."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Configure widgets, cabinet ordering, and date input normalization."""
        super().__init__(*args, **kwargs)
        self.fields['groups'].widget.attrs.update({
            'class': 'form-control',
            'list': 'groups-list',
            'autocomplete': 'off',
            'placeholder': 'Натисніть ↓ для вибору зі списку',
        })
        self.fields['cabinet'].queryset = Cabinet.objects.order_by('id')

        self.fields['price_per_month'].widget.attrs.update({
            'class': 'form-control',
            'step': '0.01',
            'inputmode': 'decimal',
        })
        # Keep native HTML date input widgets styled consistently.
        for field_name in ('create_date', 'paid_up_to'):
            field = self.fields[field_name]
            field.localize = False
            field.input_formats = ['%Y-%m-%d']
            field.widget.is_localized = False
            field.widget.format = '%Y-%m-%d'
            field.widget.attrs.update({'class': 'form-control'})


    def clean_price_per_month(self) -> Decimal:
        """Validate positive decimal amount with up to two fractional digits."""
        raw_value = self.cleaned_data.get('price_per_month')
        if raw_value is None or raw_value == '':
            raise forms.ValidationError('Поле "Місячна плата" обовʼязкове.')

        try:
            value_str = str(raw_value).strip().replace(',', '.')
            value = Decimal(value_str)

            if value.as_tuple().exponent < -2:
                raise forms.ValidationError('Переконайтеся, що тут не більше ніж 2 цифри після десяткової коми.')

            value = value.quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError, ValueError) as e:
            raise forms.ValidationError('Вкажіть коректну суму.')

        if value <= 0:
            raise forms.ValidationError('Сума має бути більшою за 0.')

        return value

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
            'price_per_month': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ip': forms.TextInput(attrs={'placeholder': '192.168.100.1', 'class': 'form-control'}),
        }


class CabinetForm(ModelForm):
    """Model form for cabinet create/edit operations."""

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
    """Model form for tag create/edit flows."""

    class Meta:
        model = Tag
        fields = ['name', 'note']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Напр. Немає сервісів'}),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Необовʼязково'}),
        }

    def clean_name(self) -> str:
        """Require a non-empty, trimmed tag name."""
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError('Назва тегу обовʼязкова.')
        return name


class CabinetTagAssignForm(forms.Form):
    """Form for assigning multiple tags to a cabinet."""

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Теги кабінету',
    )