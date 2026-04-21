# Scaling and Maintainability Guidelines

## Goal
Keep the codebase understandable while adding features and handling larger data volume.

## Application-Level Scalability

### 1. Keep Service Boundaries Clear
- `payments.py` for pay list state, search, and sort logic
- `cabinets.py` for cabinet filtering and tag combinatorics
- `statistics.py` for analytics and period calculations
- `security.py` for decrypt and permission-sensitive operations

Do not move these concerns into templates or large view functions.

### 2. Query Efficiency
- Prefer `select_related` and `prefetch_related` where appropriate
- Keep filter construction deterministic (maps and explicit state parsing)
- Watch for growing loops in statistics with long periods

### 3. Data Growth Considerations
As data volume increases:
- Add/validate DB indexes for frequently filtered fields:
  - `Pay.status`, `Pay.paid_up_to`, `Pay.create_date`
  - `Pay.cabinet_id`, `Cabinet.currency`, `Cabinet.is_daily_payment`
- Re-check execution cost of statistics monthly loop logic
- Consider caching expensive aggregate views with invalidation strategy

### 4. Safe Evolution of Domain Rules
- If changing `DAILY_DIVISOR`, provide migration note and financial impact note
- If changing `on_delete=DO_NOTHING` behavior, create explicit data-retention policy first
- If changing encryption behavior, preserve backward decryption compatibility

## Team-Level Scalability

### Documentation Discipline
- Update `documentation/` on every behavior change
- Add examples for junior onboarding in complex sections
- Keep endpoint docs aligned with `pay_app/urls.py`

### Review Checklist for Complex PRs
- [ ] Service-layer logic isolated and testable
- [ ] Query count reviewed for list/statistics pages
- [ ] Security controls unchanged or intentionally updated
- [ ] Backward-compatible route behavior (including legacy aliases)
- [ ] Docs updated in this folder

## Implementation Notes
- "Scalable" here means both performance and maintainability
- A clean boundary between view and service code prevents long-term entropy


