from django.contrib.auth.models import User
from django.db import models
from datetime import timedelta
import datetime
import cryptocode


class Pay(models.Model):
    today = datetime.date.today()
    month = today + timedelta(days=31)

    CHOICES_TYPE_SOURCE = (
        ("VPS", "VPS"),
        ("site", "site"),
        ("proxy", "proxy")
    )
    # CHOICES_PAY_SYS = (
    #     ("BTC", "BTC"),
    #     ("WM", "WM"),
    #     ("BTC|WM", "BTC|WM")
    # )
    CHOICES_ACTIVE = (
        ("active", "active"),
        ("not active", "not active")
    )

    CHOICES_CURRENCY = (
        ("USD $", "USD"),
        ("EURO €", "EURO"),
        ("UAH ₴", "UAH"),
        ("rub ₽", "rub")
    )
    id = models.BigAutoField(primary_key=True)
    cabinet = models.ForeignKey('Cabinet', on_delete=models.DO_NOTHING,
                                verbose_name='Кабінет')  # delete????? for One to many
    groups = models.CharField(max_length=50, blank=True, verbose_name='Група')
    create_date = models.DateField(default=today, verbose_name='Дата створення')
    service = models.CharField(max_length=70, verbose_name='Сервіс')
    type_source = models.CharField(max_length=58, choices=CHOICES_TYPE_SOURCE, default=1, verbose_name='Тип ресурсу')
    price_per_month = models.FloatField(max_length=14, verbose_name='Місячна плата')
    currency = models.CharField(max_length=8, default=1, choices=CHOICES_CURRENCY, verbose_name='Валюта')
    pay_sys = models.CharField(max_length=50, verbose_name='Платіжна система')
    paid_up_to = models.DateField(default=month, verbose_name='Оптачено до')
    status = models.CharField(max_length=200, default=1, null=True, choices=CHOICES_ACTIVE, verbose_name='Статус')
    email_login = models.CharField(max_length=300, verbose_name='Логін')
    password = models.CharField(max_length=300, unique=True, verbose_name='Пароль')
    ip = models.CharField(max_length=340, null=True, verbose_name='Ір/port')
    note_pay = models.CharField(max_length=340, blank=True, null=True, verbose_name='Примітка')

    def save(self, *args, **kwargs):
        user_psw = User.objects.get(username='admin').password
        self.password = cryptocode.encrypt(self.password, user_psw)
        self.email_login = cryptocode.encrypt(self.email_login, user_psw)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String for representing the Model object.
        """
        return '%i)%s' % (self.id, self.service)


class Cabinet(models.Model):
    id = models.BigAutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')
    link = models.URLField(max_length=200, blank=True, verbose_name='Посилання')
    login = models.CharField(max_length=260, unique=False, verbose_name='Логін')
    password = models.CharField(max_length=260,  verbose_name='Пароль')
    email_login = models.EmailField(max_length=260, unique=False, blank=True, verbose_name='Email')
    email_password = models.CharField(max_length=260, unique=False, verbose_name='Email_password')
    note = models.CharField(max_length=340, null=True, blank=True, verbose_name='Примітка')

    def save(self, *args, **kwargs):
        user_psw = User.objects.get(username='admin').password
        self.password = cryptocode.encrypt(self.password, user_psw)
        self.email_password = cryptocode.encrypt(self.email_password, user_psw)
        super().save(*args, **kwargs)

    def __str__(self):
        """
        String for representing the Model object.
        """
        return '%i, %s, %s' % (self.id, self.login, self.link)


class Tag(models.Model):
    name = models.CharField(max_length=120, unique=True, verbose_name='Назва тегу')
    note = models.CharField(max_length=255, blank=True, verbose_name='Опис')

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class CabinetTag(models.Model):
    cabinet = models.ForeignKey(
        Cabinet,
        on_delete=models.CASCADE,
        related_name='cabinet_tags',
        verbose_name='Кабінет',
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='cabinet_tags',
        verbose_name='Тег',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('tag__name', 'id')
        verbose_name = 'Тег кабінету'
        verbose_name_plural = 'Теги кабінетів'
        constraints = [
            models.UniqueConstraint(fields=('cabinet', 'tag'), name='uniq_cabinet_tag'),
        ]

    def __str__(self):
        return f'{self.cabinet_id} -> {self.tag.name}'