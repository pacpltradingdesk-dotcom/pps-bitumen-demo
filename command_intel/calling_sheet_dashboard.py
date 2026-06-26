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
    # _auth_user is the full user dict; the human-readable name is _auth_display.
    # Using _auth_user here passed a dict into SQL -> "binding parameter ... dict".
    u = st.session_state.get("_auth_username") or "unknown"
    name = st.session_state.get("_auth_display") or u
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
    file_bytes = up.getvalue()
    # Multi-sheet Excel (e.g. a workbook with README + Hot/Warm Leads tabs):
    # let the user pick which sheet has the leads. Default to the first sheet
    # that isn't an obvious cover/summary page.
    chosen_sheet = None
    sheet_names = eng.excel_sheet_names(file_bytes, up.name)
    if len(sheet_names) > 1:
        _COVER = {"readme", "read me", "cover", "summary", "info",
                  "instructions", "about", "index", "notes"}
        default_idx = next((i for i, s in enumerate(sheet_names)
                            if s.strip().lower() not in _COVER), 0)
        chosen_sheet = st.selectbox(
            "Is Excel me kai sheets hain — kaunsi sheet use karni hai?",
            sheet_names, index=default_idx, key="cs_sheet_pick")
    try:
        df = eng.parse_file(file_bytes, up.name, sheet_name=chosen_sheet)
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
        # If a sheet for this date already exists, merge the new leads into it
        # instead of creating a second sheet for the same day.
        existing = [s for s in eng.list_sheets(user) if s["sheet_date"] == sheet_date]
        if existing:
            sid = existing[0]["id"]
            eng.add_rows(sid, user, rows)
            total = eng.sheet_summary(sid)["total"]
            st.success(f"{len(rows)} leads is din ki sheet me add ho gaye "
                       f"(total {total}). 'Today's Calls' tab me kaam karo.")
        else:
            sid = eng.create_sheet(user, name, sheet_date, up.name, up.name, rows)
            st.success(f"Sheet saved — {len(rows)} leads. "
                       f"Ab 'Today's Calls' tab me kaam karo.")
        st.session_state["cs_active_sheet"] = sid


def _render_today(user, name):
    st.subheader("📋 Today's calls")
    today = _today()
    if st.button("⬇️ Pull pending leads from previous days", key="cs_carry"):
        n = eng.carry_over_pending(user, name, today)
        st.success(f"{n} pending leads carried into today." if n
                   else "Koi pending lead nahi mila.")
        st.rerun()
    sheets = [s for s in eng.list_sheets(user) if s["sheet_date"] == today]
    if not sheets:
        st.info("Aaj ki koi sheet nahi. Upload tab se sheet daalo, ya History se "
                "carry-over karo.")
        if st.button("➕ Create empty sheet for today", key="cs_mk_today"):
            eng.get_or_create_today_sheet(user, name, today)
            st.rerun()
        return
    # pick sheet (usually one; allow choosing if multiple).
    labels = {f'{s["title"]} (#{s["id"]})': s["id"] for s in sheets}
    # If the user just uploaded a sheet, jump straight to it — otherwise the
    # selectbox stays on a previously-selected (maybe empty) sheet and the new
    # leads look "missing".
    active = st.session_state.pop("cs_active_sheet", None)
    if active:
        for _lbl, _sid in labels.items():
            if _sid == active:
                st.session_state["cs_today_pick"] = _lbl
                break
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
        _delete_control(sid, user, f"today_{sid}")
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

    _whatsapp_panel(user, rows)
    _delete_control(sid, user, f"today_{sid}")


def _render_history(user):
    st.subheader("🗂️ Past sheets")
    sheets = eng.list_sheets(user)
    if not sheets:
        st.info("Abhi koi sheet nahi.")
        return
    table = []
    for s in sheets:
        summ = eng.sheet_summary(s["id"])
        table.append({
            "Date": s["sheet_date"], "Title": s["title"],
            "Total": summ["total"], "Called": summ["called"],
            "% Called": summ["pct_called"], "Conversions": summ["conversions"],
            "id": s["id"],
        })
    st.dataframe(pd.DataFrame(table).drop(columns=["id"]),
                 use_container_width=True, hide_index=True)
    ids = {f'{t["Date"]} — {t["Title"]} (#{t["id"]})': t["id"] for t in table}
    pick = st.selectbox("Open a sheet", list(ids.keys()), key="cs_hist_pick")
    rows = eng.get_rows(ids[pick])
    st.dataframe(pd.DataFrame([{
        "Name": r["lead_name"], "Phone": r["phone"], "Company": r["company"],
        "Status": r["call_status"], "Outcome": r["outcome"],
        "Remark": r["remark"], "Follow-up": r["followup_date"] or "",
    } for r in rows]), use_container_width=True, hide_index=True)
    _delete_control(ids[pick], user, f"hist_{ids[pick]}")


