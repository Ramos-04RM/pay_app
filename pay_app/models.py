from django.db import models
import datetime
import calendar

from .security import encrypt_value


def add_one_month(value: datetime.date) -> datetime.date:
    """Return *value* moved one month forward with safe day clamping."""
    year = value.year + (1 if value.month == 12 else 0)
    month = 1 if value.month == 12 else value.month + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def default_paid_up_to() -> datetime.date:
    """Return default paid-up-to date one month from today."""
    return add_one_month(datetime.date.today())


class Pay(models.Model):
    """Service payment record tied to a cabinet and billing metadata."""
    CHOICES_TYPE_SOURCE = (
        ("VPS", "VPS"),
        ("site", "site"),
        ("proxy", "proxy")
    )
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
    cabinet = models.ForeignKey('Cabinet', on_delete=models.DO_NOTHING, verbose_name='Кабінет')
    groups = models.CharField(max_length=50, blank=True, verbose_name='Група')
    create_date = models.DateField(default=datetime.date.today, verbose_name='Дата створення')
    service = models.CharField(max_length=70, verbose_name='Сервіс')
    type_source = models.CharField(max_length=58, choices=CHOICES_TYPE_SOURCE, default=1, verbose_name='Тип ресурсу')
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Місячна плата')
    currency = models.CharField(max_length=8, default=1, choices=CHOICES_CURRENCY, verbose_name='Валюта')
    pay_sys = models.CharField(max_length=50, verbose_name='Платіжна система')
    paid_up_to = models.DateField(default=default_paid_up_to, verbose_name='Оптачено до')
    status = models.CharField(max_length=200, default=1, null=True, choices=CHOICES_ACTIVE, verbose_name='Статус')
    email_login = models.CharField(max_length=300, verbose_name='Логін')
    password = models.CharField(max_length=300, unique=False, verbose_name='Пароль')
    ip = models.CharField(max_length=340, null=True, verbose_name='Ір/port')
    note_pay = models.CharField(max_length=340, blank=True, null=True, verbose_name='Примітка')

    def save(self, *args, **kwargs) -> None:
        """Encrypt sensitive fields before persisting the pay record."""
        self.password = encrypt_value(self.password)
        self.email_login = encrypt_value(self.email_login)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Return compact identifier for admin and debug output."""
        return '%i)%s' % (self.id, self.service)


class Cabinet(models.Model):
    """Client cabinet containing credentials, balance, and billing mode."""
    CHOICES_CURRENCY = Pay.CHOICES_CURRENCY

    id = models.BigAutoField(primary_key=True, auto_created=True, serialize=False, verbose_name='ID')
    link = models.URLField(max_length=200, blank=True, verbose_name='Посилання')
    login = models.CharField(max_length=260, unique=False, verbose_name='Логін')
    password = models.CharField(max_length=260,  verbose_name='Пароль')
    email_login = models.EmailField(max_length=260, unique=False, blank=True, verbose_name='Email')
    email_password = models.CharField(max_length=260, unique=False, verbose_name='Email_password')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True, verbose_name='Баланс')
    is_daily_payment = models.BooleanField(default=False, verbose_name='Поденна оплата')
    currency = models.CharField(max_length=8, choices=CHOICES_CURRENCY, default='', verbose_name='Валюта')
    note = models.CharField(max_length=340, null=True, blank=True, verbose_name='Примітка')

    def save(self, *args, **kwargs) -> None:
        """Encrypt cabinet secret fields before writing to the database."""
        self.password = encrypt_value(self.password)
        self.email_password = encrypt_value(self.email_password)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """Return readable cabinet identity tuple for UI/admin."""
        return '%i, %s, %s' % (self.id, self.login, self.link)


class Tag(models.Model):
    """Reusable label for grouping or filtering cabinets."""
    name = models.CharField(max_length=120, unique=True, verbose_name='Назва тегу')
    note = models.CharField(max_length=255, blank=True, verbose_name='Опис')

    class Meta:
        ordering = ('name',)
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self) -> str:
        """Return tag name."""
        return self.name


class CabinetTag(models.Model):
    """Explicit relation model linking a cabinet to a tag."""
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

    def __str__(self) -> str:
        """Return compact cabinet-to-tag relation representation."""
        return f'{self.cabinet_id} -> {self.tag.name}'