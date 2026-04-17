"""
PPS Anantam — Director Cockpit (5-Step Wizard)
================================================
Design: White-card fintech style. High-contrast numbers. Accent color strips.
Inspired by Stripe/Vercel/Linear dashboards — max readability, zero clutter.
Steps: Market Snapshot → Today's Targets → Update Prices → Price Calculator → Send Quote
"""

import streamlit as st
import json, os, datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── Data Helpers (unchanged logic) ─────────────────────────────────────────

def _load_json(f):
    try:
        with open(os.path.join(BASE_DIR, f), "r", encoding="utf-8") as fh: return json.load(fh)
    except Exception: return {}

@st.cache_data(ttl=300)
def _get_market_prices():
    p = {"brent": 0, "wti": 0, "usd_inr": 0, "vg30": 0}
    hub = _load_json("hub_cache.json")
    for c in hub.get("eia_crude", {}).get("data", []):
        if isinstance(c, dict) and c.get("benchmark") and c.get("price"):
            nm = str(c["benchmark"]).upper()
            try: pv = float(str(c["price"]).replace("$","").replace(",",""))
            except: continue
            if "BRENT" in nm: p["brent"] = pv
            elif "WTI" in nm: p["wti"] = pv
    for r in hub.get("frankfurter_fx", {}).get("data", []):
        if isinstance(r, dict) and "INR" in r.get("pair","").upper():
            try: p["usd_inr"] = round(float(r.get("rate", 83.5)), 2)
            except: pass
            break
    lp = _load_json("live_prices.json")
    p["vg30"] = lp.get("DRUM_KANDLA_VG30", lp.get("DRUM_MUMBAI_VG30", 35500))
    if not p["brent"]: p["brent"] = 82.50
    if not p["wti"]: p["wti"] = 78.30
    if not p["usd_inr"]: p["usd_inr"] = 83.50
    return p

def _get_ai_signal():
    try:
        from market_intelligence_engine import MarketIntelligenceEngine
        m = MarketIntelligenceEngine().compute_all_signals().get("master", {})
        d, c, a = m.get("market_direction","SIDEWAYS"), m.get("confidence",50), m.get("recommended_action","HOLD")
        if c > 60: l, cl = "BUY", "#10B981"
        elif c < 40: l, cl = "SELL", "#EF4444"
        else: l, cl = "HOLD", "#F59E0B"
        return {"label": l, "confidence": c, "color": cl, "direction": d, "action": a}
    except: return {"label":"HOLD","confidence":50,"color":"#F59E0B","direction":"SIDEWAYS","action":"Monitor market"}

def _get_alerts(n=3):
    try:
        from database import get_alerts
        a = get_alerts(status="new", limit=n)
        return a if a else []
    except: return []

def _get_hot_leads():
    try:
        from crm_engine import get_due_tasks
        return get_due_tasks("Overdue") + get_due_tasks("Today")
    except: return []

def _find_sources(city, grade, lt, n=3):
    try:
        from calculation_engine import get_engine
        return get_engine().find_best_sources(city, grade=grade, load_type=lt, top_n=n)
    except: return []

def _get_offer_tiers(lc):
    try:
        from calculation_engine import get_engine
        return get_engine().generate_offer_prices(lc)
    except: return {"aggressive":{"price":lc+500,"margin":500},"balanced":{"price":lc+1000,"margin":1000},"premium":{"price":lc+1500,"margin":1500}}

def _gen_wa_msg(cust, city, grade, qty, price, src=""):
    try:
        from communication_engine import CommunicationHub
        msg = CommunicationHub().whatsapp_offer(cust, city, grade, qty, price, src)
        if not msg:
            return ""
        # Defensive: strip any lone surrogates so downstream UTF-8 encoding
        # (Streamlit response, PDF export) doesn't raise.
        return "".join(c for c in msg if not 0xD800 <= ord(c) <= 0xDFFF)
    except: return f"Dear {cust},\n\nPPS Anantams - Rate Offer\nGrade: {grade} | Qty: {qty} MT\nPrice: Rs.{price:,.0f}/MT\nCity: {city}\n\n100% Advance | 24hr Validity\nPrince P Shah | +91 7795242424"


from components.message_preview import render_msg_preview as _render_msg_preview

def _log_crm(cust, ch, content):
    try:
        from database import log_communication
        log_communication({"customer_id":cust,"channel":ch,"direction":"outbound","subject":f"Quote via {ch}","content":content[:500],"template_used":"cockpit","sent_at":datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),"status":"sent"})
    except: pass

def _make_followup(cust, days=3):
    try:
        from crm_engine import add_task
        d = (datetime.datetime.now()+datetime.timedelta(days=days)).strftime("%d-%m-%Y %H:%M")
        add_task(cust, "Call", d, priority="High", note="Follow-up on Cockpit quote")
    except: pass


# ─── Premium CSS Design System ──────────────────────────────────────────────

