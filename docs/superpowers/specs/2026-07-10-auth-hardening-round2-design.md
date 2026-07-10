# Auth Hardening — Round 2 (Design Spec)

- **Date:** 2026-07-10
- **Area:** `role_engine.py` (RBAC/auth), `settings_engine.py`, theme meta-injection, `deploy/` nginx, `add_sales_users.py`
- **Status:** Approved design — pending implementation plan
- **Predecessor:** Round 1 bug sweep (commit `36ae242`). This is the follow-up "auth hardening" tranche.

## Problem

The current PIN-based auth has three concrete weaknesses:

1. **Unsalted SHA-256 PIN hashing.** `hash_pin()` (`role_engine.py:192`) is `sha256(pin).hexdigest()` — no salt, no KDF stretching. Over a 4-digit numeric space (10k) this is trivially brute-forced / rainbow-tableable offline if `bitumen_dashboard.db` leaks.
2. **Flat login throttle.** `_is_rate_limited` (`role_engine.py:202`) allows 5 failed attempts per 5-minute window, per username, with no escalation. A patient attacker gets ~1,440 guesses/day — enough to sweep a 4-digit space in ~1 week.
3. **Auth token in the URL.** `_write_token_to_url` (`role_engine.py:117`) puts the HMAC-signed session token in the `auth_t` query param. URLs leak via the HTTP `Referer` header, browser history, shared links, and server access logs, enabling session replay within the token's 24h lifetime.

## Goals

- Salt + stretch PIN hashes (PBKDF2) with **zero user disruption** (no forced resets, no lockouts).
- Make online PIN brute-forcing impractical via **escalating lockout**.
- Close the **Referer-header leak** vector for the auth token and shrink its validity window.
- Keep the app's stdlib-only / no-new-dependency philosophy.

## Non-Goals (deferred by explicit decision)

- Moving the auth token out of the URL into a cookie (fully removes the URL leak but needs a Streamlit cookie component + restore-flow rework). Deferred; residual risk documented below.
- Raising the minimum PIN length beyond the current 4 digits. Deferred; escalating throttle carries the load for this ~5-user internal tool.
- Migrating away from PIN auth (e.g. to passwords/OAuth). Out of scope.

## Design

### Component 1 — Salted PBKDF2 PIN hashing (`role_engine.py`)

**Self-describing hash format** stored in the existing `users.pin_hash` TEXT column (no schema change):

```
pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>
```

- `_PBKDF2_ITERATIONS = 200_000` (module constant).
- Salt: `secrets.token_bytes(16)`, base64-encoded.
- Hash: `hashlib.pbkdf2_hmac('sha256', pin.encode(), salt, iterations)`, base64-encoded.

**Functions:**

- `hash_pin(pin: str) -> str` — CHANGED to emit the PBKDF2 format. Used at all **creation** sites (`init_roles`, `render_user_management` create + reset, `add_sales_users.py`), which therefore produce PBKDF2 hashes automatically.
- `verify_pin(pin: str, stored: str) -> tuple[bool, bool]` — NEW. Returns `(is_valid, needs_upgrade)`.
  - Legacy detection: `stored` is 64 lowercase-hex chars with no `$` → compare `sha256(pin).hexdigest()` via `hmac.compare_digest` → `(match, True)`.
  - New format: `stored` starts with `pbkdf2_sha256$` → parse iters/salt/hash, recompute, `hmac.compare_digest` → `(match, iters < _PBKDF2_ITERATIONS)`.
  - Unknown/empty → `(False, False)`.
- `_is_legacy_hash(s: str) -> bool` — helper (`len==64 and all hex`).

**Lazy migration in `login()` (`role_engine.py:340`):** replace the inline `hmac.compare_digest(pin_hash, hash_pin(pin))` with `verify_pin(pin, pin_hash)`. On success **and** `needs_upgrade`, call `update_user(user["id"], {"pin_hash": hash_pin(pin)})` before returning. → Old SHA-256 hashes keep working and transparently upgrade to PBKDF2 on the user's next login. No forced resets, no data migration.

### Component 2 — Escalating throttle (`role_engine.py`)

`_is_rate_limited(username) -> tuple[bool, int]` — CHANGED to return `(locked, retry_after_sec)`. Tiers evaluated strictest-first against the DB `login_attempts` log (windows measured from now; lock measured from the most recent attempt):

