"""
PPS Anantam — Daily Calling Sheet (Sales)
Upload a daily calling sheet, work it (status/remark/outcome/follow-up per row),
keep a separate sheet per day with carry-over, full per-user record. Director
sees all reps + a Team tab.
"""
import datetime
import streamlit as st
import pandas as pd
import calling_sheet_engine as eng


def _current_user():
    u = st.session_state.get("_auth_username") or "unknown"
    name = st.session_state.get("_auth_user") or u
    return u, name


def _is_director():
    try:
        from role_engine import get_current_role
        return get_current_role() in ("director", "admin")
    except Exception:
        return False


def _today():
    return datetime.date.today().strftime("%Y-%m-%d")


def _render_upload(user, name):
    st.subheader("📤 Upload calling sheet")
    up = st.file_uploader("Excel or CSV", type=["csv", "xls", "xlsx"],
                          key="cs_upload")
    if not up:
        st.info("Apni daily calling sheet (Excel/CSV) upload karo. "
                "Columns auto-detect ho jaayenge.")
        return
    try:
        df = eng.parse_file(up.getvalue(), up.name)
    except Exception as e:
        st.error(f"File padhne me dikkat: {e}")
        return
    if df.empty:
        st.warning("Sheet khaali hai.")
        return

    cols = list(df.columns)
    detected = eng.detect_columns(cols)
    st.caption(f"{len(df)} rows mile. Columns map karo:")
    opts = ["(none)"] + cols
    c1, c2, c3, c4 = st.columns(4)
    mapping = {}
    for col_box, field, label in [
        (c1, "lead_name", "Name"), (c2, "phone", "Phone"),
        (c3, "company", "Company"), (c4, "city", "City")]:
        with col_box:
            default = detected.get(field) or "(none)"
            idx = opts.index(default) if default in opts else 0
            pick = st.selectbox(label, opts, index=idx, key=f"cs_map_{field}")
            mapping[field] = None if pick == "(none)" else pick

    sheet_date = st.date_input("Sheet date", value=datetime.date.today(),
                               key="cs_date").strftime("%Y-%m-%d")
    st.dataframe(df.head(10), use_container_width=True)

    if st.button("✅ Save this sheet", type="primary", key="cs_save"):
        rows = eng.normalize_rows(df, mapping)
        if not rows:
            st.error("Koi valid row nahi (name/phone dono khaali).")
            return
        sid = eng.create_sheet(user, name, sheet_date, up.name, up.name, rows)
        st.success(f"Sheet saved — {len(rows)} leads. Ab 'Today's Calls' tab me kaam karo.")
        st.session_state["cs_active_sheet"] = sid


def _render_today(user, name):
    st.subheader("📋 Today's calls")
    today = _today()
    sheets = [s for s in eng.list_sheets(user) if s["sheet_date"] == today]
    if not sheets:
        st.info("Aaj ki koi sheet nahi. Upload tab se sheet daalo, ya History se "
                "carry-over karo.")
        if st.button("➕ Create empty sheet for today", key="cs_mk_today"):
            eng.get_or_create_today_sheet(user, name, today)
            st.rerun()
        return
    # pick sheet (usually one; allow choosing if multiple)
    labels = {f'{s["title"]} (#{s["id"]})': s["id"] for s in sheets}
    chosen = st.selectbox("Sheet", list(labels.keys()), key="cs_today_pick")
    sid = labels[chosen]

    summ = eng.sheet_summary(sid)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", summ["total"])
    m2.metric("Called", f'{summ["called"]} ({summ["pct_called"]}%)')
    m3.metric("Connected", summ["connected"])
    m4.metric("Conversions", summ["conversions"])

    rows = eng.get_rows(sid)
    if not rows:
        st.info("Is sheet me koi lead nahi.")
        return
    df = pd.DataFrame([{
        "id": r["id"], "Name": r["lead_name"], "Phone": r["phone"],
        "Company": r["company"], "Status": r["call_status"] or "Pending",
        "Outcome": r["outcome"] or "", "Remark": r["remark"] or "",
        "Follow-up": r["followup_date"] or "",
    } for r in rows])

    edited = st.data_editor(
        df, key="cs_editor", use_container_width=True, hide_index=True,
        disabled=["id", "Name", "Phone", "Company"],
        column_config={
            "id": None,  # hidden
            "Status": st.column_config.SelectboxColumn(options=eng.CALL_STATUSES),
            "Outcome": st.column_config.SelectboxColumn(options=eng.OUTCOMES),
            "Remark": st.column_config.TextColumn(),
            "Follow-up": st.column_config.TextColumn(help="YYYY-MM-DD"),
        })

    if st.button("💾 Save changes", type="primary", key="cs_save_today"):
        before = {r["id"]: r for r in rows}
        n = 0
        for _, er in edited.iterrows():
            rid = int(er["id"])
            b = before.get(rid, {})
            new = {
                "call_status": er["Status"], "outcome": er["Outcome"],
                "remark": er["Remark"],
                "followup_date": er["Follow-up"] or None,
            }
            if (new["call_status"] != (b.get("call_status") or "Pending")
                    or new["outcome"] != (b.get("outcome") or "")
                    or new["remark"] != (b.get("remark") or "")
                    or (new["followup_date"] or "") != (b.get("followup_date") or "")):
                eng.update_row(rid, new)
                n += 1
        st.success(f"{n} rows updated.")
        st.rerun()


def render():
    st.header("📞 Daily Calling Sheet")
    st.caption("Apni daily calling list upload karo, har call pe remark/status/outcome "
               "set karo. Har din ki alag sheet, poora record save rehta hai.")
    user, name = _current_user()
    tabs = ["📤 Upload", "📋 Today's Calls", "🗂️ History"]
    if _is_director():
        tabs.append("👥 Team")
    selected = st.tabs(tabs)
    with selected[0]:
        _render_upload(user, name)
    with selected[1]:
        _render_today(user, name)
    with selected[2]:
        st.info("History — Task 9 me aayega.")
    if _is_director():
        with selected[3]:
            st.info("Team — Task 10 me aayega.")
