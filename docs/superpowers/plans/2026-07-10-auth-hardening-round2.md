# Auth Hardening Round 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden PIN-based auth with salted PBKDF2 hashing (lazy-migrated), escalating login lockout, and auth-token leak mitigation — with zero user disruption.

**Architecture:** All auth logic stays in `role_engine.py`. A self-describing PBKDF2 hash format lets old SHA-256 hashes verify and upgrade transparently on next login (no schema/data migration). Throttle logic is extracted into a pure, unit-testable function. Token-leak mitigation combines an in-app `no-referrer` meta tag, an nginx `Referrer-Policy` header + query-stripped access log, and a shorter, decoupled token TTL.

**Tech Stack:** Python 3.12, stdlib `hashlib.pbkdf2_hmac` / `hmac` / `secrets` / `base64` (no new dependency), pytest, Streamlit, nginx.

## Global Constraints

- No new Python dependency — stdlib only (matches the repo's no-ORM/no-extra-dep philosophy).
- `pin_hash` stays a plain `TEXT` column — no schema migration.
- Backward compatible — legacy SHA-256 hashes must keep verifying; no forced resets, no lockouts.
- New PBKDF2 format string: `pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>`.
- Constants: `_PBKDF2_ITERATIONS = 200_000`, `_PBKDF2_SALT_BYTES = 16`.
- Throttle tiers (threshold, window_sec, lockout_sec): `(15, 7200, 7200)`, `(10, 1800, 1800)`, `(5, 300, 300)`.
- New setting `rbac_token_ttl_min` default `720` (12h), independent of `rbac_session_timeout_min` (1440).
- Work happens on branch `feature/auth-hardening-round2`.
- Tests live in `tests/test_auth_hardening.py`; repo root from a test file is `Path(__file__).resolve().parents[1]`.

---

### Task 1: PBKDF2 hashing + `verify_pin` (pure functions)

**Files:**
- Modify: `role_engine.py` (imports already include `base64`, `hashlib`, `hmac`, `secrets`; `hash_pin` at `:192`)
- Test: `tests/test_auth_hardening.py` (create)

**Interfaces:**
- Produces:
  - `hash_pin(pin: str) -> str` — now returns `pbkdf2_sha256$200000$<salt_b64>$<hash_b64>`
  - `verify_pin(pin: str, stored: str) -> tuple[bool, bool]` — `(is_valid, needs_upgrade)`
  - `_is_legacy_hash(stored: str) -> bool`
  - Module constants `_PBKDF2_ALGO`, `_PBKDF2_ITERATIONS`, `_PBKDF2_SALT_BYTES`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_auth_hardening.py`:

```python
"""Round-2 auth hardening tests: PBKDF2 hashing, lazy upgrade, throttle, token TTL."""
import hashlib
import time
from pathlib import Path

import pytest

import role_engine as re


def _legacy_sha256(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def test_hash_pin_emits_pbkdf2_format():
    h = re.hash_pin("1234")
    parts = h.split("$")
    assert parts[0] == "pbkdf2_sha256"
    assert int(parts[1]) == re._PBKDF2_ITERATIONS
    assert len(parts) == 4


def test_hash_pin_uses_distinct_salts():
    assert re.hash_pin("1234") != re.hash_pin("1234")


def test_verify_pin_roundtrip_pbkdf2():
    h = re.hash_pin("4321")
    valid, needs_upgrade = re.verify_pin("4321", h)
    assert valid is True
    assert needs_upgrade is False


def test_verify_pin_rejects_wrong_pin_pbkdf2():
    h = re.hash_pin("4321")
    valid, needs_upgrade = re.verify_pin("0000", h)
    assert valid is False
    assert needs_upgrade is False


def test_verify_pin_accepts_legacy_and_flags_upgrade():
    valid, needs_upgrade = re.verify_pin("1234", _legacy_sha256("1234"))
    assert valid is True
    assert needs_upgrade is True


def test_verify_pin_rejects_wrong_pin_legacy():
    valid, needs_upgrade = re.verify_pin("9999", _legacy_sha256("1234"))
    assert valid is False
    assert needs_upgrade is False


def test_verify_pin_empty_stored():
    assert re.verify_pin("1234", "") == (False, False)


def test_is_legacy_hash():
    assert re._is_legacy_hash(_legacy_sha256("1234")) is True
    assert re._is_legacy_hash(re.hash_pin("1234")) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth_hardening.py -v`
Expected: FAIL — `AttributeError: module 'role_engine' has no attribute 'verify_pin'` (and `_PBKDF2_ITERATIONS`).

- [ ] **Step 3: Implement in `role_engine.py`**

Replace the existing `hash_pin` (currently `role_engine.py:192-194`):

```python
def hash_pin(pin: str) -> str:
    """Return a salted PBKDF2-SHA256 hash: pbkdf2_sha256$<iters>$<salt_b64>$<hash_b64>."""
    salt = secrets.token_bytes(_PBKDF2_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return "{}${}${}${}".format(
        _PBKDF2_ALGO,
        _PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(dk).decode("ascii"),
    )


def _is_legacy_hash(stored: str) -> bool:
    """True if `stored` is a bare legacy SHA-256 hex digest (64 hex chars, no '$')."""
    return len(stored) == 64 and all(c in "0123456789abcdef" for c in stored.lower())


def verify_pin(pin: str, stored: str) -> tuple[bool, bool]:
    """Verify `pin` against `stored`. Returns (is_valid, needs_upgrade).

    needs_upgrade is True only on a *successful* match against a legacy hash
    or a PBKDF2 hash with fewer than the current iteration count.
    """
    if not stored:
        return (False, False)
    if _is_legacy_hash(stored):
        match = hmac.compare_digest(
            stored, hashlib.sha256(pin.encode("utf-8")).hexdigest())
        return (match, match)
    if stored.startswith(_PBKDF2_ALGO + "$"):
        try:
            _algo, iters_s, salt_b64, hash_b64 = stored.split("$")
            iters = int(iters_s)
            salt = base64.b64decode(salt_b64)
            expected = base64.b64decode(hash_b64)
            dk = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt, iters)
            match = hmac.compare_digest(dk, expected)
            return (match, match and iters < _PBKDF2_ITERATIONS)
        except Exception:
            return (False, False)
    return (False, False)
```

Add these constants just above `hash_pin` (near the rate-limit constants block, `role_engine.py:181-185`):

```python
# ── PIN Hashing (PBKDF2) ─────────────────────────────────────────────────────
_PBKDF2_ALGO = "pbkdf2_sha256"
_PBKDF2_ITERATIONS = 200_000
_PBKDF2_SALT_BYTES = 16
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth_hardening.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Check for existing tests that assume raw SHA-256**

Run: `git grep -n "hash_pin" -- tests/ *.py`
Expected: review each hit. Any assertion comparing `hash_pin(x) == <known sha256 hex>` or `hash_pin(x) == hash_pin(x)` is now invalid (salted) and must be updated to `verify_pin`. (`add_sales_users.py` is handled in Task 7.) If a test breaks, note it and fix in this commit.

- [ ] **Step 6: Commit**

```bash
git add role_engine.py tests/test_auth_hardening.py
git commit -m "feat(auth): salted PBKDF2 pin hashing + verify_pin with legacy support"
```

---

### Task 2: Lazy upgrade on login

**Files:**
- Modify: `role_engine.py` — `login()` at `:328-372`
- Test: `tests/test_auth_hardening.py`

**Interfaces:**
- Consumes: `verify_pin` (Task 1), `database.get_user_by_username`, `database.update_user`
- Produces: `login(username, pin) -> bool` upgrades a legacy hash to PBKDF2 on successful auth.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auth_hardening.py`:

```python
import sys
import types


@pytest.fixture
def fake_streamlit(monkeypatch):
    st = types.ModuleType("streamlit")
    st.session_state = {}
    st.query_params = {}
    monkeypatch.setitem(sys.modules, "streamlit", st)
    return st


def test_login_upgrades_legacy_hash(fake_streamlit, monkeypatch):
    captured = []

    user = {
        "id": 7, "username": "bob", "role": "sales", "is_active": 1,
        "display_name": "Bob", "pin_hash": _legacy_sha256("1234"),
    }

    import database
    monkeypatch.setattr(database, "get_user_by_username", lambda u: dict(user), raising=False)
    monkeypatch.setattr(database, "update_user", lambda i, d: captured.append((i, d)), raising=False)
    monkeypatch.setattr(database, "insert_audit_log", lambda d: None, raising=False)
    monkeypatch.setattr(re, "_is_rate_limited", lambda u: (False, 0))
    monkeypatch.setattr(re, "_clear_failed_attempts", lambda u: None)

    assert re.login("bob", "1234") is True

    pin_updates = [d for (_i, d) in captured if "pin_hash" in d]
    assert pin_updates, "expected a pin_hash upgrade write"
    assert pin_updates[-1]["pin_hash"].startswith("pbkdf2_sha256$")


def test_login_wrong_pin_no_upgrade(fake_streamlit, monkeypatch):
    captured = []
    user = {
        "id": 7, "username": "bob", "role": "sales", "is_active": 1,
        "display_name": "Bob", "pin_hash": _legacy_sha256("1234"),
    }
    import database
    monkeypatch.setattr(database, "get_user_by_username", lambda u: dict(user), raising=False)
    monkeypatch.setattr(database, "update_user", lambda i, d: captured.append((i, d)), raising=False)
    monkeypatch.setattr(database, "insert_audit_log", lambda d: None, raising=False)
    monkeypatch.setattr(re, "_is_rate_limited", lambda u: (False, 0))
    recorded = []
    monkeypatch.setattr(re, "_record_failed_attempt", lambda u: recorded.append(u))

    assert re.login("bob", "0000") is False
    assert not any("pin_hash" in d for (_i, d) in captured)
    assert recorded == ["bob"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_auth_hardening.py::test_login_upgrades_legacy_hash -v`
Expected: FAIL — current `login` compares with `hmac.compare_digest(pin_hash, hash_pin(pin))`, which never matches a salted `hash_pin(pin)` against a legacy stored hash, so login returns False.

- [ ] **Step 3: Implement — update `login()` credential check**

In `role_engine.py`, inside `login()`, replace the credential check block (currently `:340-341`):

```python
        user = get_user_by_username(username)
        if user and user.get("is_active") and hmac.compare_digest(
                str(user.get("pin_hash") or ""), hash_pin(pin)):
```

with:

```python
        user = get_user_by_username(username)
        _valid, _needs_upgrade = (False, False)
        if user and user.get("is_active"):
            _valid, _needs_upgrade = verify_pin(pin, str(user.get("pin_hash") or ""))
        if user and user.get("is_active") and _valid:
```

Then, immediately after the existing `update_user(user["id"], {"last_login": _now_ist()})` line (currently `:353`), add the upgrade write:

```python
            update_user(user["id"], {"last_login": _now_ist()})
            if _needs_upgrade:
                try:
                    update_user(user["id"], {"pin_hash": hash_pin(pin)})
                except Exception:
                    pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth_hardening.py -v`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add role_engine.py tests/test_auth_hardening.py
git commit -m "feat(auth): lazy-upgrade legacy pin hashes to PBKDF2 on login"
```

---

### Task 3: Escalating throttle

**Files:**
- Modify: `role_engine.py` — `_is_rate_limited` at `:202-226`; callers `login` `:333`, `render_login_form` `:498-503`
- Test: `tests/test_auth_hardening.py`

**Interfaces:**
- Produces:
  - `_evaluate_throttle(timestamps: list[float], now: float) -> tuple[bool, int]` (pure)
  - `_is_rate_limited(username: str) -> tuple[bool, int]` (was `-> bool`)
  - Module constant `_THROTTLE_TIERS`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auth_hardening.py`:

```python
def test_throttle_tier_5():
    now = 1_000_000.0
    ts = [now - i for i in range(5)]  # 5 fails within seconds
    locked, retry = re._evaluate_throttle(ts, now)
    assert locked is True
    assert 0 < retry <= 300


def test_throttle_tier_10():
    now = 1_000_000.0
    ts = [now - i * 60 for i in range(10)]  # 10 fails within 9 min
    locked, retry = re._evaluate_throttle(ts, now)
    assert locked is True
    assert 300 < retry <= 1800


def test_throttle_tier_15():
    now = 1_000_000.0
    ts = [now - i * 120 for i in range(15)]  # 15 fails within 28 min
    locked, retry = re._evaluate_throttle(ts, now)
    assert locked is True
    assert 1800 < retry <= 7200


def test_throttle_below_threshold():
    now = 1_000_000.0
    ts = [now - i for i in range(4)]  # only 4 fails
    assert re._evaluate_throttle(ts, now) == (False, 0)


def test_throttle_stale_attempts_ignored():
    now = 1_000_000.0
    ts = [now - 400 - i for i in range(5)]  # 5 fails, all older than 5-min window
    assert re._evaluate_throttle(ts, now) == (False, 0)
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_auth_hardening.py::test_throttle_tier_5 -v`
Expected: FAIL — `AttributeError: module 'role_engine' has no attribute '_evaluate_throttle'`.

- [ ] **Step 3: Implement**

In `role_engine.py`, add the tiers constant next to the existing rate-limit constants (`:184-185`):

```python
# (threshold_fails, window_sec, lockout_sec) — evaluated strictest first
_THROTTLE_TIERS = [
    (15, 7200, 7200),
    (10, 1800, 1800),
    (5, 300, 300),
]
```

Add the pure evaluator (place directly above `_is_rate_limited`):

```python
def _evaluate_throttle(timestamps: list[float], now: float) -> tuple[bool, int]:
    """Given failed-attempt timestamps, return (locked, retry_after_sec)."""
    for threshold, window_sec, lockout_sec in _THROTTLE_TIERS:
        recent = [t for t in timestamps if now - t < window_sec]
        if len(recent) >= threshold:
            retry = int(max(recent) + lockout_sec - now)
            if retry > 0:
                return (True, retry)
    return (False, 0)
```

Replace `_is_rate_limited` (`:202-226`) with:

```python
def _is_rate_limited(username: str) -> tuple[bool, int]:
    """Return (locked, retry_after_sec) using escalating tiers. DB-backed so the
    lockout SURVIVES a Streamlit restart; falls back to memory if DB is down."""
    key = username.lower().strip()
    now = time.time()
    max_window = _THROTTLE_TIERS[0][1]
    cutoff = now - max_window
    try:
        from database import _get_conn
        conn = _get_conn()
        try:
            _attempts_table(conn)
            conn.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff,))
            conn.commit()
            rows = conn.execute(
                "SELECT attempted_at FROM login_attempts WHERE username = ? AND attempted_at >= ?",
                (key, cutoff)).fetchall()
            timestamps = [r[0] for r in rows]
        finally:
            conn.close()
    except Exception:
        timestamps = [t for t in _failed_attempts.get(key, []) if now - t < max_window]
        _failed_attempts[key] = timestamps
    return _evaluate_throttle(timestamps, now)
```

Update caller in `login()` (`:333`):

```python
    # Rate limiting check
    if _is_rate_limited(username)[0]:
        return False
```

Update caller in `render_login_form()` (`:497-503`) — replace the `if _is_rate_limited(uname):` branch:

```python
            uname = username.strip().lower()
            _locked, _retry = _is_rate_limited(uname)
            if _locked:
                _mins = max(1, _retry // 60)
                st.error(f"Too many failed attempts. Try again in ~{_mins} min.")
            elif login(username, pin):
                st.rerun()
            else:
                st.error("Invalid username or PIN.")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth_hardening.py -v`
Expected: PASS (15 tests).

- [ ] **Step 5: Commit**

```bash
git add role_engine.py tests/test_auth_hardening.py
git commit -m "feat(auth): escalating login lockout (5/10/15-fail tiers)"
```

---

### Task 4: Decoupled, shorter token TTL

**Files:**
- Modify: `settings_engine.py` — `DEFAULT_SETTINGS` at `:128`
- Modify: `role_engine.py` — add `_get_token_ttl_minutes`; `_write_token_to_url` at `:117-126`
- Test: `tests/test_auth_hardening.py`

**Interfaces:**
- Produces: `_get_token_ttl_minutes() -> int` (default 720); `_write_token_to_url` uses it for token expiry.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auth_hardening.py`:

```python
def test_token_ttl_default(monkeypatch):
    import settings_engine
    monkeypatch.setattr(settings_engine, "get", lambda k, d=None: d, raising=False)
    assert re._get_token_ttl_minutes() == 720


def test_token_ttl_honors_setting(monkeypatch):
    import settings_engine
    monkeypatch.setattr(
        settings_engine, "get",
        lambda k, d=None: 480 if k == "rbac_token_ttl_min" else d, raising=False)
    assert re._get_token_ttl_minutes() == 480
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_auth_hardening.py::test_token_ttl_default -v`
Expected: FAIL — `AttributeError: module 'role_engine' has no attribute '_get_token_ttl_minutes'`.

- [ ] **Step 3: Implement**

In `settings_engine.py`, add after the `"rbac_session_timeout_min": 1440,` line (`:128`):

```python
    "rbac_token_ttl_min": 720,
```

In `role_engine.py`, add next to `_get_session_timeout_minutes` (`:264-270`):

```python
def _get_token_ttl_minutes() -> int:
    """Auth-token lifetime in minutes. Shorter than the session timeout so a
    leaked ?auth_t= URL expires faster. Default 12h."""
    try:
        from settings_engine import get as get_setting
        return int(get_setting("rbac_token_ttl_min", 720))
    except Exception:
        return 720
```

In `_write_token_to_url` (`:122`), change:

```python
        expiry_ts = int(time.time() + _get_session_timeout_minutes() * 60)
```

to:

```python
        expiry_ts = int(time.time() + _get_token_ttl_minutes() * 60)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth_hardening.py -v`
Expected: PASS (17 tests).

- [ ] **Step 5: Commit**

```bash
git add role_engine.py settings_engine.py tests/test_auth_hardening.py
git commit -m "feat(auth): decouple token TTL from session timeout (default 12h)"
```

---

### Task 5: In-app `no-referrer` meta tag

**Files:**
- Modify: `theme.py` — JS meta-injection block after the viewport meta (`:522-528`)
- Test: `tests/test_auth_hardening.py`

**Interfaces:**
- Produces: the injected head script now creates `<meta name="referrer" content="no-referrer">`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auth_hardening.py`:

```python
def test_theme_injects_referrer_meta():
    root = Path(__file__).resolve().parents[1]
    src = (root / "theme.py").read_text(encoding="utf-8")
    assert "name=\"referrer\"" in src or "name='referrer'" in src
    assert "no-referrer" in src
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_auth_hardening.py::test_theme_injects_referrer_meta -v`
Expected: FAIL — `theme.py` has no referrer meta yet.

- [ ] **Step 3: Implement**

In `theme.py`, immediately after the viewport meta block (after the closing `}` of the `if (!document.querySelector('meta[name="viewport"]'))` block, `:528`), insert:

```javascript
            // Referrer policy — keep the ?auth_t= token out of the Referer header
            if (!document.querySelector('meta[name="referrer"]')) {
                var rf = document.createElement('meta');
                rf.name = 'referrer';
                rf.content = 'no-referrer';
                document.head.appendChild(rf);
            }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_auth_hardening.py::test_theme_injects_referrer_meta -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add theme.py tests/test_auth_hardening.py
git commit -m "feat(auth): inject no-referrer meta to stop auth token leaking via Referer"
```

---

### Task 6: nginx `Referrer-Policy` + query-stripped access log

**Files:**
- Modify: `deploy/hostinger_setup.sh` — nginx block at `:187-208`
- Test: `tests/test_auth_hardening.py`

**Interfaces:**
- Produces: nginx config emits `Referrer-Policy: no-referrer` and logs without the query string (`pps_noqs` format).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auth_hardening.py`:

```python
def test_nginx_referrer_and_logformat():
    root = Path(__file__).resolve().parents[1]
    src = (root / "deploy" / "hostinger_setup.sh").read_text(encoding="utf-8")
    assert 'Referrer-Policy "no-referrer"' in src
    assert "pps_noqs" in src
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_auth_hardening.py::test_nginx_referrer_and_logformat -v`
Expected: FAIL — the setup script has neither string yet.

- [ ] **Step 3: Implement**

In `deploy/hostinger_setup.sh`, add a log-format file **before** the `cat > "$NGINX_CONF"` heredoc (before `:187`):

```bash
# Query-string-free log format so ?auth_t= tokens never hit the access log
cat > /etc/nginx/conf.d/pps_logformat.conf <<'EOF'
log_format pps_noqs '$remote_addr - $remote_user [$time_local] '
                    '"$request_method $uri $server_protocol" '
                    '$status $body_bytes_sent "$http_referer" "$http_user_agent"';
EOF
```

Then, inside the server block heredoc, right after the `client_max_body_size 50M;` line (`:192`), add:

```
    # Round-2 auth hardening
    add_header Referrer-Policy "no-referrer" always;
    access_log /var/log/nginx/${SVC_NAME}.access.log pps_noqs;
```

Note: `${SVC_NAME}` is bash-interpolated (the server heredoc is unquoted `<<EOF`), which is intended — it resolves to the service name at install time. The `pps_logformat.conf` heredoc is single-quoted (`<<'EOF'`) so nginx's `$` variables survive.

- [ ] **Step 4: Verify script syntax + test passes**

Run: `bash -n deploy/hostinger_setup.sh && python -m pytest tests/test_auth_hardening.py::test_nginx_referrer_and_logformat -v`
Expected: no bash syntax error; test PASS. (`nginx -t` runs on the actual VPS at deploy time — not in CI.)

- [ ] **Step 5: Commit**

```bash
git add deploy/hostinger_setup.sh tests/test_auth_hardening.py
git commit -m "feat(auth): nginx Referrer-Policy header + query-stripped access log"
```

---

### Task 7: Stop leaking plaintext PINs in `add_sales_users.py`

**Files:**
- Modify: `add_sales_users.py` — import `:5`, verify line `:54`, print lines `:36,:39,:78-80`
- Test: `tests/test_auth_hardening.py`

**Interfaces:**
- Consumes: `verify_pin` (Task 1)

- [ ] **Step 1: Write the failing test**

Append to `tests/test_auth_hardening.py`:

```python
def test_add_sales_users_no_plaintext_pin_and_uses_verify():
    root = Path(__file__).resolve().parents[1]
    src = (root / "add_sales_users.py").read_text(encoding="utf-8")
    # No f-string that prints the raw PIN value
    assert "PIN={u['pin']}" not in src
    assert "PIN: {u['pin']}" not in src
    # Verification must use verify_pin (hash_pin is now salted → == compare is wrong)
    assert "verify_pin(" in src
    assert 'rec["pin_hash"] == hash_pin(' not in src
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest "tests/test_auth_hardening.py::test_add_sales_users_no_plaintext_pin_and_uses_verify" -v`
Expected: FAIL — current file prints PINs and uses `==` compare.

- [ ] **Step 3: Implement**

In `add_sales_users.py`:

Change the import (`:5`):

```python
from role_engine import init_roles, hash_pin, verify_pin
```

Change the UPDATED print (`:36`):

```python
        print(f"  🔄 UPDATED  {u['username']:8s}  (id={existing['id']}, role=sales)")
```

Change the CREATED print (`:39`):

```python
        print(f"  ➕ CREATED  {u['username']:8s}  (id={new_id}, role=sales)")
```

Change the verification compare (`:54`):

```python
    pin_ok  = verify_pin(u["pin"], rec["pin_hash"] or "")[0]
```

Change the credentials footer (`:78-81`) — stop printing PINs:

```python
print("Users configured (PINs set as specified — not displayed):")
for u in USERS:
    print(f"  • {u['username']:8s}  (Sales role)")
```

- [ ] **Step 4: Verify syntax + test passes**

Run: `python -c "import ast, pathlib; ast.parse(pathlib.Path('add_sales_users.py').read_text(encoding='utf-8'))" && python -m pytest "tests/test_auth_hardening.py::test_add_sales_users_no_plaintext_pin_and_uses_verify" -v`
Expected: no parse error; test PASS. (Do NOT run `add_sales_users.py` itself — it mutates the real `bitumen_dashboard.db`.)

- [ ] **Step 5: Commit**

```bash
git add add_sales_users.py tests/test_auth_hardening.py
git commit -m "fix(auth): stop printing plaintext PINs; use verify_pin in add_sales_users"
```

---

### Task 8: Full-suite regression check

**Files:** none (verification only)

- [ ] **Step 1: Run the new suite**

Run: `python -m pytest tests/test_auth_hardening.py -v`
Expected: PASS (all ~19 tests).

- [ ] **Step 2: Run the existing auth-adjacent tests**

Run: `python -m pytest tests/ -k "auth or login or rbac or role" -v`
Expected: PASS (or pre-existing skips). Investigate any new failure — most likely a test that assumed unsalted `hash_pin`; update it to `verify_pin`.

- [ ] **Step 3: Sanity-check the two throttle callers compile**

Run: `python -c "import ast, pathlib; ast.parse(pathlib.Path('role_engine.py').read_text(encoding='utf-8'))"`
Expected: no error. (Confirms the `_is_rate_limited` tuple-return refactor didn't leave a broken caller.)

- [ ] **Step 4: Final commit (if anything was touched in steps above)**

```bash
git add -A
git commit -m "test(auth): round-2 regression fixes" || echo "nothing to commit"
```

---

## Self-Review

**Spec coverage:**
- PBKDF2 hashing → Task 1 ✅
- Lazy migration on login → Task 2 ✅
- Escalating throttle → Task 3 ✅
- Referer meta (in-app) → Task 5 ✅; nginx Referrer-Policy + access-log → Task 6 ✅
- Shorter/decoupled token TTL → Task 4 ✅
- `add_sales_users.py` plaintext-PIN cleanup → Task 7 ✅
- Tests for all of the above → Tasks 1–7 + regression Task 8 ✅
- Residual risk (token in history) → documented in spec; no task (deferred by decision) ✅

**Placeholder scan:** No TBD/TODO; every code step shows full code. ✅

**Type consistency:** `verify_pin -> (bool, bool)` used identically in Tasks 1/2/7. `_is_rate_limited -> (bool, int)` defined in Task 3 and both callers (`login`, `render_login_form`) updated in the same task. `_evaluate_throttle(timestamps, now) -> (bool, int)` consistent. `_get_token_ttl_minutes -> int` consistent. ✅
