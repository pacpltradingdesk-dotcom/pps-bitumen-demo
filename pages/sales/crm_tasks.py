"""
PPS Anantam — CRM & Tasks Page
=================================
Contact management, relationship scoring, task management.
"""
import streamlit as st


def render():
    st.markdown('<div class="pps-page-header"><div class="pps-page-title">🎯 Sales CRM & Daily Worklist</div></div>', unsafe_allow_html=True)
    st.caption("Never miss a follow-up. Manage calls, tasks, and client engagement.")

    import crm_engine as crm

    # KPI Header
    k1, k2, k3, k4 = st.columns(4)
    tasks_today = crm.get_due_tasks("Today")
    tasks_overdue = crm.get_due_tasks("Overdue")
    k1.metric("🔥 Hot Leads", "3", "Active")
    k2.metric("📅 Tasks Due Today", len(tasks_today), "For Action")
    k3.metric("⚠️ Overdue", len(tasks_overdue), "High Priority", delta_color="inverse")
    k4.metric("💰 Deals Closing", "2", "This Week")

    st.markdown("---")

    # Main Worklist
    crm_t1, crm_t2, crm_t3 = st.tabs(["📋 Today's Worklist", "📅 Calendar", "⚙️ Automation Rules"])

    with crm_t1:
        tf_col1, tf_col2 = st.columns([3, 1])
        with tf_col1:
            task_view = st.selectbox("View Tasks", ["Due Today", "Overdue", "Upcoming"])
        with tf_col2:
            if st.button("🔄 Refresh"):
                st.rerun()

        current_tasks = crm.get_due_tasks("Today")
        if task_view == "Overdue":
            current_tasks = crm.get_due_tasks("Overdue")

        if not current_tasks:
            st.success("🎉 No tasks in this view! You are all caught up.")
        else:
            for t in current_tasks:
                with st.container():
                    c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                    with c1:
                        st.markdown(f"**{t['client']}**")
                        st.caption(f"📌 {t['note']}")
                    with c2:
                        st.write(f"**{t['type']}**")
                        st.caption(f"Due: {t['due_date']}")
                    with c3:
                        if t['priority'] == 'High':
                            st.error("High Priority")
                        elif t['priority'] == 'Medium':
                            st.warning("Medium")
                        else:
                            st.info("Low")
                    with c4:
                        if st.button("✅ Done", key=f"done_{t['id']}"):
                            crm.complete_task(t['id'], "Marked done from Dashboard")
                            st.success("Task Closed!")
                            st.rerun()
                    st.markdown("---")

    with crm_t2:
        _render_calendar_tab(crm)

    with crm_t3:
        st.write("### 🤖 Automation Enabled")
        st.write("- **New Enquiry**: Auto-create Call Task (15min)")
        st.write("- **Quoted**: Auto-create Follow-up (2hr)")
        st.write("- **Payment**: Auto-create Daily Reminder")

    # Quick Add Task
    with st.expander("➕ Add New Task Manually", expanded=False):
        with st.form("new_task_form"):
            new_client = st.text_input("Client Name")
            new_type = st.selectbox("Task Type", ["Call", "Email", "Visit", "Follow-up", "Payment"])
            new_note = st.text_area("Notes")
            new_priority = st.selectbox("Priority", ["High", "Medium", "Low"])
            new_due = st.date_input("Due Date")
            if st.form_submit_button("Add Task", type="primary"):
                try:
                    crm.add_task(new_client, new_type, str(new_due), new_note, new_priority)
                    st.success("Task added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to add task: {e}")


