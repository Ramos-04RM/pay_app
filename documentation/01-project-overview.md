# Project Overview

## Product Goal
Payment Control System helps teams track service subscriptions, cabinet balances, payment status, expiry windows, and cost analytics.

## Tech Stack
- Python 3.11 (Docker image)
- Django 4.2 LTS
- PostgreSQL in Docker/production
- SQLite in local development when `USE_SQLITE=1`
- Nginx reverse proxy + static files
- Gunicorn WSGI process in `web` container

## High-Level Modules
- `d1/settings.py` - environment-driven settings, security flags, DB switching
- `pay_app/models.py` - domain models (`Pay`, `Cabinet`, `Tag`, `CabinetTag`)
- `pay_app/views.py` - auth-protected web routes and CRUD endpoints
- `pay_app/services/` - business logic split by concern:
  - `payments.py` (pay list filtering/sorting/state)
  - `cabinets.py` (cabinet filtering and tag logic)
  - `statistics.py` (analytics calculations and period logic)
  - `daily_payment.py` (daily coverage calculation)
  - `security.py` (decrypt endpoint helpers)
- `pay_app/tests/` - module-level unit and integration tests

## Business Concepts
- **Cabinet**: client account entity with credentials, balance, currency, and payment mode
- **Pay**: one paid service tied to one cabinet
- **Tag**: reusable label for cabinet segmentation
- **CabinetTag**: many-to-many relation cabinet <-> tag with uniqueness constraint

## Non-Functional Priorities
- Security of encrypted credentials at rest
- Predictable filtering/sorting behavior in list pages
- Stable reporting over time ranges
- Ease of extending business logic in `services/`

## Implementation Notes
- Do not put business logic into views unless it is strictly request handling
- Prefer adding or extending service functions under `pay_app/services/`
- If you change models, review migration safety and existing tests first


