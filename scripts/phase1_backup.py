"""One-shot safety backup for Phase 1 migration.
Run before Task 1. Idempotent: second run overwrites with latest state."""
from __future__ import annotations
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / ".bak.archive"


def main() -> int:
    ARCHIVE.mkdir(exist_ok=True)
    targets = [
        "bitumen_dashboard.db",
        "tbl_contacts.json",
        "sales_parties.json",
        "purchase_parties.json",
    ]
    copied = 0
    for t in targets:
        src = ROOT / t
        if not src.exists():
            print(f"  [skip] {t} (missing)")
            continue
        dst = ARCHIVE / f"{t}.pre-phase1.bak"
        shutil.copy2(src, dst)
        copied += 1
        print(f"  [ok]   {t} -> {dst.relative_to(ROOT)}")

    # Tag the current commit as the baseline
    try:
        subprocess.run(["git", "tag", "-f", "pre-phase1-baseline"],
                       cwd=ROOT, check=True)
        print("  [ok]   git tag pre-phase1-baseline")
    except subprocess.CalledProcessError as e:
        print(f"  [warn] could not tag: {e}")
    print(f"Backed up {copied} file(s) to {ARCHIVE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