def _render_calendar_tab(crm):
    """Render a working monthly calendar view with tasks color-coded by due status."""
    try:
        import calendar
        import datetime
    except ImportError:
        st.error("Calendar module not available.")
        return

    # Month/Year selectors
    today = datetime.date.today()
    cal_c1, cal_c2, cal_c3 = st.columns([1, 1, 2])
    with cal_c1:
        selected_month = st.selectbox(
            "Month",
            list(range(1, 13)),
            index=today.month - 1,
            format_func=lambda m: calendar.month_name[m],
            key="cal_month"
        )
    with cal_c2:
        selected_year = st.selectbox(
            "Year",
            list(range(today.year - 1, today.year + 2)),
            index=1,
            key="cal_year"
        )
    with cal_c3:
        st.markdown("")
        st.markdown(
            "🔴 Overdue &nbsp;&nbsp; 🟠 Today &nbsp;&nbsp; 🟢 Upcoming &nbsp;&nbsp; ⚪ No Tasks"
        )

    # Fetch all tasks and build a date-to-tasks mapping
    all_tasks = crm.get_tasks()
    pending_tasks = [t for t in all_tasks if t.get("status") == "Pending"]

    # Parse task due dates into date objects
    task_by_date = {}
    for t in pending_tasks:
        due_str = t.get("due_date", "") or ""
        parsed_date = None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y-%m-%d"):
            try:
                parsed_date = datetime.datetime.strptime(due_str.split(" ")[0] if " " in due_str else due_str, fmt).date()
                break
            except (ValueError, IndexError):
                continue
        if parsed_date:
            task_by_date.setdefault(parsed_date, []).append(t)

    # Build calendar grid
    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdayscalendar(selected_year, selected_month)

    # Header row
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    header_cols = st.columns(7)
    for idx, dn in enumerate(day_names):
        header_cols[idx].markdown(
            f"<div style='text-align:center;font-weight:700;font-size:0.85rem;'>{dn}</div>",
            unsafe_allow_html=True
        )

    # Calendar rows
    for week in month_days:
        week_cols = st.columns(7)
        for idx, day_num in enumerate(week):
            with week_cols[idx]:
                if day_num == 0:
                    st.markdown("<div style='height:70px;'></div>", unsafe_allow_html=True)
                    continue

                cell_date = datetime.date(selected_year, selected_month, day_num)
                day_tasks = task_by_date.get(cell_date, [])

                # Determine color based on status
                if cell_date < today and day_tasks:
                    bg_color = "#fee2e2"  # red - overdue
                    border_color = "#ef4444"
                    dot = "🔴"
                elif cell_date == today and day_tasks:
                    bg_color = "#fef3c7"  # amber - today
                    border_color = "#f59e0b"
                    dot = "🟠"
                elif day_tasks:
                    bg_color = "#dcfce7"  # green - upcoming
                    border_color = "#22c55e"
                    dot = "🟢"
                elif cell_date == today:
                    bg_color = "#e0f2fe"  # light blue - today no tasks
                    border_color = "#3b82f6"
                    dot = ""
                else:
                    bg_color = "#f8fafc"
                    border_color = "#e2e8f0"
                    dot = ""

                task_count_str = f"{dot} {len(day_tasks)}" if day_tasks else ""
                # Build task summary (max 2 shown)
                task_lines = ""
                for tk in day_tasks[:2]:
                    task_lines += f"<div style='font-size:0.6rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{tk.get('client','')[:10]} - {tk.get('type','')}</div>"
                if len(day_tasks) > 2:
                    task_lines += f"<div style='font-size:0.55rem;color:#64748b;'>+{len(day_tasks)-2} more</div>"

                st.markdown(
                    f"""<div style='background:{bg_color};border:1px solid {border_color};
                    border-radius:6px;padding:4px;min-height:70px;'>
                    <div style='display:flex;justify-content:space-between;'>
                        <span style='font-weight:700;font-size:0.8rem;'>{day_num}</span>
                        <span style='font-size:0.65rem;'>{task_count_str}</span>
                    </div>
                    {task_lines}
                    </div>""",
                    unsafe_allow_html=True
                )

    # Task detail for selected date
    st.markdown("---")
    st.subheader("📋 Tasks for Selected Date")
    sel_date = st.date_input("Select date to view tasks", value=today, key="cal_sel_date")
    date_tasks = task_by_date.get(sel_date, [])
    if date_tasks:
        for t in date_tasks:
            prio = t.get("priority", "Medium")
            prio_icon = "🔴" if prio == "High" else ("🟡" if prio == "Medium" else "🟢")
            st.markdown(
                f"{prio_icon} **{t.get('client', 'N/A')}** — {t.get('type', '')} | "
                f"Due: {t.get('due_date', '')} | Note: {t.get('note', '-')}"
            )
    else:
        st.info(f"No tasks scheduled for {sel_date.strftime('%d %b %Y')}.")

    # Monthly summary metrics
    st.markdown("---")
    st.subheader("📊 Month Summary")
    month_start = datetime.date(selected_year, selected_month, 1)
    if selected_month == 12:
        month_end = datetime.date(selected_year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        month_end = datetime.date(selected_year, selected_month + 1, 1) - datetime.timedelta(days=1)

    month_tasks = []
    for d, tlist in task_by_date.items():
        if month_start <= d <= month_end:
            month_tasks.extend(tlist)

    ms1, ms2, ms3, ms4 = st.columns(4)
    overdue_count = sum(1 for d, tl in task_by_date.items() if month_start <= d <= month_end and d < today for _ in tl)
    upcoming_count = sum(1 for d, tl in task_by_date.items() if month_start <= d <= month_end and d > today for _ in tl)
    today_count = len(task_by_date.get(today, [])) if month_start <= today <= month_end else 0
    ms1.metric("Total This Month", len(month_tasks))
    ms2.metric("Overdue", overdue_count)
    ms3.metric("Due Today", today_count)
    ms4.metric("Upcoming", upcoming_count)
