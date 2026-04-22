# Testing and Quality Guide

## Testing Strategy

The project relies on Django test modules grouped by domain.

### Core Principles
- Keep tests close to business logic changes
- Validate both positive and edge-case behavior
- Prefer service-level assertions for filtering/calculation logic

## Test Commands

```powershell
python manage.py test
python manage.py test pay_app
python manage.py test pay_app.tests.tests_views
python manage.py test pay_app.tests.tests_statistics
python manage.py test pay_app.tests.tests_logging pay_app.tests.tests_services_security
coverage run manage.py test pay_app
coverage report
```

## Test Module Map

| Module | Focus |
|---|---|
| `tests_views.py` | route behavior, auth rules, rendering |
| `tests_models.py` | model defaults and persistence behavior |
| `tests_encryption.py` | encryption/decryption and guard logic |
| `tests_forms.py` | form validation rules |
| `tests_payments.py` | pay list filtering/sorting logic |
| `tests_cabinets.py` | cabinet filters and tag assignment |
| `tests_statistics.py` | reporting period and metric calculations |
| `tests_services_security.py` | decrypt endpoint security behavior |
| `tests_logging.py` | structured logging helpers and audit events |
| `tests_daily_payment.py` | daily coverage recalculation |
| `tests_signals.py` | signal-driven side effects |
| `tests_templatetags.py` | template filter helpers |

## Critical Regression Checklist
- [ ] Decrypt endpoint works for any authenticated user (no password re-confirmation)
- [ ] Security events (`auth.*`, `secret.decrypt.*`) go to `logs/security.jsonl`
- [ ] Log retention is 90 daily files for both `app.jsonl` and `security.jsonl`
- [ ] Secret fields remain encrypted at rest after save/edit
- [ ] `is_daily_payment=True` cabinets still recalculate `paid_up_to`
- [ ] Pay and cabinet list filters still combine correctly
- [ ] Statistics period filters still include partially active services
- [ ] Health checks keep dual contract (`:8080/healthz/` -> plain `ok`, internal Django `/healthz/` -> JSON)

## Quality Gate for Merge
- [ ] All changed modules have matching tests
- [ ] No silent behavior change in service-level filtering
- [ ] Migrations generated and reviewed if models changed
- [ ] Documentation updated when business behavior changed

