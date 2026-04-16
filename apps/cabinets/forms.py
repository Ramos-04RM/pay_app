from django import forms
from django.forms import ModelForm

from apps.cabinets.models import Cabinet
from apps.tags.models import Tag


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


class CabinetTagAssignForm(forms.Form):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all().order_by('name'),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Теги кабінету',
    )
