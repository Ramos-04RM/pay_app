# AGENTS.md - Довідка для роботи з проектом Payment Control System

## 📋 Огляд проекту

**Назва:** Payment Control System (Система контролю оплат)  
**Технології:** Django 4.2 LTS + PostgreSQL (prod) / SQLite (local)  
**Версія Python:** 3.11 (Docker image)  
**Дата створення:** квітень 2026  

Це веб-додаток для управління та моніторингу платіжних сервісів, кабінетів клієнтів та автоматизації платежів.

## 🏗️ Архітектура системи

### Основні компоненти
- **Django Web App** - основний веб-додаток
- **PostgreSQL** - основна база даних у Docker/production
- **SQLite** - локальна БД у dev режимі через `USE_SQLITE`
- **Nginx** - reverse proxy та статичні файли
- **Docker** - контейнеризація
- **Gunicorn** - WSGI сервер у контейнері `web`

### Структура проекту
```
d1/
├── d1/                    # Django settings та root URLs
├── pay_app/               # Основний додаток
│   ├── models.py          # Моделі Pay/Cabinet/Tag/CabinetTag
│   ├── views.py           # Контролери сторінок та CRUD
│   ├── services/          # Бізнес-логіка (cabinets/payments/statistics/security)
│   ├── tests/             # Набір unittest-тестів по модулях
│   ├── templates/         # HTML шаблони
│   └── static/            # CSS/JS файли
├── infra/nginx/           # Nginx конфігурація
├── docker-compose.yml     # web + db + nginx
├── entrypoint.sh          # migrate/collectstatic/superuser/gunicorn
├── requirements.txt       # Python залежності
└── AGENTS.md              # Цей файл
```

## 📊 Моделі даних

### Pay (Платіж/Сервіс)
```python
class Pay(models.Model):
    cabinet = models.ForeignKey(Cabinet, on_delete=models.DO_NOTHING)
    groups = models.CharField(max_length=50, blank=True)
    create_date = models.DateField(default=datetime.date.today)
    service = models.CharField(max_length=70)
    type_source = models.CharField(max_length=58)  # VPS/site/proxy
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8)
    pay_sys = models.CharField(max_length=50)
    paid_up_to = models.DateField(default=default_paid_up_to)
    status = models.CharField(max_length=200, null=True)  # active/not active
    email_login = models.CharField(max_length=300)  # encrypted
    password = models.CharField(max_length=300)  # encrypted
    ip = models.CharField(max_length=340, null=True)
    note_pay = models.CharField(max_length=340, blank=True, null=True)
```

### Cabinet (Кабінет клієнта)
```python
class Cabinet(models.Model):
    link = models.URLField(max_length=200, blank=True)
    login = models.CharField(max_length=260)
    password = models.CharField(max_length=260)  # encrypted
    email_login = models.EmailField(max_length=260, blank=True)
    email_password = models.CharField(max_length=260)  # encrypted
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0, null=True)
    currency = models.CharField(max_length=8)
    note = models.CharField(max_length=340, blank=True, null=True)
    is_daily_payment = models.BooleanField(default=False)
```

### Tag (Теги)
```python
class Tag(models.Model):
    name = models.CharField(max_length=120, unique=True)
    note = models.CharField(max_length=255, blank=True)

class CabinetTag(models.Model):
    cabinet = models.ForeignKey(Cabinet, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('cabinet', 'tag'), name='uniq_cabinet_tag')]
```

## 🔐 Безпека та шифрування

### ⚠️ КРИТИЧНЕ ПРАВИЛО: Обробка .env файлу
**ЧИТАЙТЕ: `.env.security-policy` ПЕРЕД ПОЧАТКОМ РОБОТИ**

**ЗАБОРОНЕНО:**
- ❌ Читати, виводити або обговорювати вміст `.env` файлу
- ❌ Вбудовувати значення з `.env` прямо в код чи конфіги
- ❌ Показувати паролі, SECRET_KEY, API ключі в повідомленнях
- ❌ Коммітити `.env` в репозиторій

**ОБОВ'ЯЗКОВО:**
- ✅ Використовувати змінні середовища: `${VARIABLE_NAME}`
- ✅ Посилатися на `.env.example` як на шаблон
- ✅ Перевіряти, що `.env` у `.gitignore`
- ✅ При оновленнях змінювати тільки `.env.example`

**Файлові правила:** Див. `.env.security-policy`

### Шифрування паролів
- Використовується бібліотека `cryptocode` для шифрування
- Основний ключ шифрування: `APP_ENCRYPTION_KEY`
- Legacy-фолбек: hash пароля користувача `LEGACY_ENCRYPTION_USER` (дефолт `admin`)
- `encrypt_value()` має захист від double-encryption через форматну перевірку

### Автентифікація
- Django auth system
- Сесії з timeout (2 години)
- Авторизація: більшість CRUD endpoint доступні будь-якому залогіненому користувачу
- Дешифрування секретів через `/decrypt_item/` дозволено тільки `is_staff`/`is_superuser`

### Вразливості (з аудиту)
- Відсутність перевірки власності записів
- Масове присвоєння без валідації
- Дефолтний `DJANGO_SECRET_KEY` у settings придатний лише для local-dev

## 🌐 API Endpoints

