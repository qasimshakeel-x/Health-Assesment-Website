# Authentication & Authorization — AI Longevity Intelligence Platform

## 1. Scheme
JWT-based stateless authentication. Library: `python-jose`. Signing algorithm: **HS256**.
Password hashing: **bcrypt**.

## 2. Tokens
| Token | Lifetime | Purpose |
|---|---|---|
| `access_token` | 24 hours | Sent as `Authorization: Bearer {token}` on every protected request |
| `refresh_token` | 7 days | Used only to obtain a new access token |

**Refresh rotation:** every call to `/auth/refresh` invalidates the old refresh token and issues a new
one. A reused/old refresh token must be rejected (store a hash or a `revoked_at` marker, not the
raw token).

## 3. Flow
1. `POST /api/v1/auth/register` — create account, bcrypt-hash password, store in `user_profiles`
   (or a dedicated `users` table — see note in §6).
2. `POST /api/v1/auth/login` — verify bcrypt hash, issue `access_token` + `refresh_token`.
3. Every protected route depends on `Depends(get_current_user)`, which decodes + validates the
   JWT, checks expiry, and loads the user.
4. On `401` (expired access token), client calls `POST /api/v1/auth/refresh` with the refresh token
   → gets a new access token + rotated refresh token.
5. Logout (if implemented): revoke the refresh token server-side (add a `revoked_at` column or a
   Redis denylist keyed by token `jti`).

## 4. Protected vs Public Endpoints
| Endpoint | Auth |
|---|---|
| `POST /auth/register` | No |
| `POST /auth/login` | No |
| `POST /auth/refresh` | No (refresh token only, not access token) |
| `POST /predict` | Yes |
| `GET /predict/{userId}/latest` | Yes |
| `GET /shap/{predictionId}` | Yes |
| `GET /simulate` | Yes |
| `POST /chat/{userId}/message` | Yes |
| `GET /chat/{userId}/history` | Yes |
| `POST /reports/{userId}/generate` | Yes |
| `GET /reports/{reportId}/status` | Yes |
| `GET /reports/{reportId}/download` | Yes |
| Admin panel routes (UC-6) | Yes + admin role |

## 5. Authorization — Admin Role
Admin is a **separate capability**, not a separate login system:
- Add a `role` column (`user` / `admin`) to the auth table.
- Admin routes check `Depends(get_current_user)` **and** `require_role("admin")`.
- Admin panel: view user profiles & predictions, delete records, trigger model retraining — every
  admin action is logged with a timestamp (who, what, when) to an `admin_action_log` table.
- Unauthorized access to admin routes → `401 Unauthorized`.
- Admin panel is never reachable by a regular patient account, and its URL/routes should not be
  advertised in the patient-facing frontend bundle.

## 6. Data model note
The SRS/SDD describe `user_profiles` as holding both health data and (implicitly) credentials. For
clean separation, prefer:
- `auth_users` — id, email, password_hash, role, created_at, refresh_token_hash/jti, revoked_at.
- `user_profiles` — id, `auth_user_id` FK, all the health intake fields.

This keeps credentials out of the health-data table and makes GDPR-style "delete my account"
simpler (cascade from `auth_users`). If the team prefers the original single-table design from the
SRS, that's acceptable too — just pick one and keep it consistent across `04-DATA-MODEL.md`.

## 7. Security Requirements (apply across every layer)
| Layer | Mechanism |
|---|---|
| Transport | HTTPS + TLS 1.3 everywhere, including DB connections (cert pinning) |
| Presentation | React `DOMPurify` on any rendered user input (XSS prevention) |
| Application | Pydantic v2 strict models on all endpoints → `422` on invalid input |
| Application | JWT bearer auth, `python-jose`, HS256, 24h/7d expiry as above |
| Business logic | Hardcoded clinical disclaimers appended server-side to every health/mental-health/cancer-screening output (not just in the frontend — so the PDF and API responses carry them too) |
| Data | SQLAlchemy ORM parameterized queries only; raw SQL forbidden |
| Data | Encryption at rest (PostgreSQL TDE / pgcrypto) |
| Data | `ANTHROPIC_API_KEY`, `DATABASE_URL`, `JWT_SECRET` — environment variables only, never in frontend code or the repo |
| Network | CORS restricted to the registered frontend origin only |
| UX | Privacy notice displayed before any health data entry |

## 8. Error Responses Related to Auth
| Error | HTTP | Message |
|---|---|---|
| Invalid credentials | 401 | "Invalid email or password." |
| Expired/invalid access token | 401 | "Session expired. Please log in again." |
| Expired/revoked refresh token | 401 | force re-login, do not silently retry |
| Admin route, non-admin user | 403 (prefer over 401 once authenticated) | "You don't have access to this." |

## 9. Testing Checklist
- `GET /predict` without token → `401`.
- `GET /predict` with expired token → `401`.
- Refresh rotation: using an already-used refresh token a second time must fail.
- Admin route with a valid non-admin token → `403`.
- Password is never returned in any API response, ever (including admin user-list endpoints).
