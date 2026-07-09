"""One-shot feature audit — verify every nav page has a working dispatch + import + render."""
import importlib, sys, traceback, re, ast, io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from nav_config import MODULE_NAV, PAGE_REDIRECTS, all_pages

# ── 1. Parse PAGE_DISPATCH from dashboard.py (without importing it — avoids streamlit) ──
dash_src = (ROOT / "dashboard.py").read_text(encoding="utf-8")
dispatch_match = re.search(r"PAGE_DISPATCH\s*=\s*\{(.*?)^\}", dash_src, re.DOTALL | re.MULTILINE)
if not dispatch_match:
    print("FATAL: PAGE_DISPATCH not found"); sys.exit(1)
dispatch_block = dispatch_match.group(1)

# Extract page-key → import path mappings
entries = re.findall(
    r'"([^"]+)":\s*(?:lambda:\s*_safe_render\(\s*lambda:\s*)?__import__\("([^"]+)",\s*fromlist=\["([^"]+)"\]\)\.([a-zA-Z_]+)\(\)',
    dispatch_block,
)
# Also: entries that point to a `_page_xxx` local helper
helper_entries = re.findall(r'"([^"]+)":\s*(_page_[a-zA-Z_]+)\s*,', dispatch_block)
# Resolve helper functions → their inner imports
helpers = {}
tree = ast.parse(dash_src)
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name.startswith("_page_"):
        # find first __import__ inside
        src = ast.get_source_segment(dash_src, node) or ""
        m = re.search(r'__import__\("([^"]+)",\s*fromlist=\["([^"]+)"\]\)\.([a-zA-Z_]+)\(\)', src)
        if m:
            helpers[node.name] = (m.group(1), m.group(2), m.group(3))
        elif "_safe_render" not in src and "render" in src:
            helpers[node.name] = ("__inline__", "render", "render")

dispatch_map = {}
for page, mod, _, fn in entries:
    dispatch_map[page] = (mod, fn)
for page, helper in helper_entries:
    if helper in helpers:
        mod, _, fn = helpers[helper]
        dispatch_map[page] = (mod, fn)
    else:
        dispatch_map[page] = ("__helper__", helper)

# ── 2. Coverage: every nav page must be dispatchable ──
nav_pages = list(dict.fromkeys(all_pages()))  # dedupe, preserve order
missing = []
for p in nav_pages:
    real = PAGE_REDIRECTS.get(p, p)
    if real not in dispatch_map and p not in dispatch_map:
        missing.append(p)

# ── 3. Import + render symbol check for each dispatch entry ──
results = []  # (page, status, detail)
for page, (mod, fn) in dispatch_map.items():
    if mod in ("__helper__", "__inline__"):
        results.append((page, "HELPER", f"{fn}"))
        continue
    try:
        m = importlib.import_module(mod)
        if not hasattr(m, fn):
            results.append((page, "FAIL", f"{mod} missing {fn}()"))
        else:
            results.append((page, "OK", f"{mod}.{fn}"))
    except Exception as e:
        tb = traceback.format_exception_only(type(e), e)[-1].strip()
        results.append((page, "IMPORT_ERR", f"{mod}: {tb}"))

# ── 4. Print per-module summary ──
page_to_module = {}
for mod_key, mod in MODULE_NAV.items():
    for tab in mod["tabs"]:
        page_to_module[tab["page"]] = mod_key

ok_count = sum(1 for _, s, _ in results if s == "OK")
helper_count = sum(1 for _, s, _ in results if s == "HELPER")
fail = [(p, s, d) for p, s, d in results if s in ("FAIL", "IMPORT_ERR")]

print("=" * 80)
print(f"FEATURE AUDIT — pps-demo-live")
print("=" * 80)
print(f"Nav pages         : {len(nav_pages)} (across {len(MODULE_NAV)} sections)")
print(f"Dispatch entries  : {len(dispatch_map)}")
print(f"Direct imports OK : {ok_count}")
print(f"Helper-routed     : {helper_count}")
print(f"BROKEN            : {len(fail)}")
print(f"Missing dispatch  : {len(missing)}")
print()

# Per-module breakdown
print("─" * 80)
print("PER-MODULE STATUS")
print("─" * 80)
status_by_page = {p: (s, d) for p, s, d in results}
for mod_key, mod in MODULE_NAV.items():
    print(f"\n{mod_key}  ({len(mod['tabs'])} features)")
    for tab in mod["tabs"]:
        p = tab["page"]
        real = PAGE_REDIRECTS.get(p, p)
        if p in status_by_page:
            s, d = status_by_page[p]
        elif real in status_by_page:
            s, d = status_by_page[real]
        else:
            s, d = "NO_DISPATCH", "—"
        icon = {"OK": "✅", "HELPER": "🔵", "FAIL": "❌", "IMPORT_ERR": "💥", "NO_DISPATCH": "⚠️"}.get(s, "?")
        print(f"  {icon} {s:12s}  {tab['label']:30s}  → {d}")

# Failures detail
if fail:
    print("\n" + "=" * 80)
    print("BROKEN FEATURES (drill-down)")
    print("=" * 80)
    for p, s, d in fail:
        print(f"\n[{s}]  {p}")
        print(f"        {d}")

if missing:
    print("\n" + "=" * 80)
    print("PAGES WITH NO DISPATCH (will show 'page not found')")
    print("=" * 80)
    for p in missing:
        print(f"  ⚠️  {p}  (in {page_to_module.get(p, '?')})")

print()
print("=" * 80)
print(f"FINAL: {ok_count + helper_count}/{len(dispatch_map)} dispatch entries healthy, {len(fail)} broken")
print("=" * 80)
