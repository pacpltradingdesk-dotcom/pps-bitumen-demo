"""
Floating sidebar toggle — injects a persistent hide/show button into the
parent DOM via components.html. Needed because the app theme hides
Streamlit's native header, which suppresses the built-in collapse control
on Streamlit 1.56.
"""
from __future__ import annotations

import streamlit.components.v1 as _components


def inject() -> None:
    _components.html(
        """
<script>
(function(){
  try {
    const pdoc = window.parent.document;
    if (pdoc.getElementById('pps-sidebar-toggle')) return;

    const style = pdoc.createElement('style');
    style.id = 'pps-sidebar-toggle-style';
    style.textContent = `
      #pps-sidebar-toggle {
        position: fixed; top: 12px; left: 12px; z-index: 999999;
        width: 36px; height: 36px;
        background: #FFFFFF; border: 1px solid #E5E7EB;
        border-radius: 8px; cursor: pointer;
        box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        display: flex; align-items: center; justify-content: center;
        font-size: 20px; font-weight: 700; color: #1e3a5f;
        line-height: 1; padding: 0;
        transition: border-color 0.15s, box-shadow 0.15s;
      }
      #pps-sidebar-toggle:hover {
        border-color: #4F46E5;
        box-shadow: 0 2px 8px rgba(79,70,229,0.2);
      }
      body.pps-sb-hidden section[data-testid="stSidebar"],
      body.pps-sb-hidden [data-testid="stSidebar"] {
        display: none !important;
      }
    `;
    pdoc.head.appendChild(style);

    const btn = pdoc.createElement('button');
    btn.id = 'pps-sidebar-toggle';
    btn.title = 'Hide / show sidebar';
    btn.type = 'button';

    const lsKey = 'pps_sb_hidden';
    const saved = pdoc.defaultView.localStorage.getItem(lsKey) === '1';
    if (saved) pdoc.body.classList.add('pps-sb-hidden');
    btn.textContent = saved ? '\u2630' : '\u2715';

    btn.addEventListener('click', function(){
      const isHidden = pdoc.body.classList.toggle('pps-sb-hidden');
      pdoc.defaultView.localStorage.setItem(lsKey, isHidden ? '1' : '0');
      btn.textContent = isHidden ? '\u2630' : '\u2715';
    });

    pdoc.body.appendChild(btn);
  } catch (e) {
    console.error('sidebar toggle inject failed:', e);
  }
})();
</script>
        """,
        height=0,
        width=0,
    )
