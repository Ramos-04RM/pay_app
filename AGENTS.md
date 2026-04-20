# AGENTS.md - Довідка для роботи з проектом Payment Control System

## 📋 Огляд проекту

**Назва:** Payment Control System (Система контролю оплат)  
**Технології:** Django 4.2 LTS + PostgreSQL  
**Версія Python:** 3.12.5  
**Дата створення:** квітень 2026  

Це веб-додаток для управління та моніторингу платіжних сервісів, кабінетів клієнтів та автоматизації платежів.

## 🏗️ Архітектура системи

### Основні компоненти
- **Django Web App** - основний веб-додаток
- **PostgreSQL** - основна база даних
- **Redis** - кешування сесій та тимчасових даних
- **Nginx** - reverse proxy та статичні файли
- **Docker** - контейнеризація
- **Cloud Agent** - автоматизація хмарної інфраструктури

### Структура проекту
```
d1-prod/
├── d1/                    # Django settings
├── pay_app/              # Основний додаток
│   ├── models.py         # Моделі даних
│   ├── views.py          # Представлення
│   ├── services/         # Бізнес-логіка
│   ├── templates/        # HTML шаблони
│   └── static/           # CSS/JS файли
├── infra/                # Інфраструктура
├── requirements.txt      # Python залежності
├── docker-compose.yml    # Docker конфігурація
└── AGENTS.md            # Цей файл
```

## 📊 Моделі даних

### Pay (Платіж/Сервіс)
```python
class Pay(models.Model):
    cabinet = models.ForeignKey(Cabinet, on_delete=models.CASCADE)
    groups = models.CharField(max_length=100)
    create_date = models.DateField(default=today)
    service = models.CharField(max_length=255)
    type_source = models.CharField(max_length=50)  # VPS/site/proxy
    price_per_month = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    pay_sys = models.CharField(max_length=50)
    paid_up_to = models.DateField()
    status = models.CharField(max_length=20)  # active/not active
    email_login = models.CharField(max_length=255)
    password = models.CharField(max_length=255)  # encrypted
    ip = models.CharField(max_length=50, blank=True)
    note_pay = models.TextField(blank=True)
```

### Cabinet (Кабінет клієнта)
```python
class Cabinet(models.Model):
    link = models.URLField()
    login = models.CharField(max_length=255)
    password = models.CharField(max_length=255)  # encrypted
    email_login = models.CharField(max_length=255)
    email_password = models.CharField(max_length=255)  # encrypted
    balance = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    note = models.TextField(blank=True)
    is_daily_payment = models.BooleanField(default=False)
```

### Tag (Теги)
```python
class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    note = models.TextField(blank=True)

class CabinetTag(models.Model):
    cabinet = models.ForeignKey(Cabinet, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
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
- Ключ шифрування: `APP_ENCRYPTION_KEY` (з env або порожній)
- Фолбек: шифрування через пароль користувача (небезпечно!)

### Автентифікація
- Django auth system
- Сесії з timeout (2 години)
- Авторизація: будь-який залогінений користувач може редагувати всі записи

### Вразливості (з аудиту)
- Відсутність перевірки власності записів
- Масове присвоєння без валідації
- Хардкоджені креденціали в settings
- Старий SECRET_KEY

## 🌐 API Endpoints

### Основні URL патерни
```
/                     # Головна сторінка (список кабінетів)
/login/               # Авторизація
/logout/              # Вихід
/add_pay/             # Додати платіж
/edit_table/          # Редагувати таблицю платежів
/delete/<id>/         # Видалити платіж
/cabinet/<id>/        # Деталі кабінету
/statistics/          # Статистика
/healthz/             # Health check (публічний)
/admin/               # Django admin
```

### AJAX Endpoints
- `/edit_table/` - POST для масового оновлення
- `/pay_edit/<id>/` - Редагування платежу
- `/delete/<id>/` - Видалення

## ⚙️ Налаштування та конфігурація

### Environment Variables
```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# База даних
POSTGRES_DB=app_pay_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=secure-password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Шифрування
APP_ENCRYPTION_KEY=your-32-char-encryption-key

# Хмара (опціонально)
CLOUD_PROVIDER=aws
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
```

### Django Settings
- `DEBUG`: false в production
- `SECRET_KEY`: унікальний, не дефолтний
- `ALLOWED_HOSTS`: конкретні домени
- `SESSION_TIMEOUT`: 2 години
- `CSRF_TRUSTED_ORIGINS`: для HTTPS

## 🐳 Docker та розгортання

### Docker Compose сервіси
```yaml
services:
  web:
    build: .
    ports: ["8000:8000"]
    environment: [...]
  db:
    image: postgres:15
    environment: [...]
  redis:
    image: redis:7-alpine
```

### Команди для запуску
```bash
# Локальний запуск
python manage.py runserver

# Docker
docker-compose up -d

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
- Правдоподібні дані для тестування фільтрів

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
- Django логи: `DEBUG` рівень
- SQL запити: через django-debug-toolbar
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
```

### Рекомендовані інструменти
- **IDE**: PyCharm/VSCode з Python плагінами
- **DB**: pgAdmin або DBeaver для PostgreSQL
- **API**: Postman для тестування endpoints
- **Debug**: django-debug-toolbar

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

### Навички агента
- Інфраструктура як код (IaC)
- Автоматичне масштабовування
- Моніторинг та алерти
- Backup та disaster recovery
- CI/CD pipelines

### Файли агента
- `cloud_agent_skills.py` - основні скіли
- `docker-compose.yml` - конфігурація
- `infra/` - конфіги інфраструктури

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
