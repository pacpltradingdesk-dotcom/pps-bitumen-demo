"""
Walkthrough test for the two new features:
  A) News "share everywhere" — per-article + digest, message + deep links
  B) Global search / command palette — query -> results -> navigation, RBAC-filtered

Run: PYTHONIOENCODING=utf-8 .venv\\Scripts\\python.exe test_new_features.py
"""
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from streamlit.testing.v1 import AppTest
from nav_config import get_module_for_page

results = []
def check(name, ok, detail=""):
    results.append(ok)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail}" if detail else ""))

def ss(at, key, default=None):
    return at.session_state[key] if key in at.session_state else default

def seed(at, role="director"):
    at.session_state["_auth_user"] = {"username": role, "role": role}
    at.session_state["_auth_role"] = role
    at.session_state["_auth_username"] = role
    at.session_state["_auth_last_activity"] = time.time()

def open_page(page, role="director", **extra):
    at = AppTest.from_file("dashboard.py", default_timeout=90)
    seed(at, role)
    at.session_state["selected_page"] = page
    at.session_state["_active_module"] = get_module_for_page(page)
    for k, v in extra.items():
        at.session_state[k] = v
    at.run()
    return at

def crashed(at):
    return bool(at.exception) or [e.value for e in at.error if "failed to load" in e.value.lower()]


# ════════════════════════════════════════════════════════════════════════
print("=" * 72)
print("A) NEWS SHARE EVERYWHERE")
print("=" * 72)

import news_share as nshare
import news_engine as ne

arts = ne.get_articles(region="Domestic", max_age_hours=99999)

# A1. single-article message + all channel links valid
if arts:
    msg = nshare.build_article_message(arts[0])
    links = nshare._links(msg, arts[0].get("source_url", ""), "PPS News")
    have = {k for k, (_l, url) in links.items() if url.startswith("http") or url.startswith("mailto")}
    check("article message built + 5 channels (WA/TG/Email/X/LinkedIn)",
          bool(msg) and have == {"WhatsApp", "Telegram", "Email", "Twitter", "LinkedIn"},
          f"channels={sorted(have)}")
    # deep-link sanity
    wa = links["WhatsApp"][1]
    check("WhatsApp deep link is wa.me with encoded text",
          wa.startswith("https://wa.me/?text=") and "%" in wa)
    check("Email link is mailto with subject+body",
          links["Email"][1].startswith("mailto:?subject=") and "body=" in links["Email"][1])

# A2. digest (share ALL) bundles many articles
digest = nshare.build_digest_message(arts, "Domestic News Digest", limit=5)
nlines = sum(1 for ln in digest.splitlines() if ln.strip()[:1].isdigit())
check("digest bundles multiple stories into one message", nlines >= min(5, len(arts)),
      f"{nlines} numbered stories")

# A3. empty digest is graceful
empty = nshare.build_digest_message([], "Empty")
check("empty digest is graceful (no crash)", "No news to share" in empty)

# A4. News page renders clean (both roles)
for role in ("director", "sales"):
    at = open_page("📰 News Intelligence", role)
    check(f"News Intelligence renders clean ({role})", not crashed(at))

# A5. Command Center (has the digest share) renders clean
at = open_page("🎯 Command Center", "sales")
check("Command Center renders clean (with Share Top News)", not crashed(at))


# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
print("B) GLOBAL SEARCH / COMMAND PALETTE")
print("=" * 72)

def search_results(at, slot="main"):
    return [b for b in at.button if b.key and b.key.startswith(f"_gsres_{slot}_")]

# B1. search 'contacts' as director -> Contacts Directory appears
at = open_page("🏠 Home", "director", _gsearch_main="contacts")
res = search_results(at)
labels = [b.label for b in res]
check("search 'contacts' returns Contacts Directory", any("Contacts" in l for l in labels),
      f"{len(res)} results: {labels[:4]}")

# B2. search 'news' -> News Intelligence appears
at = open_page("🏠 Home", "director", _gsearch_main="news")
labels = [b.label for b in search_results(at)]
check("search 'news' returns News Intelligence", any("News" in l for l in labels), f"{labels[:4]}")

# B3. clicking a search result navigates to that page
at = open_page("🏠 Home", "director", _gsearch_main="tender")
res = search_results(at)
if res:
    res[0].click().run()
    dest = ss(at, "selected_page")
    check("clicking a search result navigates there", dest == "🏗️ NHAI Tenders", f"landed on {dest}")
else:
    check("clicking a search result navigates there", False, "no results to click")

# B4. RBAC — sales searching 'user management' must NOT see the admin page
at = open_page("🏠 Home", "sales", _gsearch_main="user management")
labels = [b.label for b in search_results(at)]
check("RBAC: sales search hides User Management", not any("User Management" in l for l in labels),
      f"results={labels}")

# B5. nonsense query -> no results, no crash
at = open_page("🏠 Home", "director", _gsearch_main="zxqwlkjasdf")
check("nonsense query: no crash, no results", not crashed(at) and not search_results(at))


# ════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 72)
passed = sum(results)
print(f"NEW-FEATURE WALKTHROUGH: {passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)
