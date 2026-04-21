# Architecture and Data Flow

## System Overview

```mermaid
graph TB
    Client[Browser Client] --> Nginx[Nginx :80]
    Nginx --> Web[Django Web :8000]
    Web --> DB[(PostgreSQL :5432)]
    Web --> Static[Static Files]
    Nginx --> Static
    
    subgraph "Docker Compose"
        Web
        DB
        Nginx
    end
```

## Layered Structure

```mermaid
graph TD
    Template[Template Layer<br/>pay_app/templates/] --> View[View Layer<br/>pay_app/views.py]
    View --> Service[Service Layer<br/>pay_app/services/]
    Service --> Model[Model Layer<br/>pay_app/models.py]
    Model --> Database[(Database<br/>PostgreSQL/SQLite)]
    
    subgraph "Services"
        S1[payments.py<br/>List & Filter Logic]
        S2[cabinets.py<br/>Cabinet Management]
        S3[statistics.py<br/>Analytics & Reporting]
        S4[security.py<br/>Decrypt & Auth]
        S5[daily_payment.py<br/>Payment Calculations]
    end
```

1. **View layer** (`pay_app/views.py`)
   - Validates request method/auth decorators
   - Builds forms and delegates business logic to services
   - Returns HTML or JSON responses

2. **Service layer** (`pay_app/services/`)
   - Encapsulates business rules, filtering, and derived calculations
   - Keeps views thin and reusable

3. **Model layer** (`pay_app/models.py`)
   - Defines schema and persistence behavior
   - Applies encryption in `save()` for secret fields

4. **Template layer** (`pay_app/templates/`)
   - Renders server-side HTML pages

## Request Flow Example: Pay List

```mermaid
sequenceDiagram
    participant C as Client
    participant V as views.py
    participant PS as payments.py
    participant M as Models
    participant T as Template
    
    C->>V: GET /?mode=upcoming&sort=paid_up_to_asc
    V->>PS: build_pay_list_context(request)
    PS->>PS: get_pay_list_state() - parse query params
    PS->>M: build_pay_queryset() - filter & sort
    M-->>PS: QuerySet with related data
    PS->>PS: get_pay_sidebar_context() - URLs & options
    PS-->>V: merged context dict
    V->>T: render('index.html', context)
    T-->>C: HTML response
```

## Request Flow Example: Decrypt Secret

```mermaid
sequenceDiagram
    participant C as Client
    participant V as views.py
    participant SS as security.py
    participant SEC as security.py
    participant L as Logger
    
    C->>V: POST /decrypt_item/ {"model":"pay","id":123,"field":"password"}
    V->>SS: decrypt_item_payload(request)
    SS-->>V: parsed JSON payload
    V->>SEC: decrypt_secret(user, payload)
    SEC->>SEC: validate model/field/permissions
    SEC->>SEC: decrypt_value() with key candidates
    SEC->>L: log secret_decrypt action
    SEC-->>V: {"value": "decrypted_text"}
    V-->>C: JSON response
```

## Data Integrity and Delete Behavior

- Cabinet delete route is `delete_cabinet/<id>`
- Because `Pay.cabinet` uses `DO_NOTHING`, linked service history is protected from accidental cascade deletion
- Deletion can fail when references still exist; this is expected

## Container Runtime Flow

```mermaid
graph TD
    Start([Container Start]) --> Wait[Wait for PostgreSQL]
    Wait --> Migrate[makemigrations + migrate]
    Migrate --> Static[collectstatic]
    Static --> Super[Create Superuser if needed]
    Super --> Gunicorn[Start Gunicorn :8000]
    
    subgraph "entrypoint.sh"
        Wait
        Migrate
        Static
        Super
        Gunicorn
    end
```

`entrypoint.sh` boot sequence in `web` container:
1. Wait for PostgreSQL health
2. `makemigrations pay_app`
3. `migrate`
4. `collectstatic`
5. Ensure superuser exists from env vars
6. Start Gunicorn

## Best-Practice Boundaries

- Keep filters and derived query state in `services/payments.py` and `services/cabinets.py`
- Keep analytics math in `services/statistics.py`
- Keep security and decryption checks in `services/security.py`
- Avoid coupling templates to DB logic directly

## Extension Strategy

When adding new feature behavior:
1. Add route to `pay_app/urls.py`
2. Keep view small and delegate to a service function
3. Add service-level unit tests in corresponding `pay_app/tests/tests_*.py`
4. Add docs update under `documentation/`


