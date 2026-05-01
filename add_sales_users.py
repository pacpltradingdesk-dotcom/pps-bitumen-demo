"""One-shot: add 3 sales users (janki, renuka, riya) and verify login works."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from role_engine import init_roles, hash_pin
from database import get_user_by_username, insert_user, update_user, get_all_users

init_roles()

USERS = [
    {"username": "janki",  "display_name": "Janki",  "pin": "1111"},
    {"username": "renuka", "display_name": "Renuka", "pin": "2222"},
    {"username": "riya",   "display_name": "Riya",   "pin": "3333"},
]

print("=" * 70)
print("ADD SALES USERS — pps-demo-live")
print("=" * 70)

for u in USERS:
    existing = get_user_by_username(u["username"])
    payload = {
        "username":     u["username"],
        "display_name": u["display_name"],
        "role":         "sales",
        "pin_hash":     hash_pin(u["pin"]),
        "is_active":    1,
    }
    if existing:
        update_user(existing["id"], {
            "display_name": payload["display_name"],
            "role":         "sales",
            "pin_hash":     payload["pin_hash"],
            "is_active":    1,
        })
        print(f"  🔄 UPDATED  {u['username']:8s}  (id={existing['id']}, role=sales, PIN={u['pin']})")
    else:
        new_id = insert_user(payload)
        print(f"  ➕ CREATED  {u['username']:8s}  (id={new_id}, role=sales, PIN={u['pin']})")

# ── Verify: read back + simulate login (PIN hash match) ──
print()
print("─" * 70)
print("VERIFICATION — read-back + PIN match")
print("─" * 70)

all_ok = True
for u in USERS:
    rec = get_user_by_username(u["username"])
    if not rec:
        print(f"  ❌ {u['username']}: not found after insert")
        all_ok = False
        continue
    pin_ok  = rec["pin_hash"] == hash_pin(u["pin"])
    role_ok = rec["role"] == "sales"
    active  = bool(rec.get("is_active"))
    status = "✅" if (pin_ok and role_ok and active) else "❌"
    print(f"  {status} {u['username']:8s}  id={rec['id']:<3}  role={rec['role']:9s}  active={active}  pin_match={pin_ok}")
    if not (pin_ok and role_ok and active):
        all_ok = False

# ── Full user table snapshot ──
print()
print("─" * 70)
print("ALL USERS (current users table)")
print("─" * 70)
users = get_all_users()
print(f"  {'ID':<4} {'USERNAME':<12} {'DISPLAY':<14} {'ROLE':<10} {'ACTIVE':<7} {'CREATED'}")
for u in users:
    print(f"  {u['id']:<4} {u['username']:<12} {(u.get('display_name') or ''):<14} "
          f"{u.get('role', ''):<10} {bool(u.get('is_active'))!s:<7} {u.get('created_at', '')}")

print()
print("=" * 70)
print(f"RESULT: {'✅ ALL 3 SALES USERS WORKING' if all_ok else '❌ SOMETHING FAILED'}")
print("=" * 70)
print()
print("Login credentials:")
for u in USERS:
    print(f"  • {u['username']:8s}  PIN: {u['pin']}  (Sales role)")
print()
print("PIN change karne ke liye: ⚙️ Settings → 👥 User Management page")