def _css():
    st.markdown("""<style>
/* === DESIGN TOKENS === */
/* Palette: Slate base, Indigo accent, Emerald success, Amber warning, Rose danger */
/* White cards + colored accent strips = max readability (Stripe/Linear pattern) */

/* Header — Deep dark with subtle gradient, no heavy colors */
.ck-hd{background:#0F172A;border-radius:18px;padding:28px 32px;margin-bottom:22px;display:flex;align-items:center;justify-content:space-between;position:relative;overflow:hidden}
.ck-hd::before{content:'';position:absolute;right:20px;top:50%;transform:translateY(-50%);width:120px;height:80px;opacity:0.04;background:repeating-conic-gradient(#fff 0% 25%,transparent 0% 50%) 0 0/16px 16px;pointer-events:none}
.ck-hd .t{font-size:1.55rem;font-weight:800;color:#F8FAFC;letter-spacing:-0.04em;position:relative}
.ck-hd .s{font-size:0.82rem;color:#64748B;margin-top:3px;font-weight:500;position:relative}
.ck-hd .dt{background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:8px 18px;color:#94A3B8;font-size:0.78rem;font-weight:600;position:relative}

/* Steps — Pill tabs */
.ck-st{display:flex;gap:3px;background:#F1F5F9;border-radius:12px;padding:4px;margin-bottom:24px}
.ck-s{flex:1;display:flex;align-items:center;justify-content:center;gap:7px;padding:10px 6px;border-radius:9px;font-size:0.78rem;font-weight:600;color:#94A3B8;cursor:default;transition:all 0.25s}
.ck-s.a{background:#fff;color:#4F46E5;box-shadow:0 1px 8px rgba(79,70,229,0.1),0 1px 3px rgba(0,0,0,0.06);font-weight:700}
.ck-s.d{color:#10B981}
.ck-n{width:22px;height:22px;border-radius:7px;display:inline-flex;align-items:center;justify-content:center;font-size:0.65rem;font-weight:800;flex-shrink:0}
.ck-s.a .ck-n{background:#4F46E5;color:#fff}
.ck-s.d .ck-n{background:#D1FAE5;color:#10B981}
.ck-s:not(.a):not(.d) .ck-n{background:#E2E8F0;color:#94A3B8}

/* KPI — White cards with accent strip + background tile squares pattern */
.ck-kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}
.ck-kpi{background:#fff;border-radius:14px;padding:20px;border:1px solid #E2E8F0;position:relative;overflow:hidden;transition:all 0.2s}
.ck-kpi:hover{box-shadow:0 8px 24px rgba(0,0,0,0.06);transform:translateY(-2px)}
.ck-kpi::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;border-radius:4px 0 0 4px}
/* Decorative tile squares in background */
.ck-kpi::after{content:'';position:absolute;right:8px;top:8px;width:48px;height:48px;border-radius:10px;opacity:0.06;background:repeating-conic-gradient(currentColor 0% 25%,transparent 0% 50%) 0 0/14px 14px}
.ck-kpi .ki{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.ck-kpi .ki .dot{width:8px;height:8px;border-radius:50%}
.ck-kpi .kl{font-size:0.65rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.1em}
.ck-kpi .kv{font-size:1.75rem;font-weight:900;color:#0F172A;letter-spacing:-0.04em;line-height:1}
.ck-kpi.c1{color:#6366F1} .ck-kpi.c1::before{background:#6366F1} .ck-kpi.c1 .dot{background:#6366F1}
.ck-kpi.c2{color:#0EA5E9} .ck-kpi.c2::before{background:#0EA5E9} .ck-kpi.c2 .dot{background:#0EA5E9}
.ck-kpi.c3{color:#10B981} .ck-kpi.c3::before{background:#10B981} .ck-kpi.c3 .dot{background:#10B981}
.ck-kpi.c4{color:#8B5CF6} .ck-kpi.c4::before{background:#8B5CF6} .ck-kpi.c4 .dot{background:#8B5CF6}
/* Ensure text stays black (not inheriting card color) */
.ck-kpi .kv{color:#0F172A}
.ck-kpi .kl{color:#94A3B8}

/* Signal */
.ck-sig{background:#fff;border-radius:14px;padding:24px;border:1px solid #E2E8F0;text-align:center;position:relative;overflow:hidden}
.ck-sig::after{content:'';position:absolute;left:10px;bottom:10px;width:40px;height:40px;border-radius:8px;opacity:0.04;background:repeating-conic-gradient(#10B981 0% 25%,transparent 0% 50%) 0 0/12px 12px}
.ck-sig .sh{font-size:0.58rem;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:14px}
.ck-sig .sr{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:12px}
.ck-sig .sd{width:10px;height:10px;border-radius:50%;animation:ckp 2s ease infinite}
@keyframes ckp{0%,100%{box-shadow:0 0 0 0 currentColor}50%{box-shadow:0 0 0 8px transparent}}
.ck-sig .sl{font-size:1.8rem;font-weight:900;letter-spacing:-0.03em}
.ck-sig .sc{font-size:0.9rem;font-weight:700;opacity:0.5}
.ck-sig .sb{width:100%;height:4px;background:#F1F5F9;border-radius:2px;margin:0 0 12px;overflow:hidden}
.ck-sig .sf{height:100%;border-radius:2px}
.ck-sig .si{font-size:0.75rem;color:#64748B;line-height:1.6}

/* Alerts */
.ck-al{background:#fff;border-radius:14px;padding:20px 22px;border:1px solid #E2E8F0;position:relative;overflow:hidden}
.ck-al::after{content:'';position:absolute;right:10px;bottom:10px;width:40px;height:40px;border-radius:8px;opacity:0.04;background:repeating-conic-gradient(#EF4444 0% 25%,transparent 0% 50%) 0 0/12px 12px}
.ck-al .ah{font-size:0.58rem;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:0.14em;margin-bottom:12px;display:flex;align-items:center;gap:6px}
.ck-al .adot{width:5px;height:5px;border-radius:50%;background:#EF4444;animation:ckp 2s ease infinite;color:#EF4444}
.ck-ai{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;margin-bottom:5px}
.ck-ai .ab{font-size:0.6rem;font-weight:800;padding:2px 8px;border-radius:5px;flex-shrink:0}
.ck-ai .ax{font-size:0.8rem;font-weight:500;color:#334155}

/* Section Hdr */
.ck-sec{display:flex;align-items:center;gap:12px;margin-bottom:4px}
.ck-sec .ic{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.15rem}
.ck-sec .tt{font-size:1.15rem;font-weight:800;color:#0F172A;letter-spacing:-0.02em}
.ck-sec .su{font-size:0.76rem;color:#64748B}

/* Leads */
.ck-ld{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:14px 18px;margin-bottom:8px;transition:all 0.2s;position:relative;overflow:hidden}
.ck-ld::after{content:'';position:absolute;right:8px;top:50%;transform:translateY(-50%);width:32px;height:32px;opacity:0.04;background:repeating-conic-gradient(#6366F1 0% 25%,transparent 0% 50%) 0 0/10px 10px}
.ck-ld:hover{box-shadow:0 6px 20px rgba(0,0,0,0.05);border-color:#C7D2FE;transform:translateY(-1px)}

/* Sources */
.ck-sr{background:#fff;border:1px solid #E2E8F0;border-radius:12px;padding:14px 18px;margin-bottom:8px;transition:all 0.2s}
.ck-sr:hover{box-shadow:0 4px 16px rgba(0,0,0,0.05);transform:translateY(-1px)}

/* Tiers */
.ck-tr{background:#fff;border-radius:16px;padding:24px 14px;text-align:center;border:1.5px solid #E2E8F0;transition:all 0.25s;position:relative;overflow:hidden}
.ck-tr::after{content:'';position:absolute;right:6px;top:6px;width:36px;height:36px;border-radius:8px;opacity:0.05;background:repeating-conic-gradient(currentColor 0% 25%,transparent 0% 50%) 0 0/10px 10px}
.ck-tr:hover{transform:translateY(-4px);box-shadow:0 12px 32px rgba(0,0,0,0.08)}
.ck-tr .ti{font-size:1.8rem;margin-bottom:4px}
.ck-tr .tn{font-size:0.65rem;font-weight:800;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:10px}
.ck-tr .tp{font-size:1.55rem;font-weight:900;color:#0F172A;letter-spacing:-0.03em}
.ck-tr .tu{font-size:0.7rem;color:#94A3B8}
.ck-tr .tm{font-size:0.7rem;color:#64748B;margin-top:10px;padding-top:10px;border-top:1px dashed #E2E8F0}

/* Quote */
.ck-qt{background:#FAFBFC;border:1px solid #E2E8F0;border-radius:16px;padding:24px;position:relative;overflow:hidden}
.ck-qt::after{content:'';position:absolute;right:12px;top:12px;width:56px;height:56px;border-radius:10px;opacity:0.04;background:repeating-conic-gradient(#10B981 0% 25%,transparent 0% 50%) 0 0/14px 14px}
.ck-qg{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.ck-qi .ql{font-size:0.58rem;font-weight:800;color:#94A3B8;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:4px}
.ck-qi .qv{font-size:0.92rem;font-weight:700;color:#1E293B}

/* Step pills not used — buttons handle navigation */

@media(max-width:768px){.ck-kpis{grid-template-columns:1fr 1fr}.ck-hd{flex-direction:column;text-align:center;gap:12px}.ck-qg{grid-template-columns:1fr 1fr}}
</style>""", unsafe_allow_html=True)


