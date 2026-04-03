# Clinic Management Backend — Progress Log

## Stack
- **Framework:** Django 5.2 + Django REST Framework 3.17
- **Database:** PostgreSQL (hosted on Supabase, session pooler)
- **Auth:** Supabase Auth — JWT validated server-side (ES256 via JWKS / HS256 via secret)
- **Python:** 3.12

---

## Phase 1 — Core Backend (Complete)

### Architecture
- Multi-tenant isolation: every query is scoped by `clinic_id` from the authenticated user's profile
- All models use `managed = False` (tables owned by Supabase/PostgreSQL, not Django migrations)
- `BaseModel` abstract class provides `id` (UUID, PK) and `created_at` (auto) to all models

### Apps

#### `core`
- `SupabaseJWTAuthentication` — validates Supabase-issued JWTs
  - Supports ES256 (asymmetric, JWKS endpoint) and HS256 (symmetric, secret)
  - Sets `request.user` to the matching `Profile` instance
  - Returns proper `401` for expired, invalid, or misconfigured tokens

#### `users`
| Method | Endpoint | Role Required |
|--------|----------|---------------|
| GET | `/api/users/me/` | Any authenticated |
| GET | `/api/users/` | Admin |
| POST | `/api/users/` | Admin |
| PATCH | `/api/users/<id>/role/` | Admin |
| PATCH | `/api/users/<id>/` | Admin or self |

- User creation is a two-step atomic flow: Supabase Admin API → Profile row
- Role-based permission system: `admin`, `doctor`, `lab_tech`, `receptionist`

#### `clinic`
| Method | Endpoint | Role Required |
|--------|----------|---------------|
| GET/POST | `/api/clinic/patients/` | GET: any \| POST: receptionist, admin |
| GET/PATCH | `/api/clinic/patients/<id>/` | GET: any \| PATCH: receptionist, admin |
| GET/POST | `/api/clinic/visits/` | GET: any \| POST: receptionist, admin |
| GET/PATCH | `/api/clinic/visits/<id>/` | GET: any \| PATCH: receptionist, admin, doctor |
| GET/POST | `/api/clinic/consultations/` | GET: any \| POST: doctor |
| GET | `/api/clinic/consultations/<id>/` | Any authenticated |

#### `lab`
| Method | Endpoint | Role Required |
|--------|----------|---------------|
| GET/POST | `/api/lab/tests/` | GET: any \| POST: admin |
| GET/PATCH | `/api/lab/tests/<id>/` | GET: any \| PATCH: admin |
| GET/POST | `/api/lab/orders/` | GET: any \| POST: doctor |
| GET/PATCH | `/api/lab/orders/<id>/` | GET: any \| PATCH: lab_tech, admin |
| GET/POST | `/api/lab/results/` | GET: any \| POST: lab_tech |
| GET | `/api/lab/results/<id>/` | Any authenticated |

---

## Phase 1 — Bug Fixes (Complete)

| # | Location | Bug | Fix |
|---|----------|-----|-----|
| 1 | `core/authentication.py` | ES256 token with no `SUPABASE_URL` caused unhandled `AttributeError` → 500 | Added `None` guard; returns `401` with clear message |
| 2 | `clinic/views.py`, `lab/views.py` | Raw UUID strings from request body passed directly to ORM; invalid UUIDs raised `ValueError` → 500 | Added `_parse_uuid()` helper in both files; returns `400` with field-level error |
| 3 | `users/views.py` | Supabase auth user created in step 1 could be orphaned if Profile DB insert failed in step 2 | Wrapped step 2 in try/except; on failure calls Supabase Admin API to delete the auth user before re-raising |
| 4 | `clinic/serializers.py` | `VisitStatusSerializer` defined but never used anywhere | Removed class and unused import |

---

## Phase 2 — CI/CD (Complete)

### GitHub Actions — `.github/workflows/ci.yml`

Triggers on every push to `main`/`develop` and every PR to `main`.

Pipeline steps:
1. Checkout code
2. Set up Python 3.12
3. Install `requirements.txt`
4. Run `manage.py check` (import/config validation)
5. Run `manage.py test` (full test suite)

Spins up a real PostgreSQL 16 service container — no mocked DB.

---

## Next Steps (Planned)

- [ ] Write test suite (unit + integration tests per app)
- [ ] Add pagination to list endpoints
- [ ] Add search/filter parameters (patient name, phone, test name)
- [ ] Configure production deployment (Render / Railway / Fly.io)
- [ ] Set DEBUG=False for production, configure `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`
- [ ] Add request throttling / rate limiting
- [ ] Register models in Django admin