| Fails within window | Window | Lockout |
|---|---|---|
| ≥ 15 | 2 h | 2 h |
| ≥ 10 | 30 min | 30 min |
| ≥ 5 | 5 min | 5 min |

- Constant: `_THROTTLE_TIERS = [(15, 7200, 7200), (10, 1800, 1800), (5, 300, 300)]` as `(threshold, window_sec, lockout_sec)`.
- `retry_after_sec = max(0, last_attempt_ts + lockout_sec - now)` for the highest tier met.
- DB-backed (existing `login_attempts` table) with the current in-memory dict fallback preserved.
- **Callers updated:** `login()` early-return and `render_login_form()` both consume the tuple; the login UI surfaces the wait time (e.g. "Too many attempts — try again in N min").
- `_record_failed_attempt` / `_clear_failed_attempts` unchanged.

### Component 3 — Token-leak mitigation (referrer + TTL)

**(a) Referer-header suppression (two layers):**
- In-app: inject `<meta name="referrer" content="no-referrer">` into the page `<head>` via the existing theme JS meta-injection path (same mechanism that injects viewport/PWA meta). Controls the `Referer` header for sub-resource requests originating from the page.
- Edge: add `add_header Referrer-Policy "no-referrer" always;` to the nginx `server` block in `deploy/` (setup script + any committed nginx conf). Defense-in-depth for the top-level document.

**(b) Shorter, decoupled token TTL:**
- New setting `rbac_token_ttl_min` in `settings_engine.DEFAULT_SETTINGS`, default **720** (12h), independent of `rbac_session_timeout_min` (still 1440).
- `_write_token_to_url` computes expiry from `rbac_token_ttl_min` (not the session-timeout minutes). Token is still slid forward on each authenticated render, so an active user is never interrupted; an idle/stolen URL dies within ≤12h.

**(c) Keep the token out of nginx access logs:** in the nginx conf, strip/omit the query string for logging on the app location (e.g. log `$uri` rather than `$request`, or a `map` that blanks `auth_t`). Documented as part of the deploy change.

**Residual risk (accepted):** the token still lands in browser history and any shared URL. The complete fix (cookie storage) is deferred (see Non-Goals). This spec closes the Referer-header and access-log vectors and halves the exposure window.

### Small in-scope cleanup

- `add_sales_users.py` — stop printing plaintext PINs to stdout (`:36,:39,:80`). Hashing already routes through `hash_pin`, so created users get PBKDF2 automatically.

## Testing (TDD)

New `tests/test_auth_hardening.py`:

- `hash_pin` emits `pbkdf2_sha256$…` format; distinct salts across calls.
- `verify_pin` round-trips a PBKDF2 hash (correct PIN → valid, `needs_upgrade=False`).
- `verify_pin` accepts a legacy SHA-256 hash for the correct PIN and reports `needs_upgrade=True`.
- `verify_pin` rejects a wrong PIN for both legacy and new formats.
- `login()` upgrades a legacy hash to PBKDF2 on successful auth (DB mocked/`tmp_db`).
- Throttle tiers: 5 fails → ~5-min lock; 10 fails → ~30-min lock; 15 fails → ~2-h lock (attempt timestamps injected).
- `_write_token_to_url` / token expiry honors `rbac_token_ttl_min`.

Regression guard: grep for any existing test asserting `hash_pin` equals a known SHA-256 literal and update it to the new contract.

## Files Touched

- `role_engine.py` — `hash_pin`, new `verify_pin`/`_is_legacy_hash`, `login` lazy upgrade, escalating `_is_rate_limited`, token TTL from new setting, login-UI wait-time message.
- `settings_engine.py` — add `rbac_token_ttl_min` default.
- theme meta-injection helper (`theme.py`) — referrer meta tag.
- `deploy/` — nginx `Referrer-Policy` header + auth-token log suppression.
- `add_sales_users.py` — remove plaintext PIN printing.
- `tests/test_auth_hardening.py` — new.

## Rollout / Safety Notes

- Backward compatible: legacy hashes verify until each user next logs in. No downtime, no reset.
- `admin/0000` default account continues to work and upgrades on first login; changing that default PIN remains a separate operational task.
- PBKDF2 at 200k iters adds a few ms per login — negligible for a ~5-user tool.
- Set `AUTH_SECRET` (env / `st.secrets`) in prod so tokens survive redeploys (already required today; unchanged by this work).
