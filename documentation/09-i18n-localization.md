# Internationalization (i18n) Quick Guide

This project is bilingual: Ukrainian (`uk`) and English (`en`).

## Current Project Setup
- Language settings: `d1/settings.py` -> `LANGUAGES = [('uk', ...), ('en', ...)]`
- Locale path: `d1/settings.py` -> `LOCALE_PATHS = [BASE_DIR / 'locale']`
- Middleware enabled: `LocaleMiddleware`
- Language switch route enabled in `d1/urls.py` via `path('i18n/', include('django.conf.urls.i18n'))`
- UI language switch form exists in `pay_app/templates/index.html` (`{% url 'set_language' %}`)

## Translation Files in Repo
- Source translations: `locale/uk/LC_MESSAGES/django.po`
- Compiled translations: `locale/uk/LC_MESSAGES/django.mo`

## Standard Workflow
1. Mark strings for translation in Python/templates using `gettext` / `{% trans %}`.
2. Update `.po` from source with `makemessages`.
3. Edit `locale/uk/LC_MESSAGES/django.po`.
4. Compile `.po` to `.mo` with `compilemessages`.
5. Restart app/server so new catalog is loaded.

## Commands

### Windows (PowerShell)

```powershell
# From project root
python manage.py makemessages -l uk
python manage.py compilemessages
```

### Linux / macOS

```bash
# From project root
python manage.py makemessages -l uk
python manage.py compilemessages
```

## Useful Variants

```bash
# Rebuild all configured locales
python manage.py compilemessages

# Ignore virtualenv and build artifacts during extraction
python manage.py makemessages -l uk --ignore .venv/* --ignore venv/* --ignore staticfiles/*
```

## Short Usage Guides

### Add one translatable string in Python

```python
from django.utils.translation import gettext as _

label = _("Active services")
```

### Add one translatable string in template

```django
{% load i18n %}
<h2>{% trans "Statistics" %}</h2>
```

### Switch language from UI
- Open main page `/`
- Use language selector form (posts to `set_language`)
- Choose `uk` or `en`

## Troubleshooting

### `compilemessages` fails with `msgfmt` not found
Django requires GNU gettext tools.

- Windows: install gettext (for example via Chocolatey/MSYS2), then reopen terminal.
- Linux: install `gettext` package.
- macOS: install `gettext` via Homebrew and ensure binaries are in `PATH`.

### New translation does not appear
- Confirm string is marked with `gettext`/`trans`
- Re-run `makemessages` and `compilemessages`
- Restart development server or web container

### `.po` updated but `.mo` unchanged in runtime
- Verify `locale/uk/LC_MESSAGES/django.mo` was recompiled successfully
- If using Docker, rebuild/restart container after compile