### Основні URL патерни
```
/                     # Головна сторінка (список платежів)
/accounts/login/      # Авторизація
/accounts/logout/     # Вихід
/pay/new/             # Додати платіж
/cabinet/new/         # Додати кабінет
/edit_page/           # Список для редагування
/edit_table/<id>      # Редагувати платіж
/delete/<id>          # Видалити платіж
/delete_cabinet/<id>  # Видалити кабінет
/cabinet/             # Сторінка кабінетів
/cabinet/<id>         # Фільтр по конкретному платежу
/cabinet_edit/<id>    # Редагування кабінету
/pay_edit/<id>        # Редагування платежу
/statistics/          # Статистика
/tags/                # Список тегів
/tags/new/            # Створення тегу
/healthz/             # Health check (публічний)
/admin/               # Django admin
```

### AJAX Endpoints
- `/decrypt_item/` - POST JSON для дешифрування `pay/cabinet` секретів (тільки staff/superuser)

## ⚙️ Налаштування та конфігурація

### Environment Variables
```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com
USE_SQLITE=0
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1

# База даних
POSTGRES_DB=app_pay_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=secure-password
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Шифрування
APP_ENCRYPTION_KEY=your-32-char-encryption-key
LEGACY_ENCRYPTION_USER=admin

# Bootstrap admin (docker entrypoint)
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=change-me

```

### Django Settings
- `DEBUG`: false в production
- `SECRET_KEY`: з `DJANGO_SECRET_KEY` (dev fallback треба замінити у production)
- `ALLOWED_HOSTS`: конкретні домени
- `SESSION_TIMEOUT`: 2 години
- `CSRF_TRUSTED_ORIGINS`: через `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASES`: SQLite у local (`USE_SQLITE=1`) або PostgreSQL (`USE_SQLITE=0`)

## 🐳 Docker та розгортання

### Docker Compose сервіси
```yaml
services:
  web:
    build: .
    env_file: [.env]
    environment: [DJANGO_DEBUG, USE_SQLITE, POSTGRES_*, DJANGO_*]
  db:
    image: postgres:16
    environment: [...]
  nginx:
    image: nginx:1.27-alpine
    ports: ["8080:80"]
```

### Команди для запуску
```bash
# Локальний запуск
set USE_SQLITE=1
python manage.py runserver

# Docker
docker compose up -d

# Production
gunicorn d1.wsgi:application --bind 0.0.0.0:8000
```

## 🧪 Тестування

### Запуск тестів
```bash
# Всі тести
python manage.py test

# Конкретний додаток
python manage.py test pay_app

# З покриттям
coverage run manage.py test
coverage report
```

### Тестові дані
- `populate_testdata.py` - скрипт для генерації 70 кабінетів + 200 платежів
- Правдоподобні дані для тестування фільтрів

### Тестові сценарії
- Авторизація/вихід
- CRUD операції з платежами
- Фільтрація за типом/статусом
- Пошук
- Статистика

## 📈 Моніторинг та логування

### Метрики для відстеження
- Кількість активних користувачів
- Час відповіді сторінок
- Помилки 4xx/5xx
- Використання CPU/RAM
- Статистика платежів

### Логи
- Django логи: стандартний logger + логування дій дешифрування (`secret_decrypt ...`)
- Nginx access/error logs у контейнері `nginx`
- Помилки: Sentry або аналог

## 🔧 Інструменти розробки

### Необхідні пакети
```
Django==4.2.14
psycopg2-binary==2.9.10
cryptocode==0.1
django-crispy-forms==1.14.0
django-session-timeout==0.1.0
whitenoise==6.8.2
gunicorn==22.0.0
six==1.16.0
```

### Рекомендовані інструменти
- **IDE**: PyCharm/VSCode з Python плагінами
- **DB**: pgAdmin або DBeaver для PostgreSQL
- **API**: Postman для тестування endpoints
- **Debug**: Django runserver + browser DevTools

## 🚀 Розгортання в продакшн

### Checklist
- [ ] `DEBUG = False`
- [ ] Безпечний `SECRET_KEY`
- [ ] HTTPS налаштований
- [ ] База даних окремо від веб-сервера
- [ ] Статичні файли через CDN
- [ ] Backup налаштований
- [ ] Моніторинг активний
- [ ] Firewall налаштований

### Хмарні провайдери
- **AWS**: EC2 + RDS + CloudWatch
- **GCP**: Compute Engine + Cloud SQL
- **Azure**: VM + Database
- **DigitalOcean**: Droplets + Managed DB

## 🤖 Cloud Agent

> Детальна специфікація у **[`agent_skills.md`](./agent_skills.md)** — workflows, rules+checklists, команди PowerShell/Docker.

### Файли агента
- [`agent_skills.md`](./agent_skills.md) — workflows: deploy / migrations / smoke test / rollback / incident triage
- `docker-compose.yml` - конфігурація
- `infra/` - конфіги інфраструктури
- `entrypoint.sh` - ініціалізація БД, staticfiles, superuser, запуск gunicorn

## 📝 TODO та покращення

### Критичні
- [ ] Додати перевірку власності записів
- [ ] Замінити cryptocode на cryptography
- [ ] Виправити масове присвоєння
- [ ] Налаштувати rate limiting

### Покращення
- [ ] API для мобільного додатку
- [ ] WebSocket для real-time оновлень
- [ ] Інтеграція з платіжними системами
- [ ] Розширені звіти та аналітика

## 📞 Контакти та підтримка

**Розробник:** Igor B.  
**Версія:** 1.0.0  
**Дата:** квітень 2026  

Для питань щодо проекту звертайтеся до основного розробника або створюйте issue в репозиторії.

---

*Цей файл автоматично згенеровано для допомоги агентам у роботі з проектом. Оновлюйте його при внесенні змін до системи.*
