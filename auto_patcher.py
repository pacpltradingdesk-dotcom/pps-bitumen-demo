"""
Auto-patcher — India localization audit & fix.
Run explicitly: python auto_patcher.py
Never runs on import.
"""
import os
import re
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def run_patcher():
    """Run the auto-patcher. Only call explicitly — never on import."""
    py_files = []
    for root, dirs, files in os.walk(BASE_DIR):
        if "node_modules" in root or ".git" in root or "venv" in root:
            continue
        for f in files:
            if f.endswith(".py") and f != "india_localization.py" and f != "auto_patcher.py":
                py_files.append(os.path.join(root, f))

    audit_report = {
        "us_currency_issues": [],
        "us_date_issues": [],
        "comma_grouping_issues": []
    }

    import_statement = (
        "try:\n"
        "    from india_localization import format_inr, format_inr_short, format_date, "
        "format_datetime_ist, get_financial_year, get_fy_quarter\n"
        "except ImportError:\n"
        "    import sys\n"
        "    import os\n"
        "    sys.path.append(os.path.dirname(os.path.dirname(__file__)))\n"
        "    try:\n"
        "        from india_localization import format_inr, format_inr_short, format_date, "
        "format_datetime_ist, get_financial_year, get_fy_quarter\n"
        "    except:\n"
        "        pass\n"
    )

    for path in py_files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        filename = os.path.basename(path)

        # Detect US currency
        if re.search(r'\$\d+', content) or (re.search(r'\$\{', content) and 'javascript' not in content.lower()):
            audit_report["us_currency_issues"].append(filename)

        # Detect bad dates
        if re.search(r'%Y-%m-%d', content):
            audit_report["us_date_issues"].append(filename)

        # Detect bad commas
        if re.search(r'\{[^\}]*:,[.\d]*f\}', content):
            audit_report["comma_grouping_issues"].append(filename)

        # Fixes
        content = content.replace('%Y-%m-%d', '%d-%m-%Y')
        content = re.sub(r'₹\s*\{([^:]+):,\.0f\}', r'{format_inr(\1)}', content)
        content = re.sub(r'₹\s*\{([^:]+):,\.2f\}', r'{format_inr(\1)}', content)
        content = re.sub(r'₹\s*\{([^:]+):,\}', r'{format_inr(\1)}', content)
        content = re.sub(r'\$(\d+)', r'₹ \\1', content)
        content = content.replace("₹{", "{")

        if content != original_content:
            if 'format_inr(' in content and 'from india_localization' not in content:
                content = import_statement + content
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Patched: {filename}")

    with open(os.path.join(BASE_DIR, "audit_export.json"), "w") as f:
        json.dump(audit_report, f, indent=4)

    print("Audit and Auto-Patch Complete!")


if __name__ == "__main__":
    run_patcher()
