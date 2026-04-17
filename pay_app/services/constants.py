from decimal import Decimal

PAY_MODE_ALL = 'all'
PAY_MODE_UPCOMING = 'upcoming'
PAY_MODE_OVERDUE = 'overdue'
PAY_MODES = {PAY_MODE_ALL, PAY_MODE_UPCOMING, PAY_MODE_OVERDUE}

PAY_SORT_MAP = {
    'id_asc': ('id',),
    'id_desc': ('-id',),
    'groups_asc': ('groups', 'id'),
    'groups_desc': ('-groups', 'id'),
    'create_date_asc': ('create_date', 'id'),
    'create_date_desc': ('-create_date', 'id'),
    'service_asc': ('service', 'id'),
    'service_desc': ('-service', 'id'),
    'type_source_asc': ('type_source', 'id'),
    'type_source_desc': ('-type_source', 'id'),
    'price_per_month_asc': ('price_per_month', 'id'),
    'price_per_month_desc': ('-price_per_month', 'id'),
    'currency_asc': ('currency', 'id'),
    'currency_desc': ('-currency', 'id'),
    'cabinet_balance_asc': ('cabinet_balance_for_sort', 'id'),
    'cabinet_balance_desc': ('-cabinet_balance_for_sort', 'id'),
    'cabinet_currency_asc': ('cabinet__currency', 'id'),
    'cabinet_currency_desc': ('-cabinet__currency', 'id'),
    'pay_sys_asc': ('pay_sys', 'id'),
    'pay_sys_desc': ('-pay_sys', 'id'),
    'paid_up_to_asc': ('paid_up_to', 'id'),
    'paid_up_to_desc': ('-paid_up_to', 'id'),
    'email_login_asc': ('email_login', 'id'),
    'email_login_desc': ('-email_login', 'id'),
    'status_asc': ('status', 'id'),
    'status_desc': ('-status', 'id'),
}
PAY_SORT_DEFAULT = 'id_asc'

CABINET_SORT_MAP = {
    'login_asc': ('login', 'id'),
    'login_desc': ('-login', 'id'),
    'link_asc': ('link', 'id'),
    'link_desc': ('-link', 'id'),
    'email_login_asc': ('email_login', 'id'),
    'email_login_desc': ('-email_login', 'id'),
    'note_asc': ('note', 'id'),
    'note_desc': ('-note', 'id'),
    'services_asc': ('services_count', 'id'),
    'services_desc': ('-services_count', 'id'),
    'balance_asc': ('balance_value', 'id'),
    'balance_desc': ('-balance_value', 'id'),
    'currency_asc': ('currency', 'id'),
    'currency_desc': ('-currency', 'id'),
    'tags_asc': ('tags_count', 'login', 'id'),
    'tags_desc': ('-tags_count', 'login', 'id'),
}

STAT_PERIOD_MONTH = 'month'
STAT_PERIOD_YEAR = 'year'
STAT_PERIOD_LAST_12 = 'last12'
STAT_PERIOD_CUSTOM = 'custom'
STAT_PERIOD_CHOICES = {
    STAT_PERIOD_MONTH,
    STAT_PERIOD_YEAR,
    STAT_PERIOD_LAST_12,
    STAT_PERIOD_CUSTOM,
}

DAILY_DIVISOR = Decimal('27')