def _render_team():
    st.subheader("👥 Team calling activity")
    rollup = eng.team_summary()
    if not rollup:
        st.info("Abhi kisi rep ki koi sheet nahi.")
        return
    reps = sorted({r["owner_username"] for r in rollup})
    pick = st.selectbox("Rep", ["(All)"] + reps, key="cs_team_rep")
    data = rollup if pick == "(All)" else [r for r in rollup
                                           if r["owner_username"] == pick]
    st.dataframe(pd.DataFrame([{
        "Rep": r["owner_name"] or r["owner_username"], "Date": r["sheet_date"],
        "Title": r["title"], "Total": r["total"], "Called": r["called"],
        "% Called": r["pct_called"], "Connected": r["connected"],
        "Conversions": r["conversions"],
    } for r in data]), use_container_width=True, hide_index=True)


def _lead_wa_number(r):
    """Best WhatsApp number for a lead: explicit WhatsApp col (from extra) else phone."""
    extra = r.get("extra") or {}
    for k in ("WhatsApp Number", "Whatsapp Number", "WhatsApp", "whatsapp"):
        if extra.get(k):
            return str(extra[k])
    return str(r.get("phone") or "")


def _whatsapp_panel(user, rows):
    """Send a WhatsApp to a lead from the SAME QR-linked number the AI chat uses
    (whatsapp_bridge -> pps-chat-wa /send). No separate WhatsApp."""
    st.markdown("---")
    st.markdown("##### 📲 WhatsApp a lead — aapke connected number se")
    try:
        import whatsapp_bridge as wab
        status = wab.link_status(user) or {}
    except Exception as e:
        st.caption(f"WhatsApp bridge unavailable: {e}")
        return
    if status.get("status") != "connected":
        st.info("Aapka WhatsApp abhi connect nahi hai. **Sales → Client Chat** page "
                "pe jaakar QR scan karke apna WhatsApp link karo — phir yahin se "
                f"leads ko message bhej paoge. (status: {status.get('status', 'offline')})")
        return
    st.caption(f"🟢 Connected: {status.get('number', '')}")
    leads = [r for r in rows if _lead_wa_number(r)]
    if not leads:
        st.caption("Is sheet ke kisi lead ka number nahi.")
        return
    pick = st.selectbox(
        "Lead", leads, key="cs_wa_lead",
        format_func=lambda r: f'{r.get("lead_name") or r.get("company") or "?"}'
                              f' — {_lead_wa_number(r)}')
    num = _lead_wa_number(pick)
    who = pick.get("lead_name") or pick.get("company") or ""
    default_msg = (f"Namaste {who}, PPS Anantam (bitumen) se baat kar rahe hain. "
                   "Aapke liye aaj ke rate bhej sakte hain?")
    msg = st.text_area("Message", value=default_msg, key="cs_wa_msg", height=90)
    if st.button("📲 Send WhatsApp", key="cs_wa_send", type="primary"):
        res = wab.send_text(num, msg, from_user=user)
        if res.get("ok") and not res.get("queued"):
            st.success(f"Bheja gaya — {res.get('channel', 'WhatsApp')}.")
        elif res.get("queued"):
            st.warning("WhatsApp service abhi offline — message queue me daal diya "
                       "(connect hote hi chala jaayega).")
        else:
            st.error(f"Send fail: {res.get('error', 'unknown')}")


def _delete_control(sid, user, key):
    # Two-step inline confirm (no expander — an expander collapses on the
    # confirm-rerun and hides the button, which made delete awkward).
    flag = f"cs_delask_{key}"
    if not st.session_state.get(flag):
        if st.button("🗑️ Remove this sheet", key=f"cs_delask_{key}"):
            st.session_state[flag] = True
            st.rerun()
    else:
        st.warning("Ye poori sheet + saare leads permanently delete ho jaayenge. "
                   "Wapas nahi aayega.")
        col1, col2 = st.columns(2)
        if col1.button("✅ Haan, delete karo", key=f"cs_delyes_{key}",
                       type="primary"):
            ok = eng.delete_sheet(sid, owner_username=user)
            st.session_state.pop(flag, None)
            if ok:
                st.success("Sheet deleted.")
            else:
                st.error("Delete nahi hua — ye sheet aapki nahi hai.")
            st.rerun()
        if col2.button("Cancel", key=f"cs_delno_{key}"):
            st.session_state.pop(flag, None)
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
        _render_history(user)
    if _is_director():
        with selected[3]:
            _render_team()
