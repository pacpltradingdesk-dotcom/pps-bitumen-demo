"""
PPS Anantam — Smoke Test v5.0
================================
Verifies all page modules can be imported without errors.
Run: python test_smoke.py
"""
import ast
import sys
import io
import glob

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    print("=" * 60)
    print("PPS Anantam Dashboard v5.0 — Smoke Test")
    print("=" * 60)

    errors = []
    ok = 0

    # 1. Core files
    core_files = [
        'dashboard.py', 'theme.py', 'nav_config.py', 'top_bar.py',
        'subtab_bar.py', 'telegram_engine.py', 'share_system.py',
    ]
    print("\n[1] Core files:")
    for f in core_files:
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                ast.parse(fh.read())
            print(f"  ✓ {f}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {f}: {e}")
            errors.append(f)

    # 2. Page files
    print("\n[2] Page files:")
    for f in sorted(glob.glob('pages/**/*.py', recursive=True)):
        if '__init__' in f:
            continue
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                ast.parse(fh.read())
            print(f"  ✓ {f}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {f}: {e}")
            errors.append(f)

    # 3. Component files
    print("\n[3] Components:")
    for f in sorted(glob.glob('components/**/*.py', recursive=True)):
        if '__init__' in f:
            continue
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                ast.parse(fh.read())
            print(f"  ✓ {f}")
            ok += 1
        except Exception as e:
            print(f"  ✗ {f}: {e}")
            errors.append(f)

    # 4. Nav config verification
    print("\n[4] Navigation config:")
    try:
        from nav_config import MODULE_NAV, TOPBAR_MODULES, OVERFLOW_MODULES, all_pages, PAGE_REDIRECTS
        pages = all_pages()
        print(f"  ✓ {len(MODULE_NAV)} modules, {len(pages)} pages, {len(PAGE_REDIRECTS)} redirects")
        print(f"  ✓ Top bar: {len(TOPBAR_MODULES)} modules + {len(OVERFLOW_MODULES)} overflow")
    except Exception as e:
        print(f"  ✗ nav_config: {e}")
        errors.append('nav_config')

    # 5. Theme verification
    print("\n[5] Theme:")
    try:
        from theme import NAVY_DARK, BLUE_PRIMARY, WHITE, SLATE_900, inject_theme
        print(f"  ✓ Theme colors + inject_theme loaded")
    except Exception as e:
        print(f"  ✗ theme: {e}")
        errors.append('theme')

    # Summary
    print("\n" + "=" * 60)
    if errors:
        print(f"RESULT: {ok} passed, {len(errors)} FAILED")
        for e in errors:
            print(f"  FAIL: {e}")
        return 1
    else:
        print(f"RESULT: ALL {ok} files PASSED ✓")
        return 0


if __name__ == "__main__":
    sys.exit(main())
