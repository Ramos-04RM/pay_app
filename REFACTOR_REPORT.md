# Refactor Analysis & Plan

## A) Current-state analysis (statictic/main codebase)

### Architecture smells
- `pay_app/views.py` is a god-module handling list rendering, filters, decrypt endpoint, CRUD, statistics, and tags in one file.
- Model `save()` methods contain encryption concerns tightly coupled to a specific user (`admin`) and authentication storage implementation.
- Settings are hardcoded for local PostgreSQL credentials and debug mode, making production deployment unsafe by default.

### Bugs and fragility
- Encryption/decryption depends on `User(username='admin').password`; if this user is absent or password hash changes, decryption can fail.
- Forms and view code mix float-like handling for money (`FloatField` + float parsing), risking precision and filter inconsistency.
- Tests had non-representative coverage and a broken assumption (`Tag.slug`) that does not exist in the model.

### Security risks
- Secret key and DB credentials were committed in source.
- Decrypt endpoint allowed any authenticated user to decrypt protected fields.
- No decrypt audit trail.

### ORM/performance concerns
- Very broad views with repeated context and aggregate work increase query complexity and maintenance overhead.
- Sorting/filtering paths were spread across ad-hoc functions with duplicated state logic.

### Migration & compatibility risks
- Existing DB is populated, and model schema (including float money) is in use. Hard schema swaps (Float -> Decimal) are high-risk without data migration windows.
- Encryption format must remain backward-compatible with existing rows.

### Production readiness gaps
- No environment-driven settings profile.
- No compose stack for PostgreSQL + Gunicorn + Nginx.
- No health endpoint.

## B) Target architecture (this refactor iteration)
- Keep current DB schema for compatibility.
- Introduce encryption service module (`pay_app/security.py`) with:
  - application-level key (`APP_ENCRYPTION_KEY`) for new writes,
  - legacy fallback key compatibility via existing admin password hash.
- Harden decrypt endpoint with explicit privileged-user permission check and audit logging.
- Harden money input validation at form layer using Decimal normalization.
- Move deployment concerns to environment config and containerized production topology.
- Expand tests to cover:
  - pay list filter/search,
  - cabinet filters/tags,
  - statistics page filters,
  - create flow,
  - decrypt permission and compatibility behavior.

## C) Implementation phases completed
1. Security and settings hardening.
2. Encryption compatibility layer integrated into model save/decrypt flow.
3. Deployment assets added (Dockerfile, Compose, Nginx, env example).
4. Regression test suite expanded for key business flows.

## Deferred items / risk register
- Full modular split of `views.py` into dedicated app modules is partially deferred to reduce immediate regression risk.
- Float money field remains for DB compatibility; recommend phased Decimal migration with dual-write/read strategy in a future release.
- Template-layer cleanup into reusable component libraries can be done safely in a dedicated UI pass.
