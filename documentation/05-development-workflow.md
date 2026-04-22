# Development Workflow

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Setup — Windows](#local-setup--windows)
3. [Local Setup — Linux](#local-setup--linux)
4. [Local Setup — macOS](#local-setup--macos)
5. [Docker Setup (All Platforms)](#docker-setup-all-platforms)
6. [Migration Workflow Best Practices](#migration-workflow-best-practices)
7. [Bilingual (i18n) Workflow Quick Commands](#bilingual-i18n-workflow-quick-commands)
8. [Branch and PR Checklist](#branch-and-pr-checklist)
9. [Secure Config Workflow](#secure-config-workflow)
10. [Implementation Notes](#implementation-notes)

---

## Prerequisites

Install the following on your machine before starting:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ | https://python.org |
| Git | any | https://git-scm.com |
| Docker Desktop | latest | https://docker.com/products/docker-desktop |
| Docker Compose | v2 (`docker compose`) | included in Docker Desktop |

Verify installations:

```bash
python --version
git --version
docker --version
docker compose version
```

---

## Local Setup — Windows

Runs with SQLite. No Docker required for local development.

### Step 1 — Clone the repository

```powershell
git clone <your-repo-url>
```

### Step 2 — Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> If you see a script execution policy error, run first:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 3 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 4 — Create the local environment file

```powershell
Copy-Item .env.example .env
```

Open `.env` in any editor and set minimum required values:

```dotenv
DJANGO_SECRET_KEY=any-local-dev-string
DJANGO_DEBUG=1
APP_ENCRYPTION_KEY=any-32-char-local-key-1234567890
```

> Never commit `.env`. It is already in `.gitignore`.

### Step 5 — Switch to SQLite and apply migrations

```powershell
$env:USE_SQLITE = "1"
python manage.py migrate
```

### Step 6 — Create a local superuser

```powershell
python manage.py createsuperuser
```

### Step 7 — Run the development server

```powershell
$env:USE_SQLITE = "1"
python manage.py runserver
```

Open in browser: http://127.0.0.1:8000

### Optional — Populate with test data

```powershell
$env:USE_SQLITE = "1"
python populate_testdata.py
```

---

## Local Setup — Linux

Tested on Ubuntu 22.04+. Debian-based distros work the same way.

### Step 1 — Install system dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git
```

### Step 2 — Clone the repository

```bash
git clone <your-repo-url>
```

### Step 3 — Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 5 — Create the local environment file

```bash
cp .env.example .env
nano .env
```

Set at minimum:

```dotenv
DJANGO_SECRET_KEY=any-local-dev-string
DJANGO_DEBUG=1
APP_ENCRYPTION_KEY=any-32-char-local-key-1234567890
```

### Step 6 — Switch to SQLite and apply migrations

```bash
USE_SQLITE=1 python manage.py migrate
```

### Step 7 — Create a local superuser

```bash
USE_SQLITE=1 python manage.py createsuperuser
```

### Step 8 — Run the development server

```bash
USE_SQLITE=1 python manage.py runserver
```

Open in browser: http://127.0.0.1:8000

### Optional — Populate with test data

```bash
USE_SQLITE=1 python populate_testdata.py
```

---

## Local Setup — macOS

Tested on macOS 13+.

### Step 1 — Install Homebrew and system dependencies

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.11 git
```

### Step 2 — Clone the repository

```bash
git clone <your-repo-url>
```

### Step 3 — Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

> On Apple Silicon (M1/M2/M3), `psycopg2-binary` installs fine from pip.
> If you see build errors, use:
> ```bash
> arch -arm64 pip install psycopg2-binary
> ```

### Step 5 — Create the local environment file

```bash
cp .env.example .env
open -e .env
```

Set at minimum:

```dotenv
DJANGO_SECRET_KEY=any-local-dev-string
DJANGO_DEBUG=1
APP_ENCRYPTION_KEY=any-32-char-local-key-1234567890
```

### Step 6 — Switch to SQLite and apply migrations

```bash
USE_SQLITE=1 python manage.py migrate
```

### Step 7 — Create a local superuser

```bash
USE_SQLITE=1 python manage.py createsuperuser
```

### Step 8 — Run the development server

```bash
USE_SQLITE=1 python manage.py runserver
```

Open in browser: http://127.0.0.1:8000

### Optional — Populate with test data

```bash
USE_SQLITE=1 python populate_testdata.py
```

---

## Docker Setup (All Platforms)

Runs the full production-like stack: `web` (Django + Gunicorn) + `db` (PostgreSQL 16) + `nginx` (port 8080).

### Step 1 — Ensure Docker is running

```bash
docker info
```

### Step 2 — Clone the repository (if not done)

```bash
git clone <your-repo-url>
```

### Step 3 — Create the environment file

**Windows:**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Edit `.env` and set secure values:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-strong-secret
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,nginx
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
APP_ENCRYPTION_KEY=replace-with-a-strong-32-char-key
POSTGRES_PASSWORD=replace-with-a-strong-db-password
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=replace-with-a-strong-admin-password
```

### Step 4 — Build and start the stack

```bash
docker compose up -d --build
```

### Step 5 — Verify all containers are running

```bash
docker compose ps
```

Expected:
```
NAME    STATUS          PORTS
web     Up              (no public port — accessed via nginx)
db      Up (healthy)    5432/tcp
nginx   Up              0.0.0.0:8080->80/tcp
```

> Note: `web` has no published port by default. All external traffic is routed through `nginx` on port 8080.

### Step 6 — Check startup logs

```bash
docker compose logs web --tail=60
```

Look for:
- `Applying migrations... OK`
- `Collecting static files... OK`
- `Starting Gunicorn...`

### Step 7 — Verify the application is running

```bash
curl http://localhost:8080/healthz/
```

Expected: `ok` (plain text — returned by Nginx directly, no Django involvement).

To check the Django JSON health endpoint from inside the stack:

```bash
docker compose exec web curl -s http://web:8000/healthz/
```

Expected: `{"status": "ok"}`

Open in browser: http://localhost:8080

### Step 8 — Log in

- **App:** http://localhost:8080/accounts/login/
- **Admin:** http://localhost:8080/admin
- Credentials: `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD` from your `.env`

### Stopping the stack

```bash
# Stop, keep data
docker compose down

# Stop and destroy DB volume (dev only — all data lost)
docker compose down -v
```

### Rebuild after code changes

```bash
docker compose up -d --build
docker compose logs web --tail=30
```

---

## Migration Workflow Best Practices

1. Change models in `pay_app/models.py`
2. Create migration explicitly
3. Review generated migration file before applying
4. Apply migration
5. Run tests
6. Update documentation if behavior changed

**Local — Windows:**
```powershell
$env:USE_SQLITE = "1"
python manage.py makemigrations pay_app
python manage.py migrate
python manage.py test pay_app
```

**Local — Linux / macOS:**
```bash
USE_SQLITE=1 python manage.py makemigrations pay_app
USE_SQLITE=1 python manage.py migrate
USE_SQLITE=1 python manage.py test pay_app
```

**Docker (all platforms):**
```bash
docker compose exec web python manage.py makemigrations pay_app
docker compose exec web python manage.py migrate
docker compose exec web python manage.py showmigrations pay_app
```

---

## Bilingual (i18n) Workflow Quick Commands

For detailed bilingual workflow and troubleshooting, see [`documentation/09-i18n-localization.md`](./09-i18n-localization.md).

### Build `django.mo` from `django.po`

```powershell
python manage.py compilemessages
```

### Update Ukrainian catalog from source strings

```powershell
python manage.py makemessages -l uk
python manage.py compilemessages
```

Linux/macOS use the same commands in a shell.

---

## Branch and PR Checklist
- [ ] Feature branch created from latest main
- [ ] Business logic kept in `pay_app/services/`
- [ ] Tests added/updated in `pay_app/tests/`
- [ ] No secret values committed
- [ ] `.env` not in git
- [ ] `documentation/` updated for behavior changes

---

## Secure Config Workflow
- Use `.env.example` as the only safe template — edit this, not `.env`
- Keep production secret values outside the repository
- Ensure `DJANGO_DEBUG=0` in all non-local environments
- Ensure `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` are set to actual domain/IP
- See `.env.security-policy` for full rules

---

## Implementation Notes
- If in doubt, modify service functions first, not view functions
- Re-run the affected test module before the full suite for faster feedback
- Never bypass migration review when model fields change

