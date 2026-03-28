import streamlit as st
import datetime
import calendar

from sales_calendar import (
    CITY_SEASONS, get_season_status, get_holidays_for_month,
    get_sundays, get_yearly_overview, get_city_remarks,
    MONTH_NAMES, STATE_HOLIDAYS, MAJOR_FESTIVALS_2026
)
from distance_matrix import CITY_STATE_MAP, ALL_STATES, get_cities_by_state


def render():
    _today_str = datetime.date.today().strftime("%d %b %Y")
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            border-bottom:2px solid var(--sandal,#e8dcc8);
            padding-bottom:6px;
            margin-bottom:10px;">
  <div style="display:flex;align-items:baseline;gap:10px;">
    <span style="font-size:1.08rem;font-weight:800;color:var(--navy,#1e3a5f);">📅 Sales Calendar</span>
    <span style="font-size:0.7rem;color:#64748b;font-weight:500;">Sales & Revenue</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-size:0.68rem;color:var(--steel-light,#64748b);">{_today_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.header("📅 Sales Calendar - Season & Holiday Planner")
    st.caption("Understand peak/off seasons, holidays, and best times to contact clients by city")

    # City/State Selection
    cal_col1, cal_col2, cal_col3 = st.columns([1, 1, 2])

    with cal_col1:
        cal_state = st.selectbox("📍 Select State", ["All States"] + ALL_STATES, key="cal_state")
        if cal_state == "All States":
            cal_cities = sorted(list(CITY_STATE_MAP.keys()))
        else:
            cal_cities = sorted(get_cities_by_state(cal_state))
        cal_city = st.selectbox("🏙️ Select City", cal_cities, key="cal_city")

    with cal_col2:
        # Get city state for holidays
        city_state = CITY_STATE_MAP.get(cal_city, "Gujarat")
        st.info(f"**State:** {city_state}")

        # Current month indicator
        today = datetime.date.today()
        current_season = get_season_status(cal_city, today.month)

        st.markdown(f"""
<div style="background-color:{current_season['color']}; color:white; padding:15px; border-radius:10px; text-align:center;">
<b style="font-size:1.3em;">Current Status</b><br>
<span style="font-size:1.5em;">{current_season['label']}</span>
</div>
""", unsafe_allow_html=True)

    with cal_col3:
        remarks = get_city_remarks(cal_city)
        if remarks:
            st.warning(f"📋 **Weather Note:** {remarks}")

    st.markdown("---")

    # YEARLY OVERVIEW - 12 Month Grid
    st.subheader(f"📊 Year 2026 - Season Overview for {cal_city}")

    yearly = get_yearly_overview(cal_city)

    # Create 12-month grid (4 columns x 3 rows)
    row1 = st.columns(4)
    row2 = st.columns(4)
    row3 = st.columns(4)

    all_rows = [row1, row2, row3]
    month_idx = 0

    for row in all_rows:
        for col in row:
            if month_idx < 12:
                m_data = yearly[month_idx]
                with col:
                    st.markdown(f"""
<div style="background-color:{m_data['color']}; color:white; padding:10px; border-radius:8px; text-align:center; margin:2px;">
<b>{m_data['month_name']}</b><br>
<small>{m_data['label'].replace('✅ ', '').replace('❌ ', '').replace('⚠️ ', '')}</small>
</div>
""", unsafe_allow_html=True)
                month_idx += 1

    st.markdown("---")

    # MONTHLY CALENDAR VIEW
    st.subheader("📆 Monthly Calendar View")

    month_cols = st.columns([1, 2, 1])
    with month_cols[1]:
        selected_month = st.selectbox("Select Month",
            options=list(range(1, 13)),
            format_func=lambda x: MONTH_NAMES[x],
            index=today.month - 1,
            key="cal_month"
        )

    year = 2026

    # Get calendar data
    cal_data = calendar.monthcalendar(year, selected_month)
    sundays = get_sundays(year, selected_month)
    holidays = get_holidays_for_month(year, selected_month, city_state)
    month_season = get_season_status(cal_city, selected_month)

    # Season banner
    st.markdown(f"""
<div style="background-color:{month_season['color']}; color:white; padding:10px; border-radius:8px; text-align:center; margin-bottom:10px;">
<b>{MONTH_NAMES[selected_month]} 2026</b> - {month_season['label']}
</div>
""", unsafe_allow_html=True)

    # Calendar grid with days
    st.markdown("##### 📅 Calendar")

    # Header row
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    header_cols = st.columns(7)
    for i, day_name in enumerate(day_names):
        bg = "#E74C3C" if day_name == "Sun" else "#2C3E50"
        header_cols[i].markdown(f"""
<div style="background-color:{bg}; color:white; padding:5px; text-align:center; border-radius:5px;">
<b>{day_name}</b>
</div>
        """, unsafe_allow_html=True)

    # Calendar weeks
    holiday_days = {h['date'].day: h['name'] for h in holidays}

    for week in cal_data:
        week_cols = st.columns(7)
        for i, day in enumerate(week):
            with week_cols[i]:
                if day == 0:
                    st.write("")
                else:
                    # Determine day color
                    is_sunday = (i == 6)
                    is_holiday = day in holiday_days

                    if is_sunday:
                        bg = "#E74C3C"
                        txt = "white"
                    elif is_holiday:
                        bg = "#9B59B6"
                        txt = "white"
                    else:
                        bg = "#ECF0F1"
                        txt = "#2C3E50"

                    holiday_indicator = "🎉" if is_holiday else ""

                    st.markdown(f"""
<div style="background-color:{bg}; color:{txt}; padding:8px; text-align:center; border-radius:5px; margin:1px; min-height:40px;">
<b>{day}</b> {holiday_indicator}
</div>
""", unsafe_allow_html=True)

    # Holidays List
    st.markdown("---")
    st.subheader(f"🎊 Holidays & Festivals in {MONTH_NAMES[selected_month]}")

    if holidays:
        for h in holidays:
            type_color = "#E74C3C" if h['type'] == 'national' else "#9B59B6" if h['type'] == 'festival' else "#3498DB"
            type_label = "🇮🇳 National" if h['type'] == 'national' else "🎉 Festival" if h['type'] == 'festival' else "🏛️ State"
            st.markdown(f"""
<div style="background-color:#FFF; border-left:4px solid {type_color}; padding:8px; margin:5px 0; border-radius:3px;">
<b>{h['date'].day} {MONTH_NAMES[selected_month]}</b> - {h['name']} <small>({type_label})</small>
</div>
""", unsafe_allow_html=True)
    else:
        st.info("No major holidays this month.")

    # UPCOMING IMPORTANT DATES
    st.markdown("---")
    st.subheader("📌 Upcoming Important Dates (Next 30 Days)")

    upcoming = []
    for m, d, name, duration in MAJOR_FESTIVALS_2026:
        festival_date = datetime.date(2026, m, d)
        days_until = (festival_date - today).days
        if 0 <= days_until <= 30:
            upcoming.append((days_until, f"{d} {MONTH_NAMES[m]}", name))

    if upcoming:
        for days, date_str, name in sorted(upcoming):
            urgency = "🔴" if days <= 7 else "🟡" if days <= 14 else "🟢"
            st.markdown(f"{urgency} **{date_str}** - {name} ({days} days away)")
    else:
        st.info("No major festivals in next 30 days.")

    # SALES TIPS
    st.markdown("---")
    st.subheader(f"💡 Sales Tips for {cal_city}")

    tips_col1, tips_col2 = st.columns(2)

    with tips_col1:
        st.markdown("**🎯 Best Time to Call:**")
        if month_season['status'] == 'peak':
            st.success("✅ NOW is ideal! High demand season.")
            st.caption("• Contractors actively placing orders")
            st.caption("• Follow up on pending quotes")
            st.caption("• Push for bulk orders")
        elif month_season['status'] == 'off':
            st.error("❌ Low demand period")
            st.caption("• Focus on relationship building")
            st.caption("• Discuss advance bookings for next season")
            st.caption("• Collect payments from previous orders")
        else:
            st.warning("⚠️ Moderate season")
            st.caption("• Good for quote discussions")
            st.caption("• Push urgent project orders")

    with tips_col2:
        st.markdown("**🗣️ Conversation Topics:**")
        # Check for upcoming festivals
        next_festival = None
        for m, d, name, duration in MAJOR_FESTIVALS_2026:
            fest_date = datetime.date(2026, m, d)
            if 0 < (fest_date - today).days <= 30:
                next_festival = name
                break

        if next_festival:
            st.info(f"🎉 Wish client for: **{next_festival}**")

        if city_state in STATE_HOLIDAYS and "holidays" in STATE_HOLIDAYS[city_state]:
            local_festivals = [f[2] for f in STATE_HOLIDAYS[city_state]["holidays"]]
            if local_festivals:
                st.caption(f"Local festivals to mention: {', '.join(local_festivals[:3])}")

        st.caption("• Ask about ongoing projects")
        st.caption("• Enquire about tender participation")
        st.caption("• Discuss competitor pricing if known")
