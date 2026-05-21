"""
VISIBLE Browser Test - PPS Anantam Dashboard
Opens real Chromium window - watch every page load live.
Run: python browser_test_visible.py
"""
import os, sys, time, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8501"
SS_DIR   = "browser_test_screenshots"
os.makedirs(SS_DIR, exist_ok=True)

USERS = [
    {"user": "admin",  "pwd": "0000", "role": "admin"},
    {"user": "janki",  "pwd": "1111", "role": "sales"},
    {"user": "renuka", "pwd": "2222", "role": "sales"},
    {"user": "riya",   "pwd": "3333", "role": "sales"},
]

# Per-module starred pages to test (matching the sidebar label text)
MODULE_STARRED = {
    "Price & Info": [
        "Command Center", "Live Market", "Market Signals", "News",
        "Telegram Analyzer", "Price Prediction", "Director Briefing",
    ],
    "Sales": [
        "Pricing Calculator", "CRM & Tasks", "Opportunities", "Negotiation", "Daily Log",
    ],
    "Logistics": [],          # no starred pages; just test module tab load
    "Purchasers": ["Purchase Orders"],
    "Sharing": [],            # no starred pages; just test module tab load
    "Settings": ["Settings", "User Management"],
}

MODULES_ADMIN = ["Price & Info", "Sales", "Logistics", "Purchasers", "Sharing", "Settings"]
MODULES_SALES = ["Price & Info", "Sales", "Logistics", "Purchasers", "Sharing"]

results = []

def L(msg):
    print(msg, flush=True)
    results.append(msg)

def ss(page, name):
    p = os.path.join(SS_DIR, f"VIS_{name}.png")
    try:
        page.screenshot(path=p)
    except Exception:
        pass
    return p

def pause(secs=1.5):
    time.sleep(secs)

def stl_wait(page, timeout=15000):
    try:
        page.wait_for_selector('[data-testid="stStatusWidget"]', timeout=3000)
        page.wait_for_selector('[data-testid="stStatusWidget"]', state='hidden', timeout=timeout)
    except Exception:
        pass
    pause(0.8)

# ── HEALTH CHECK ───────────────────────────────────────────────

def page_is_alive(page):
    """Returns True if the Playwright page context is still responsive."""
    try:
        page.evaluate("1+1")
        return True
    except Exception:
        return False

def ensure_connected(page, user, pwd):
    """If page context died, reload and re-login. Returns True if OK."""
    if not page_is_alive(page):
        L(f"  WARN - page context dead, attempting recovery...")
        try:
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=25000)
            stl_wait(page, 15000)
            pause(2)
        except Exception:
            return False

    # Check if session expired (redirected to login)
    try:
        if page.locator('input[type="password"]').is_visible(timeout=2000):
            L(f"  WARN - session expired, re-logging in...")
            ok = do_login(page, user, pwd)
            if ok:
                dismiss_tour(page)
                return True
            return False
    except Exception:
        pass

    return True

# ── TOUR DISMISS ───────────────────────────────────────────────

