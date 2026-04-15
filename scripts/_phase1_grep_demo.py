"""Phase 1 grep gate — zero demo-string check."""
import pathlib
forbidden = ['L&T Construction', 'Rohan Kumar', 'Shree Ganesh', 'Highway Builders']
hits = []
for p in pathlib.Path('.').rglob('*.py'):
    rel = str(p).replace('\\', '/')
    if any(x in rel for x in ['__pycache__', 'generate_pdf_demos',
                              'tests/', 'docs/', 'scripts/',
                              '.bak.archive', '.worktrees/']):
        continue
    try:
        txt = p.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        continue
    for needle in forbidden:
        if needle in txt:
            hits.append((rel, needle))
for h in hits:
    print(h)
print('total:', len(hits))
