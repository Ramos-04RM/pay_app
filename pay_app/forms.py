from django.forms import ModelForm
from django import forms
from pay_app.models import Pay, Cabinet


class DateInput(forms.DateInput):
    input_type = 'date'


class PayForm(ModelForm):
    class Meta:
        model = Pay
        fields = ['cabinet', 'groups', 'create_date', 'service', 'type_source', 'price_per_month', 'currency',
                  'pay_sys', 'paid_up_to', 'status', 'email_login', 'password', 'ip', 'note_pay']
        # fields = '__all__'  # or
        widgets = {
            'groups': forms.TextInput(attrs={'class': 'form-control'}),
            'service': forms.TextInput(attrs={'class': 'form-control'}),
            'pay_sys': forms.TextInput(attrs={'class': 'form-control'}),
            'create_date': DateInput(),
            'paid_up_to': DateInput(),
            'price_per_month': forms.NumberInput(attrs={'class': 'form-control'}),
            # 'password': forms.PasswordInput(
            #     attrs={'placeholder': '********', 'autocomplete': 'off', 'data-toggle': 'password'}),
            'ip': forms.TextInput(attrs={'placeholder': '192.168.100.1', 'class': 'form-control'}),
        }


class CabinetForm(ModelForm):
    class Meta:
        model = Cabinet
        # fields = {'link', 'login', 'password', 'email_login', 'email_password', 'note'}
        fields = '__all__'  # or

        widgets = {
            'link': forms.URLInput(attrs={'class': 'form-control'}),
            'email_login': forms.EmailInput(attrs={'class': 'form-control'}),
            # 'email_password': forms.PasswordInput(
            #     attrs={'placeholder': '********', 'autocomplete': 'off', 'data-toggle': 'password'}),
            # 'password': forms.PasswordInput(
            #     attrs={'placeholder': '********', 'autocomplete': 'off', 'data-toggle': 'password'}),

        }