def kill_tour(page):
    """Aggressively kill the tour regardless of tooltip visibility.
    Uses Playwright force=True click on the hidden PPS-TOUR-SKIP-CTRL button.
    Call this before any navigation to prevent tooltip overlay from blocking clicks."""
    # Primary: Playwright force=True click — handles off-screen/hidden elements
    try:
        ctrl = page.locator('button:has-text("PPS-TOUR-SKIP-CTRL")')
        if ctrl.count() > 0:
            ctrl.first.click(force=True, timeout=3000)
            stl_wait(page, 6000)
            pause(0.8)
            return True
    except Exception:
        pass
    # Fallback: JS dispatchEvent (handles React synthetic events)
    try:
        clicked = page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button'));
                const ctrl = btns.find(b =>
                    (b.innerText || b.textContent || '').trim().includes('PPS-TOUR-SKIP-CTRL')
                );
                if (ctrl) {
                    ctrl.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true}));
                    return true;
                }
                return false;
            }
        """)
        if clicked:
            stl_wait(page, 4000)
            pause(0.8)
            return True
    except Exception:
        pass
    return False


def dismiss_tour(page):
    """Dismiss the tour popup only if the visual tooltip is visible.
    Returns True if tour was detected and dismissed."""

    # Quick check: is visual Skip button visible (in parent DOM, rendered by JS)?
    skip_visible = False
    try:
        skip_visible = page.locator('button:has-text("Skip")').is_visible(timeout=1500)
    except Exception:
        pass

    # Also check if the tour control buttons exist in the sidebar
    # (they're always present when _show_tutorial=True, even without the tooltip)
    tour_active = False
    try:
        tour_active = page.locator('button:has-text("PPS-TOUR-SKIP-CTRL")').count() > 0
    except Exception:
        pass

    if not skip_visible and not tour_active:
        return False

    L("  INFO - tour active, dismissing...")
    killed = kill_tour(page)
    if killed:
        pause(0.5)
        return True

    # If kill failed, try visual Skip button
    if skip_visible:
        try:
            page.locator('button:has-text("Skip")').first.click()
            stl_wait(page, 4000)
            pause(0.8)
            return True
        except Exception:
            pass

    # Last resort: Escape
    try:
        page.keyboard.press("Escape")
        pause(0.6)
    except Exception:
        pass

    return False

# ── LOGIN ─────────────────────────────────────────────────────

def do_login(page, user, pwd):
    page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_selector('input', timeout=20000)
    pause(1.5)

    u = page.locator('input[type="text"], input:not([type="password"])').first
    u.clear()
    u.fill(user)
    pause(0.4)

    p = page.locator('input[type="password"]').first
    p.clear()
    p.fill(pwd)
    pause(0.4)

    p.press("Enter")
    pause(0.5)
    try:
        page.locator('button:has-text("Sign In")').first.click(timeout=2000)
    except Exception:
        pass

    try:
        page.wait_for_selector(
            '[data-testid="stSidebar"], button:has-text("Price & Info")',
            timeout=25000
        )
        pause(1.5)
        return True
    except Exception:
        return False

# ── NAVIGATION ────────────────────────────────────────────────

def _module_btn(page, name):
    """Locate a module tab button by accessible name (handles nested Streamlit spans)."""
    return page.get_by_role("button", name=name, exact=True)


def escape_fast_path(page):
    """Command Center page uses st.stop() BEFORE render_top_bar(), so module tabs
    are absent from the DOM. Click any non-CC sidebar page to trigger a full render."""
    # Use get_by_role (ARIA accessible name) — more reliable than :text-is() for
    # Streamlit buttons whose text is nested inside inner spans/divs
    try:
        cnt = _module_btn(page, "Price & Info").count()
        if cnt > 0:
            return True  # top bar already rendered
    except Exception:
        pass
    # Navigate away from CC to trigger full render with top bar
    for label in ["Live Market", "Market Signals", "News"]:
        try:
            btn = page.locator(f'[data-testid="stSidebar"] button:has-text("{label}")').first
            if btn.count() > 0:
                btn.click(force=True, timeout=4000)
                stl_wait(page, 8000)
                pause(1.0)
                if _module_btn(page, "Price & Info").count() > 0:
                    return True
        except Exception:
            pass
    return False



def _do_relogin(page, user, pwd):
    """Login without navigating away (page must already show login form).
    Returns True on success."""
    try:
        page.wait_for_selector('input', timeout=10000)
        pause(1.0)
        u = page.locator('input[type="text"], input:not([type="password"])').first
        u.clear()
        u.fill(user)
        pause(0.3)
        p = page.locator('input[type="password"]').first
        p.clear()
        p.fill(pwd)
        pause(0.3)
        p.press("Enter")
        pause(0.5)
    except Exception:
        return False
    try:
        page.locator('button:has-text("Sign In")').first.click(timeout=2000)
    except Exception:
        pass
    try:
        page.wait_for_selector('[data-testid="stSidebar"]', timeout=25000)
        pause(1.5)
        return True
    except Exception:
        return False


def click_module(page, name, user, pwd):
    """Navigate to a module using ?_m=<label> query param.

    dashboard.py reads this param after auth and auto-navigates.
    Requires a page reload (fresh Streamlit session), so we re-login.
    Sidebar buttons work in Playwright; stMain top-bar tabs do not trigger reruns.
    """
    if name == "Price & Info":
        kill_tour(page)
        escape_fast_path(page)
        return True

    url = f"{BASE_URL}/?_m={name}"
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        L(f"  ERROR - goto {url} failed: {str(e)[:80]}")
        return False

    stl_wait(page, 15000)
    pause(1.5)

    # Re-login (page reload resets Streamlit session)
    try:
        if page.locator('input[type="password"]').is_visible(timeout=3000):
            L(f"  INFO - re-login for module '{name}'")
            ok = _do_relogin(page, user, pwd)
            if not ok:
                L(f"  ERROR - re-login failed for module '{name}'")
                return False
            dismiss_tour(page)
            stl_wait(page, 15000)
            pause(2.0)
    except Exception:
        pass

    kill_tour(page)
    stl_wait(page, 10000)
    pause(1.0)
    L(f"  INFO - module '{name}' loaded")
    return True

def click_sidebar(page, label):
    """Click a sidebar page button. Returns True if clicked successfully."""
    # Use click() with timeout — Playwright waits for element to be visible+actionable
    for text in [f"{label} ✦", label, f"✦ {label}"]:
        try:
            btn = page.locator(f'[data-testid="stSidebar"] button:has-text("{text}")').first
            btn.click(timeout=5000)   # auto-waits for visible + actionable
            stl_wait(page, 12000)
            pause(1)
            return True
        except Exception:
            pass
    return False

def get_errors(page):
    errs = []
    try:
        for el in page.locator('[data-testid="stAlert"]').all():
            t = el.inner_text()
            if any(w in t.lower() for w in ["error","traceback","exception","keyerror","attributeerror"]):
                errs.append(t[:120])
    except Exception:
        pass
    try:
        for el in page.locator('.stException').all():
            t = el.inner_text()[:120]
            if t.strip():
                errs.append(t)
    except Exception:
        pass
    return errs

def has_content(page):
    try:
        body = page.locator('[data-testid="stMain"]').inner_text(timeout=8000)
        return len(body.strip()) > 80
    except Exception:
        return False


def run_user(browser, info):
    user, pwd, role = info["user"], info["pwd"], info["role"]
    modules = MODULES_ADMIN if role == "admin" else MODULES_SALES

    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()

    L(f"\n{'='*65}")
    L(f"  TESTING USER: {user.upper()}  |  ROLE: {role}")
    L(f"{'='*65}")

    # ── LOGIN ────────────────────────────────────────────────
    L(f"\n[LOGIN] {user} / {pwd}")
    ok = do_login(page, user, pwd)
    if not ok:
        L(f"  FAIL - login did not load dashboard")
        ss(page, f"{user}_login_fail")
        ctx.close()
        return 0, 0, 0

    shot = ss(page, f"{user}_01_logged_in")
    L(f"  PASS - logged in  |  {shot}")
    pause(1)

    # Kill tour at login (tour starts on first render after login)
    # Must call kill_tour directly — tooltip may not be visible yet
    pause(2)  # let JS render the tour tooltip first
    killed = kill_tour(page)
    if killed:
        L(f"  INFO - tour killed at login")
        stl_wait(page)
        pause(1)
    elif dismiss_tour(page):
        L(f"  INFO - tour dismissed at login")
        stl_wait(page)
        pause(1)

    # ── RBAC CHECK ───────────────────────────────────────────
    L(f"\n[RBAC CHECK]")
    for mod in ["Price & Info","Sales","Logistics","Purchasers","Sharing","Settings"]:
        try:
            vis = page.locator(f'button:has-text("{mod}")').first.is_visible(timeout=1000)
        except Exception:
            vis = False
        if mod == "Settings":
            if role == "admin":
                status = "PASS - Settings visible (admin)" if vis else "WARN - Settings hidden (unexpected for admin)"
            else:
                status = "PASS - Settings hidden (sales)" if not vis else "FAIL - Settings visible (RBAC bypass!)"
        else:
            status = "PASS" if vis else "WARN - missing"
        L(f"  {mod}: {'VISIBLE' if vis else 'HIDDEN'} => {status}")
    pause(1)

    total = passed = failed = 0

    # ── MODULE + SIDEBAR WALK ─────────────────────────────────
    for mi, mod in enumerate(modules, 1):
        L(f"\n[MODULE {mi}/{len(modules)}] {mod}")
        starred = MODULE_STARRED.get(mod, [])

        # Kill tour BEFORE clicking module — tour JS overlays target buttons
        kill_tour(page)

        ok = click_module(page, mod, user, pwd)
        if not ok:
            L(f"  FAIL - could not click module tab '{mod}'")
            ss(page, f"{user}_{mi:02d}_mod_{mod.replace(' ','_').replace('&','n')}_FAIL")
            failed += 1; total += 1
            continue

        # Kill any tour overlay that triggers on module load
        if kill_tour(page):
            L(f"  INFO - tour killed after module load")
            pause(1.0)

        errs = get_errors(page)
        content = has_content(page)
        shot = ss(page, f"{user}_{mi:02d}_mod_{mod.replace(' ','_').replace('&','n')}")
        status = "PASS" if content and not errs else "WARN" if content else "FAIL"
        L(f"  {status} - module tab loaded  |  {shot}")
        if errs:
            for e in errs[:2]: L(f"  ERROR: {e[:100]}")
        total += 1
        if status == "PASS": passed += 1
        else: failed += 1
        pause(1)

        # DEBUG: dump all sidebar buttons so we can see what's there
        try:
            all_btns = page.locator('[data-testid="stSidebar"] button').all()
            btn_labels = []
            for b in all_btns[:25]:
                try:
                    txt = (b.inner_text(timeout=500) or "").strip()[:40]
                    if txt:
                        btn_labels.append(repr(txt))
                except Exception:
                    pass
            L(f"  DEBUG sidebar buttons ({len(btn_labels)}): {', '.join(btn_labels)}")
        except Exception as de:
            L(f"  DEBUG error: {de}")

        # Click each starred sidebar page for THIS module
        if not starred:
            L(f"  INFO - no starred pages for {mod}, skipping sidebar test")

        for pi, pg in enumerate(starred, 1):
            L(f"  [{mi}.{pi}] Sidebar page: {pg}")

            kill_tour(page)
            ok2 = click_sidebar(page, pg)

            # Tour may appear after sidebar navigation
            if dismiss_tour(page):
                L(f"    INFO - tour dismissed after sidebar nav")
                pause(0.8)

            errs2 = get_errors(page)
            content2 = has_content(page)
            shot2 = ss(page, f"{user}_{mi:02d}_pg{pi:02d}_{pg.replace(' ','_')}")

            if ok2 and content2 and not errs2:
                L(f"    PASS - rendered OK  |  {shot2}")
                passed += 1
            elif ok2 and content2:
                L(f"    WARN - loaded with errors  |  {shot2}")
                for e in errs2[:1]: L(f"    ERROR: {e[:90]}")
                failed += 1
            elif not ok2:
                L(f"    FAIL - button not found/clickable  |  {shot2}")
                failed += 1
            else:
                L(f"    FAIL - no content after click  |  {shot2}")
                failed += 1
            total += 1
            pause(1.2)

        # Pause between modules to let server breathe
        pause(2)

    # ── LOGOUT ───────────────────────────────────────────────
    L(f"\n[LOGOUT]")
    try:
        if not page_is_alive(page):
            L("  WARN - page context died before logout")
        else:
            # Prefer sidebar logout (sidebar clicks are reliable); fallback to any
            logout_btn = None
            try:
                sb_logout = page.locator(
                    '[data-testid="stSidebar"] button:has-text("Logout")'
                ).first
                if sb_logout.is_visible(timeout=2000):
                    logout_btn = sb_logout
            except Exception:
                pass
            if logout_btn is None:
                try:
                    any_logout = page.locator('button:has-text("Logout")').first
                    if any_logout.is_visible(timeout=2000):
                        logout_btn = any_logout
                except Exception:
                    pass

            if logout_btn:
                logout_btn.click()
                # Wait for login form: username text input is the clearest signal
                logged_out = False
                try:
                    page.wait_for_selector(
                        'input[type="text"], input[type="password"]',
                        timeout=15000
                    )
                    logged_out = True
                except Exception:
                    pass
                if not logged_out:
                    try:
                        body = page.content()
                        logged_out = any(s in body for s in
                                         ["Sign In", "Welcome Back", "Enter username", "login"])
                    except Exception:
                        pass
                shot = ss(page, f"{user}_logout")
                if logged_out:
                    L(f"  PASS - logout OK, login form visible  |  {shot}")
                else:
                    L(f"  WARN - logout clicked, login page unclear  |  {shot}")
            else:
                L("  WARN - Logout button not found")
    except Exception as ex:
        L(f"  WARN - {str(ex)[:60]}")

    L(f"\n  --- USER SUMMARY [{user.upper()}] ---")
    L(f"  Pages: {total}  |  PASS: {passed}  |  FAIL/WARN: {failed}")

    pause(2)
    ctx.close()
    return total, passed, failed


def wait_for_app(timeout=30):
    """Wait until the Streamlit app responds. Returns True if up."""
    import urllib.request as _ur
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            _ur.urlopen(BASE_URL, timeout=4)
            return True
        except Exception:
            time.sleep(2)
    return False


def main():
    L("=" * 65)
    L("  PPS ANANTAM — VISIBLE BROWSER TEST")
    L(f"  URL: {BASE_URL}")
    L("=" * 65)

    if not wait_for_app(20):
        L(f"  FAIL - App not reachable at {BASE_URL}")
        return
    L(f"  App is UP at {BASE_URL}")

    L("\n  >>> Browser window will open — watch live navigation <<<\n")
    pause(2)

    gt = gp = gf = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            slow_mo=400,
            args=["--start-maximized"]
        )

        for info in USERS:
            if not wait_for_app(30):
                L(f"\n  SKIP {info['user'].upper()} — app unreachable, cannot continue")
                continue
            try:
                t, ps, f = run_user(browser, info)
            except Exception as ex:
                L(f"\n  ERROR running {info['user']}: {str(ex)[:120]}")
                t, ps, f = 0, 0, 0
            gt += t; gp += ps; gf += f
            pause(3)

        L("\n  Test complete — closing browser in 5 seconds...")
        pause(5)
        browser.close()

    L("\n" + "=" * 65)
    L("  GRAND TOTAL")
    L(f"  Total pages : {gt}")
    L(f"  PASS        : {gp}")
    L(f"  FAIL/WARN   : {gf}")
    L(f"  Screenshots : {SS_DIR}/VIS_*.png")
    L("=" * 65)

    with open("browser_test_report_visible.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(results))
    L("  Report saved: browser_test_report_visible.txt")


if __name__ == "__main__":
    main()