# ─── Step Bar (clickable buttons) ──────────────────────────────────────────

def _steps(cur):
    st_list = [("1","Market Snapshot"),("2","Today's Targets"),("3","Update Prices"),("4","Price Calculator"),("5","Send Quote")]
    icons = ["📊","🎯","📝","🧮","📤"]
    cols = st.columns(5)
    for idx, (n, lb) in enumerate(st_list):
        i = int(n)
        with cols[idx]:
            # Active = primary, Done = checkmark, Future = plain
            if i == cur:
                st.button(f"{icons[idx]} {lb}", key=f"sj_{i}", use_container_width=True, type="primary", disabled=True)
            elif i < cur:
                if st.button(f"✓ {lb}", key=f"sj_{i}", use_container_width=True):
                    st.session_state["_ck"] = i; st.rerun()
            else:
                if st.button(f"{n}  {lb}", key=f"sj_{i}", use_container_width=True):
                    st.session_state["_ck"] = i; st.rerun()
    st.markdown("")


# ─── Step 1 ─────────────────────────────────────────────────────────────────

def _step1():
    p = _get_market_prices()
    sig = _get_ai_signal()

    st.markdown('<div class="ck-sec"><div class="ic" style="background:#EEF2FF;">&#128202;</div><div><div class="tt">Market Snapshot</div><div class="su">Live prices + AI signal at a glance</div></div></div>', unsafe_allow_html=True)
    st.markdown("")

    # White KPI cards with colored left strip
    st.markdown(f'<div class="ck-kpis">'
        f'<div class="ck-kpi c1"><div class="ki"><div class="kl">Brent Crude</div><div class="dot"></div></div><div class="kv">${p["brent"]:.2f}</div></div>'
        f'<div class="ck-kpi c2"><div class="ki"><div class="kl">WTI Crude</div><div class="dot"></div></div><div class="kv">${p["wti"]:.2f}</div></div>'
        f'<div class="ck-kpi c3"><div class="ki"><div class="kl">USD / INR</div><div class="dot"></div></div><div class="kv">&#8377;{p["usd_inr"]:.2f}</div></div>'
        f'<div class="ck-kpi c4"><div class="ki"><div class="kl">VG30 Bitumen</div><div class="dot"></div></div><div class="kv">&#8377;{p["vg30"]:,.0f}</div></div>'
        f'</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([2, 3])
    with c1:
        st.markdown(f'<div class="ck-sig"><div class="sh">AI Market Signal</div><div class="sr"><div class="sd" style="background:{sig["color"]};color:{sig["color"]};"></div><span class="sl" style="color:{sig["color"]};">{sig["label"]}</span><span class="sc" style="color:{sig["color"]};">{sig["confidence"]}%</span></div><div class="sb"><div class="sf" style="width:{sig["confidence"]}%;background:{sig["color"]};"></div></div><div class="si"><strong>Direction:</strong> {sig["direction"]}<br>{sig["action"]}</div></div>', unsafe_allow_html=True)

    with c2:
        alerts = _get_alerts(3)
        ai = ""
        if alerts:
            for a in alerts[:3]:
                pr = a.get("priority","P1"); t = a.get("title","Alert")
                if pr == "P0": ai += f'<div class="ck-ai" style="background:#FEF2F2;"><span class="ab" style="background:#FECDD3;color:#E11D48;">{pr}</span><span class="ax">{t}</span></div>'
                elif pr == "P1": ai += f'<div class="ck-ai" style="background:#FFFBEB;"><span class="ab" style="background:#FDE68A;color:#B45309;">{pr}</span><span class="ax">{t}</span></div>'
                else: ai += f'<div class="ck-ai" style="background:#EFF6FF;"><span class="ab" style="background:#BFDBFE;color:#1D4ED8;">{pr}</span><span class="ax">{t}</span></div>'
        else:
            ai = '<div class="ck-ai" style="background:#F0FDF4;"><span class="ab" style="background:#BBF7D0;color:#16A34A;">OK</span><span class="ax">No active alerts</span></div>'
        st.markdown(f'<div class="ck-al"><div class="ah"><div class="adot"></div>LIVE ALERTS</div>{ai}</div>', unsafe_allow_html=True)

    st.markdown("")
    if st.button("Next  \u2192  Today's Targets", type="primary", key="s1n"):
        st.session_state["_ck"] = 2; st.rerun()


# ─── Step 2 ─────────────────────────────────────────────────────────────────

def _step2():
    st.markdown('<div class="ck-sec"><div class="ic" style="background:#FEF3C7;">&#127919;</div><div><div class="tt">Today\'s Targets</div><div class="su">Hot leads &amp; overdue - click to auto-fill pricing</div></div></div>', unsafe_allow_html=True)
    st.markdown("")

    leads = _get_hot_leads()
    if not leads:
        try:
            from components.empty_state import render_empty_state
            render_empty_state(
                key="dc_targets",
                icon="🎉",
                title="Aaj koi overdue/due-today task nahi — all clear!",
                hint="Opportunities se naya target uthao ya Scan chalao.",
                cta_label="→ Open Opportunities",
                cta_target="🔍 Opportunities",
                tone="success",
            )
        except Exception:
            st.info("No overdue or due-today tasks. All clear!")
    else:
        for i, ld in enumerate(leads[:8]):
            cl = ld.get("client","?"); tt = ld.get("type","Call"); pr = ld.get("priority","Medium")
            du = ld.get("due_date",""); nt = ld.get("note","")
            pc = "#E11D48" if pr == "High" else ("#B45309" if pr == "Medium" else "#1D4ED8")
            pbg = "#FFF1F2" if pr == "High" else ("#FFFBEB" if pr == "Medium" else "#EFF6FF")
            ci, ca = st.columns([3, 1])
            with ci:
                st.markdown(f'<div class="ck-ld"><div style="display:flex;justify-content:space-between;align-items:center;"><div><strong>{cl}</strong> <span style="background:{pbg};color:{pc};padding:2px 8px;border-radius:6px;font-size:0.65rem;font-weight:700;margin-left:6px;">{pr}</span></div><span style="font-size:0.72rem;color:#94A3B8;">{tt} &bull; {du}</span></div><div style="font-size:0.78rem;color:#64748B;margin-top:3px;">{nt}</div></div>', unsafe_allow_html=True)
            with ca:
                if st.button("Select \u2192", key=f"l{i}"):
                    st.session_state["_ck_c"] = cl; st.session_state["_ck"] = 3; st.rerun()

    st.markdown("")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("\u2190 Back", key="s2b"): st.session_state["_ck"] = 1; st.rerun()
    with b2:
        if st.button("Next \u2192 Update Prices", type="primary", key="s2n"): st.session_state["_ck"] = 3; st.rerun()


# ─── Step 3: Manual Price Entry ────────────────────────────────────────────

def _step3():
    st.markdown('<div class="ck-sec"><div class="ic" style="background:#FEF3C7;">&#128221;</div><div><div class="tt">Update Prices</div><div class="su">Enter or update VG30/VG10 base prices — reflects everywhere instantly</div></div></div>', unsafe_allow_html=True)
    st.markdown("")

    # Load current prices
    lp_path = os.path.join(BASE_DIR, "live_prices.json")
    try:
        with open(lp_path, "r", encoding="utf-8") as f:
            lp = json.load(f)
    except Exception:
        lp = {}

    cur_mumbai_vg30 = lp.get("DRUM_MUMBAI_VG30", 37000)
    cur_kandla_vg30 = lp.get("DRUM_KANDLA_VG30", 35500)
    cur_mumbai_vg10 = lp.get("DRUM_MUMBAI_VG10", 38000)
    cur_kandla_vg10 = lp.get("DRUM_KANDLA_VG10", 36500)

    # Show current prices
    st.markdown(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:12px;padding:16px 20px;margin-bottom:16px;">
<div style="font-size:0.72rem;font-weight:700;color:#16A34A;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:8px;">&#9989; Current Live Prices</div>
<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:12px;">
<div><span style="font-size:0.68rem;color:#64748B;">Mumbai VG30</span><br><strong style="font-size:1.1rem;color:#0F172A;">&#8377;{cur_mumbai_vg30:,}/MT</strong></div>
<div><span style="font-size:0.68rem;color:#64748B;">Kandla VG30</span><br><strong style="font-size:1.1rem;color:#0F172A;">&#8377;{cur_kandla_vg30:,}/MT</strong></div>
<div><span style="font-size:0.68rem;color:#64748B;">Mumbai VG10</span><br><strong style="font-size:1.1rem;color:#0F172A;">&#8377;{cur_mumbai_vg10:,}/MT</strong></div>
<div><span style="font-size:0.68rem;color:#64748B;">Kandla VG10</span><br><strong style="font-size:1.1rem;color:#0F172A;">&#8377;{cur_kandla_vg10:,}/MT</strong></div>
</div></div>""", unsafe_allow_html=True)

    # Entry form
    with st.form("ck_manual_price"):
        st.markdown("#### Enter New Prices")
        c1, c2 = st.columns(2)
        with c1:
            new_mumbai_vg30 = st.number_input("Mumbai VG30 (₹/MT)", min_value=10000, max_value=200000, value=cur_mumbai_vg30, step=100, key="ck_mv30")
            new_mumbai_vg10 = st.number_input("Mumbai VG10 (₹/MT)", min_value=10000, max_value=200000, value=cur_mumbai_vg10, step=100, key="ck_mv10")
        with c2:
            new_kandla_vg30 = st.number_input("Kandla VG30 (₹/MT)", min_value=10000, max_value=200000, value=cur_kandla_vg30, step=100, key="ck_kv30")
            new_kandla_vg10 = st.number_input("Kandla VG10 (₹/MT)", min_value=10000, max_value=200000, value=cur_kandla_vg10, step=100, key="ck_kv10")

        remarks = st.text_input("Remarks (optional)", placeholder="e.g. IOCL revision, competitor quote...", key="ck_remarks")

        submitted = st.form_submit_button("✅ Update Prices", type="primary", use_container_width=True)
        if submitted:
            # Update live_prices.json
            lp["DRUM_MUMBAI_VG30"] = new_mumbai_vg30
            lp["DRUM_KANDLA_VG30"] = new_kandla_vg30
            lp["DRUM_MUMBAI_VG10"] = new_mumbai_vg10
            lp["DRUM_KANDLA_VG10"] = new_kandla_vg10
            try:
                with open(lp_path, "w", encoding="utf-8") as f:
                    json.dump(lp, f, indent=4, ensure_ascii=False)
                # Clear cached market prices so new values show up
                _get_market_prices.clear()
                # Reload calculation engine so calculator picks up new prices
                try:
                    from calculation_engine import get_engine
                    get_engine().reload_prices()
                except Exception:
                    pass
                # Save price snapshot for KPI change badges
                try:
                    snap_path = os.path.join(BASE_DIR, "tbl_price_history_snapshot.json")
                    old_snap = {}
                    if os.path.exists(snap_path):
                        with open(snap_path, "r") as sf:
                            old_snap = json.load(sf)
                    old_snap["vg30"] = new_kandla_vg30
                    with open(snap_path, "w") as sf:
                        json.dump(old_snap, sf, indent=2)
                except Exception:
                    pass
                # Clear any old calculator results so they recalculate
                st.session_state.pop("_ck_q", None)
                st.session_state.pop("_ck_srcs", None)
                st.session_state["_ck_price_updated"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Failed to save prices: {e}")

    # Show success if just updated
    if st.session_state.pop("_ck_price_updated", False):
        st.success("✅ Prices updated successfully! New rates will reflect across all pages — Command Center, Market Snapshot, Pricing Calculator, Rate Broadcast, etc.")

    st.markdown("")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("\u2190 Back", key="s3b"): st.session_state["_ck"] = 2; st.rerun()
    with b2:
        if st.button("Skip \u2192", key="s3s"): st.session_state["_ck"] = 4; st.rerun()
    with b3:
        if st.button("Next \u2192 Calculator", type="primary", key="s3n"): st.session_state["_ck"] = 4; st.rerun()


# ─── Step 4: Price Calculator ──────────────────────────────────────────────

def _step4():
    st.markdown('<div class="ck-sec"><div class="ic" style="background:#DBEAFE;">&#129518;</div><div><div class="tt">Instant Price Calculator</div><div class="su">Top sources + 3-tier offer</div></div></div>', unsafe_allow_html=True)
    st.markdown("")

    pf = st.session_state.get("_ck_c", "")
    try:
        from components.autosuggest import customer_picker, city_picker
        _have_pickers = True
    except Exception:
        _have_pickers = False
    c1, c2 = st.columns(2)
    with c1:
        if _have_pickers:
            cust = customer_picker(key="cc", default=pf)
        else:
            cust = st.text_input("Customer", value=pf, key="cc")
        gr = st.selectbox("Grade", ["VG30","VG10","VG40","CRMB-55","CRMB-60","PMB"], key="cg")
    with c2:
        if _have_pickers:
            city = city_picker(key="ci")
        else:
            city = st.text_input("City", key="ci", placeholder="Ahmedabad, Pune...")
        q1, q2 = st.columns(2)
        with q1: qty = st.number_input("Qty (MT)", min_value=1, value=20, step=1, key="cq")
        with q2: lt = st.selectbox("Load", ["Bulk","Drum"], key="cl")

    if st.button("Calculate", type="primary", key="ccalc"):
        if not cust or not city: st.warning("Enter Customer and City."); return
        srcs = _find_sources(city, gr, lt, 3)
        if not srcs: st.warning(f"No sources for {city}."); return
        best = srcs[0]; lc = best.get("landed_cost", 0)
        offers = _get_offer_tiers(lc)
        st.session_state["_ck_q"] = {"customer":cust,"city":city,"grade":gr,"qty":qty,"load_type":lt,"source":best.get("source",""),"landed_cost":lc,"offers":offers}
        st.session_state["_ck_srcs"] = srcs
        st.rerun()

    # Show results if calculated (persists across reruns)
    q = st.session_state.get("_ck_q")
    srcs = st.session_state.get("_ck_srcs")
    if q and srcs:
        st.markdown("---")
        st.markdown("**Top Sources**")
        clrs = ["#6366F1","#0EA5E9","#10B981"]
        for idx, s in enumerate(srcs):
            rc = clrs[idx] if idx < 3 else "#94A3B8"
            st.markdown(f'<div class="ck-sr" style="border-left:4px solid {rc};"><div style="display:flex;justify-content:space-between;align-items:center;"><div><strong>#{s.get("rank",idx+1)} {s.get("source","?")}</strong> <span style="font-size:0.72rem;color:#94A3B8;">{s.get("source_label",s.get("source_type",""))}</span></div><div style="text-align:right;"><strong style="font-size:1.05rem;color:{rc};">&#8377;{s.get("landed_cost",0):,.0f}/MT</strong><div style="font-size:0.65rem;color:#94A3B8;">Base &#8377;{s.get("base_price",0):,.0f} + Freight &#8377;{s.get("freight",0):,.0f} + GST &#8377;{s.get("gst",0):,.0f}</div></div></div></div>', unsafe_allow_html=True)

        offers = q.get("offers", {})
        st.markdown(""); st.markdown("**Offer Pricing**")

        t1, t2, t3 = st.columns(3)
        trs = [("aggressive","Aggressive","#EF4444","&#128293;",t1),("balanced","Balanced","#F59E0B","&#9878;&#65039;",t2),("premium","Premium","#10B981","&#128142;",t3)]
        for tk, tn, tc, ti, col in trs:
            td = offers.get(tk,{}); pr = td.get("price",0); mg = td.get("margin",0)
            with col:
                st.markdown(f'<div class="ck-tr" style="border-color:{tc}25;"><div class="ti">{ti}</div><div class="tn" style="color:{tc};">{tn}</div><div class="tp">&#8377;{pr:,.0f}<span class="tu">/MT</span></div><div class="tm">Margin &#8377;{mg:,.0f}/MT</div></div>', unsafe_allow_html=True)

        st.markdown("")
        tc = st.radio("Tier", ["Aggressive","Balanced","Premium"], index=1, horizontal=True, key="ct")
        st.session_state["_ck_t"] = tc.lower()
        if st.button("Next \u2192 Send Quote", type="primary", key="s4n"):
            st.session_state["_ck"] = 5; st.rerun()

    st.markdown("")
    if st.button("\u2190 Back", key="s4b"):
        st.session_state.pop("_ck_srcs", None)
        st.session_state["_ck"] = 3; st.rerun()


# ─── Step 5: Send Quote ───────────────────────────────────────────────────

def _step5():
    st.markdown('<div class="ck-sec"><div class="ic" style="background:#D1FAE5;">&#128228;</div><div><div class="tt">Send Quote</div><div class="su">Review, send, auto-log CRM</div></div></div>', unsafe_allow_html=True)
    st.markdown("")

    q = st.session_state.get("_ck_q")
    tk = st.session_state.get("_ck_t", "balanced")
    if not q:
        st.warning("No quote. Go back to Step 4 (Calculator).")
        if st.button("\u2190 Back", key="s5b0"): st.session_state["_ck"] = 4; st.rerun()
        return

    td = q.get("offers",{}).get(tk,{}); pr = td.get("price",0)
    cu = q["customer"]; ci = q["city"]; gr = q["grade"]; qt = q["qty"]; src = q["source"]

    st.markdown(f'<div class="ck-qt"><div class="ck-qg"><div class="ck-qi"><div class="ql">Customer</div><div class="qv">{cu}</div></div><div class="ck-qi"><div class="ql">City</div><div class="qv">{ci}</div></div><div class="ck-qi"><div class="ql">Source</div><div class="qv">{src}</div></div><div class="ck-qi"><div class="ql">Grade / Qty</div><div class="qv">{gr} - {qt} MT ({q.get("load_type","Bulk")})</div></div><div class="ck-qi"><div class="ql">Tier</div><div class="qv">{tk.title()}</div></div><div class="ck-qi"><div class="ql">Price</div><div class="qv" style="font-size:1.25rem;color:#10B981;font-weight:900;">&#8377;{pr:,.0f}/MT</div></div></div><div style="margin-top:14px;padding-top:12px;border-top:1px dashed #CBD5E1;font-size:0.78rem;color:#64748B;display:flex;justify-content:space-between;flex-wrap:wrap;gap:6px;"><span>Total: <strong style="color:#0F172A;">&#8377;{pr*qt:,.0f}</strong></span><span>100% Advance &bull; 24hr Validity &bull; Ex-Terminal</span></div></div>', unsafe_allow_html=True)

    # Show success message FIRST (if returning from send)
    snt = st.session_state.pop("_ck_snt", None)
    if snt:
        st.success(f"Quote sent via {snt}! CRM logged + 3-day follow-up created.")
        st.balloons()

    # Message preview — graphical bubble that mirrors the actual channel UI,
    # plus a collapsed editor below for manual tweaks.
    st.markdown("")
    try:
        msg_default = _gen_wa_msg(cu, ci, gr, qt, pr, src)
    except Exception:
        msg_default = f"Dear {cu},\n\nPPS Anantams - Rate Offer\nGrade: {gr} | Qty: {qt} MT\nPrice: Rs.{pr:,.0f}/MT\nCity: {ci}\n\n100% Advance | 24hr Validity\nPrince P Shah | +91 7795242424"
    # Pull current edit (if user tweaked) else use generated default
    msg = st.session_state.get("cm", msg_default)
    st.markdown(
        '<div style="font-size:0.82rem;font-weight:700;color:#475569;margin:6px 0 0 2px;">📱 Message Preview</div>',
        unsafe_allow_html=True,
    )
    _render_msg_preview(msg, channel="whatsapp")
    with st.expander("✏️ Edit message", expanded=False):
        msg = st.text_area("Msg", value=msg, height=180, key="cm",
                           help="Edit the WhatsApp message. *text* renders as bold in the preview above.")

    # ── Send & Share Buttons ──
    st.markdown("")
    st.markdown('<div class="ck-sec"><div class="ic" style="background:#EEF2FF;">&#128640;</div><div><div class="tt">Send & Share</div><div class="su">Choose channel to deliver quote</div></div></div>', unsafe_allow_html=True)
    st.markdown("")

    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        if st.button("WhatsApp", type="primary", key="sw", use_container_width=True):
            try: _log_crm(cu,"WhatsApp",msg)
            except: pass
            try: _make_followup(cu)
            except: pass
            st.session_state["_ck_snt"] = "WhatsApp"
            st.rerun()
    with s2:
        if st.button("Email", key="se", use_container_width=True):
            try: _log_crm(cu,"Email",msg)
            except: pass
            try: _make_followup(cu)
            except: pass
            st.session_state["_ck_snt"] = "Email"
            st.rerun()
    with s3:
        if st.button("Telegram", key="st", use_container_width=True):
            try: _log_crm(cu,"Telegram",msg)
            except: pass
            try: _make_followup(cu)
            except: pass
            st.session_state["_ck_snt"] = "Telegram"
            st.rerun()
    with s4:
        if st.button("PDF Quote", key="sp", use_container_width=True):
            try:
                from pdf_generator import create_price_pdf, get_next_quote_number
                qn = get_next_quote_number()
                pdf_path = create_price_pdf(cu, gr, src, pr, qty=qt, quote_no=qn, filename=f"Quote_{cu}_{ci}.pdf")
                if pdf_path:
                    with open(pdf_path, "rb") as pf:
                        st.session_state["_ck_pdf_data"] = pf.read()
                        st.session_state["_ck_pdf_name"] = f"Quote_{cu}_{ci}.pdf"
            except Exception:
                pass
            try: _log_crm(cu,"PDF",msg)
            except: pass
            try: _make_followup(cu)
            except: pass
            st.session_state["_ck_snt"] = "PDF"
            st.rerun()
    with s5:
        if st.button("Share Link", key="sl", use_container_width=True):
            try:
                from shareable_links_engine import create_share_link, generate_share_url
                token = create_share_link("Quote", content_json={"customer": cu, "city": ci, "grade": gr, "qty": qt, "price": pr, "source": src, "tier": tk}, created_by="cockpit")
                url = generate_share_url(token)
                st.session_state["_ck_share_url"] = url
            except Exception:
                pass
            try: _log_crm(cu,"Share Link",msg)
            except: pass
            st.session_state["_ck_snt"] = "Share Link"
            st.rerun()

    # Show share link if generated
    share_url = st.session_state.pop("_ck_share_url", None)
    if share_url:
        st.code(share_url, language=None)
        st.caption("Copy this link and share anywhere!")

    # Show PDF download button if generated
    pdf_data = st.session_state.pop("_ck_pdf_data", None)
    pdf_name = st.session_state.pop("_ck_pdf_name", "Quote.pdf")
    if pdf_data:
        st.download_button("Download PDF", data=pdf_data, file_name=pdf_name, mime="application/pdf", key="sp_dl")

    # ── WhatsApp Deep Link ──
    import urllib.parse
    wa_encoded = urllib.parse.quote(msg)
    # Try to find customer phone from contacts
    phone_clean = ""
    try:
        contacts_path = os.path.join(BASE_DIR, "tbl_contacts.json")
        if os.path.exists(contacts_path):
            with open(contacts_path, "r", encoding="utf-8") as cf:
                _contacts = json.load(cf)
            for _ct in _contacts:
                if _ct.get("name", "").lower() == cu.lower() or _ct.get("company", "").lower() == cu.lower():
                    _ph = str(_ct.get("phone", _ct.get("mobile", "")))
                    _ph = _ph.replace("+", "").replace(" ", "").replace("-", "")
                    if len(_ph) >= 10:
                        phone_clean = _ph if _ph.startswith("91") else f"91{_ph[-10:]}"
                        break
    except Exception:
        pass
    if not phone_clean:
        phone_clean = "917795242424"  # Fallback to PPS owner
    st.markdown(f'<a href="https://wa.me/{phone_clean}?text={wa_encoded}" target="_blank" style="display:inline-block;background:#25D366;color:#fff;padding:8px 20px;border-radius:8px;text-decoration:none;font-weight:700;font-size:0.85rem;margin-top:8px;">Open in WhatsApp</a>', unsafe_allow_html=True)

    st.markdown("")
    b1, b2 = st.columns(2)
    with b1:
        if st.button("\u2190 Back", key="s5b"): st.session_state["_ck"] = 4; st.rerun()
    with b2:
        if st.button("New Quote", type="primary", key="s5r"):
            for k in ["_ck","_ck_c","_ck_q","_ck_t","_ck_snt","_ck_srcs","_ck_share_url"]: st.session_state.pop(k,None)
            st.rerun()


# ─── Main ───────────────────────────────────────────────────────────────────

def render():
    _css()
    h = datetime.datetime.now().hour
    g = "Good Morning" if h < 12 else ("Good Afternoon" if h < 17 else "Good Evening")
    n = datetime.datetime.now()
    st.markdown(f'<div class="ck-hd"><div><div class="t">&#128142; One-Click Quote</div><div class="s">{g}, Sir</div></div><div class="dt">&#128197; {n.strftime("%d %b %Y")} &bull; {n.strftime("%A")}</div></div>', unsafe_allow_html=True)

    if "_ck" not in st.session_state: st.session_state["_ck"] = 1
    cur = st.session_state["_ck"]
    _steps(cur)
    [_step1, _step2, _step3, _step4, _step5][cur - 1]()
