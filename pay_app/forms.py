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
        }


class TagForm(ModelForm):
    class Meta:
        model = Tag
        fields = ['name', 'slug', 'note']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Напр. Немає сервісів'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Напр. no-services'}),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Необовʼязково'}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get('slug') or '').strip()
        if not slug:
            raise forms.ValidationError('Slug обовʼязковий.')

        qs = Tag.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Такий slug вже існує.')
        return slug


class CabinetTagAssignForm(forms.Form):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Теги кабінету',
    )