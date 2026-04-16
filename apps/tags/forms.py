from django import forms
from django.forms import ModelForm

from apps.tags.models import Tag


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
