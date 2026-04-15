"""
Static analysis: scan every st.button() call across the codebase and
classify its handler block. Flags fake/no-op buttons that look clickable
but don't do anything useful.

Categories:
  ok      — handler calls a function or sets selected_page/_nav_goto
  toast   — handler only shows a toast/info/success (cosmetic only)
  pass    — handler is `pass` or `...` (genuinely empty)
  todo    — handler has a TODO/FIXME/XXX comment
  rerun   — handler is `st.rerun()` only (might be intentional but suspicious)
  unknown — couldn't classify, manual review needed
"""
import ast, sys, os
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {"__pycache__", ".worktrees", "node_modules", ".venv", ".git",
             "demo_pdfs", ".bak.archive", "presentation"}


# --- helpers ----------------------------------------------------------------

def is_button_call(node):
    """True if AST call is st.button() or st.form_submit_button()."""
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr not in ("button", "form_submit_button"):
        return False
    # Heuristic: receiver must reference 'st' or end in '.st'
    base = node.func.value
    if isinstance(base, ast.Name) and base.id == "st":
        return True
    if isinstance(base, ast.Attribute) and base.attr == "st":
        return True
    return False


def button_label(node):
    if node.args:
        a = node.args[0]
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            return a.value
        if isinstance(a, ast.JoinedStr):
            return "".join(
                v.value if isinstance(v, ast.Constant) else "{...}"
                for v in a.values
            )
    return "<dynamic>"


def find_buttons(tree):
    """Yield (lineno, label, parent_if_node) for each button call.

    parent_if_node is the surrounding `if st.button(...):` if found
    (so we can analyze the body), else None for naked calls.
    """
    # Walk all `if` nodes whose test is a button call
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            t = node.test
            if is_button_call(t):
                yield node.lineno, button_label(t), node
            # `if (st.button(...)):`
        # Naked button calls (not inside `if`) — also list, but they have no handler
        if isinstance(node, ast.Expr) and is_button_call(node.value):
            yield node.lineno, button_label(node.value), None


# --- classifier -------------------------------------------------------------

NAV_KEYS = ("_nav_goto", "selected_page", "_active_module",
            "_show_cmd_palette", "_show_tutorial")
ACTION_FUNCS = ("rerun", "stop", "switch_page", "navigate_to",
                "_go", "go_to", "switch_to_page")
TOAST_FUNCS = ("toast", "success", "info", "warning")


def classify(if_node):
    """Return (category, evidence_string)."""
    if if_node is None:
        return ("naked", "button rendered but no handler block")
    body = if_node.body
    if not body:
        return ("pass", "empty body")

    # Bag of all node text
    src = ast.unparse(if_node) if hasattr(ast, "unparse") else ""

    # 1. Nav patterns
    for n in ast.walk(if_node):
        if isinstance(n, ast.Subscript) and isinstance(n.value, ast.Attribute):
            if n.value.attr == "session_state":
                # st.session_state[...] = ...
                k = n.slice
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    if k.value in NAV_KEYS:
                        return ("ok-nav", f"sets st.session_state[{k.value!r}]")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            if n.func.attr in ACTION_FUNCS:
                return ("ok-call", f"calls {n.func.attr}()")
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id in ACTION_FUNCS:
                return ("ok-call", f"calls {n.func.id}()")

    # 2. Pure pass / ellipsis
    if all(isinstance(s, ast.Pass) or
           (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)
            and s.value.value is Ellipsis)
           for s in body):
        return ("pass", "body is pass / ...")

    # 3. TODO / FIXME / XXX comment as only content
    if "TODO" in src.upper() or "FIXME" in src.upper() or "XXX" in src.upper():
        return ("todo", "handler has TODO/FIXME marker")

    # 4. Toast/info only — cosmetic feedback, no real action
    UI_ONLY_ATTRS = TOAST_FUNCS + (
        "button", "form_submit_button", "markdown", "caption",
        "write", "code", "json", "dataframe", "table", "metric",
        "columns", "container", "expander", "tabs", "spinner",
        "empty", "divider", "header", "subheader", "error", "exception",
    )
    has_toast = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr in TOAST_FUNCS
        for n in ast.walk(if_node)
    )
    # "Real action" = any Call that is NOT a UI-cosmetic-only call.
    # Includes both attribute calls (engine.foo()) AND name calls (foo()).
    has_other_call = False
    for n in ast.walk(if_node):
        if not isinstance(n, ast.Call):
            continue
        if isinstance(n.func, ast.Attribute):
            if n.func.attr not in UI_ONLY_ATTRS:
                has_other_call = True
                break
        elif isinstance(n.func, ast.Name):
            # Plain function call like _save_log_entry(...) or do_thing()
            if n.func.id not in ("print", "len", "str", "int", "float",
                                 "bool", "dict", "list", "tuple", "set",
                                 "any", "all", "range"):
                has_other_call = True
                break
    has_assign = any(isinstance(n, (ast.Assign, ast.AugAssign))
                     for n in ast.walk(if_node))

    if has_toast and not has_other_call and not has_assign:
        return ("toast", "only shows toast/info — no real action")

    # 5. Other meaningful handler — assume OK
    if has_other_call or has_assign:
        return ("ok-other", "calls funcs / mutates state")

    return ("unknown", "manual review needed")


# --- runner -----------------------------------------------------------------

def main():
    results = defaultdict(list)
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        parts = set(rel.parts)
        if parts & SKIP_DIRS:
            continue
        if rel.name in ("button_audit.py",):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for lineno, label, if_node in find_buttons(tree):
            cat, evidence = classify(if_node)
            results[cat].append((str(rel).replace("\\", "/"), lineno,
                                 label[:60], evidence))

    print("=" * 78)
    print(f"BUTTON AUDIT — {ROOT}")
    print("=" * 78)
    total = sum(len(v) for v in results.values())
    print(f"Total buttons scanned: {total}\n")
    order = ["pass", "todo", "naked", "toast", "rerun", "unknown",
             "ok-nav", "ok-call", "ok-other"]
    for cat in order:
        items = results.get(cat, [])
        if not items:
            continue
        marker = "❌" if cat in ("pass", "todo", "naked") else \
                 "⚠️" if cat in ("toast", "unknown") else "✅"
        print(f"\n{marker} [{cat}] — {len(items)} buttons")
        if cat in ("ok-nav", "ok-call", "ok-other"):
            # Just count, don't list
            continue
        for path, line, label, ev in items:
            print(f"  {path}:{line:5d}  {label!r}  ← {ev}")


if __name__ == "__main__":
    main()
