# Domain and Business Logic

## Core Entities

### Cabinet
Represents a client account with credentials, balance, preferred currency, and optional daily-payment mode.

Key fields:
- `balance` (`Decimal`) - available amount for service coverage
- `is_daily_payment` (`bool`) - enables paid-up-to recalculation for active services
- Encrypted at rest: `password`, `email_password`

### Pay
Represents one service billing line tied to a cabinet.

Key fields:
- `price_per_month` (`Decimal`) - monthly service amount
- `paid_up_to` (`Date`) - service coverage date
- `status` - usually `active` or `not active`
- Encrypted at rest: `email_login`, `password`

### Tag and CabinetTag
Used to segment cabinets and power filters.
- `Tag.name` is unique
- `CabinetTag` uses unique constraint on (`cabinet`, `tag`)

## Critical Business Rules

### Why `Pay.cabinet` uses `on_delete=DO_NOTHING`
`Pay` references `Cabinet` with `on_delete=models.DO_NOTHING` intentionally.

Business intent:
- Prevent automatic deletion of a cabinet if service records are still linked
- Keep billing history intact and avoid silent cascade data loss

Operational impact:
- Deleting a cabinet with linked pays can fail at DB level
- Users must remove or reassign dependent services first

**Implementation Note:** Do not change to `CASCADE` unless product explicitly accepts history loss risk

### `Cabinet.is_daily_payment` semantics
If `is_daily_payment=True`, paid-up-to is derived from current balance and active service cost.

Where implemented:
- `pay_app/services/daily_payment.py`
- function: `recalculate_cabinet_paid_up_to(cabinet_id)`

Algorithm:
1. Exit if cabinet not found or `is_daily_payment=False`
2. Load active services (`status='active'`)
3. Convert each monthly price to daily using `DAILY_DIVISOR` (currently 28)
4. Sum daily prices
5. Compute covered days as `floor(balance / total_daily)`
6. Set the same `paid_up_to` for all active pays: `today + covered_days`

Implications:
- All active services in the same daily cabinet share one computed `paid_up_to`
- Invalid monthly prices (`<=0` or parse errors) stop recalculation early

**Implementation Note:** If you change `DAILY_DIVISOR`, confirm impact on financial expectations and tests

## Encryption and Secret Handling

At-rest encryption is performed in model `save()` methods:
- `Pay.save()` encrypts `password`, `email_login`
- `Cabinet.save()` encrypts `password`, `email_password`

Key behavior:
- Primary key source: `APP_ENCRYPTION_KEY`
- Legacy fallback user: `LEGACY_ENCRYPTION_USER`
- Double-encryption protection: `is_encrypted_value()` checks payload format

Never do:
- Manual encryption in views when model `save()` already handles it
- Logging decrypted values

## Filtering and List Semantics

### Pay list (`services/payments.py`)
- Supports mode switching: `all`, `upcoming`, `overdue`
- Applies status defaults by mode
- Supports toggled binary filters:
  - cabinet balance compared to monthly payment
  - daily payment yes/no
- Uses explicit sort map (`PAY_SORT_MAP`) for predictable ordering

### Cabinet list (`services/cabinets.py`)
- Supports multi-filter search, service-state flags, tags, currency, balance range
- Tag filter behavior requires all selected tags (`matched_tag_count == len(tag_ids)`)
- Sort behavior controlled by `CABINET_SORT_MAP`

## Statistics Logic Highlights
Implemented in `pay_app/services/statistics.py`.

- Period options: month, year, last12, custom
- Base inclusion rule for services in period:
  - `create_date <= period_end`
  - `paid_up_to >= period_start`
- Proportional monthly cost calculation prevents overcounting partial-month activity
- Drill-down filters support deep inspection by expiry bucket/group/cabinet/month/status

**Implementation Note:** Statistics logic is dense; update tests before refactoring loops or period math




