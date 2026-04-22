# API and Route Reference (Markdown)

This project is server-rendered Django with HTML pages and a small JSON endpoint set.

## Authentication
Most routes require login (`@login_required`) except health check.

Auth routes come from `django.contrib.auth.urls` under `/accounts/`.

Common routes available in this project:

| Method | Path | Purpose |
|---|---|---|
| GET/POST | `/accounts/login/` | Login page + submit credentials |
| POST | `/accounts/logout/` | Logout current session |
| GET/POST | `/accounts/password_change/` | Change password |
| GET | `/accounts/password_change/done/` | Password change success page |
| GET/POST | `/accounts/password_reset/` | Request password reset |
| GET | `/accounts/password_reset/done/` | Password reset email sent page |
| GET/POST | `/accounts/reset/<uidb64>/<token>/` | Set new password from reset link |
| GET | `/accounts/reset/done/` | Password reset completion page |

## Main Routes

| Method | Path | Purpose | Auth |
|---|---|---|---|
| GET | `/` | Pay list home | Yes |
| GET | `/healthz/` | Health check JSON | No |
| GET/POST | `/pay/new/` | Create pay record | Yes |
| GET/POST | `/cabinet/new/` | Create cabinet and tags | Yes |
| GET | `/edit_page/` | Flat edit list view | Yes |
| GET/POST | `/edit_table/<id>` | Edit pay by ID | Yes |
| GET/POST | `/pay_edit/<id>` | Combined pay/cabinet edit flow | Yes |
| GET/POST | `/cabinet_edit/<id>` | Edit cabinet and tags | Yes |
| GET | `/cabinet/` | Cabinet list with advanced filters | Yes |
| GET | `/cabinet/<id>` | Pay details scoped to ID | Yes |
| GET | `/statistics/` | Analytics dashboard | Yes |
| GET | `/tags/` | Tag list and search | Yes |
| GET/POST | `/tags/new/` | Create tag | Yes |
| GET/POST | `/tags/<id>/edit/` | Edit tag | Yes |
| GET/POST | `/tags/<id>/delete/` | Delete tag | Yes |
| GET/POST | `/delete/<id>` | Delete pay | Yes |
| GET/POST | `/delete_cabinet/<id>` | Delete cabinet | Yes |

## Legacy Compatibility Routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/filter_type_sourse/<name>` | Typo alias for `filter_by_type_source` |
| GET | `/edit_tb/<id>` | Alias for `edit_table` |

## Filter/Helper Routes

| Method | Path |
|---|---|
| GET | `/sort/<name>` |
| GET | `/filter/<name>` |
| GET | `/filter_overdue_payments/<name>` |
| GET | `/filter_pay_sys/<name>` |
| GET | `/filter_type_source/<name>` |
| GET | `/filter_by_active/<name>` |
| GET | `/searching/<name>` |
| GET | `/sort_cabinet/<name>` |
| GET/POST | `/edit_dt/<id>` |

## AJAX / JSON Endpoint

### `POST /decrypt_item/`

Purpose:
- Decrypt one allowed secret field from `Pay` or `Cabinet`

Access:
- User must be authenticated
- No extra password confirmation is required

Allowed payload by model:

```json
{
  "model": "pay",
  "id": 123,
  "field": "password|email_login"
}
```

```json
{
  "model": "cabinet",
  "id": 123,
  "field": "password|email_password"
}
```

Validation behavior:
- Invalid JSON -> `400`
- Invalid model/field/id format -> `400`
- Not authenticated -> Django login redirect (`302`)
- Object not found by id -> `404`
- Empty value or decrypt fail -> `400`
- Wrong HTTP method (non-POST) -> `405`
- Success -> `200` with `{ "value": "..." }`

Security note:
- Decrypt actions are logged as structured events: `secret.decrypt.success` / `secret.decrypt.failed`
- These events are written to `logs/security.jsonl`

## Health Check

There are **two** health check endpoints with different response contracts:

### `GET /healthz/` — via Nginx (port 8080, public)

Handled directly by Nginx (`infra/nginx/default.conf`). Does **not** proxy to Django.

Returns plain text:
```
ok
```
- HTTP `200`
- No Django involvement (access log disabled)
- Use this for **container/ingress-level** liveness probes

### `GET /healthz/` — via Django directly (port 8000, internal)

Handled by `pay_app.views.healthz`. Returns JSON:
```json
{"status": "ok"}
```
- HTTP `200`
- Accessible only inside the Docker network (`http://web:8000/healthz/`)
- Use this for **application-level** health assertions in tests

> **Summary:** From outside the stack (port 8080), expect plain `ok\n`. From inside (port 8000), expect `{"status": "ok"}`.
