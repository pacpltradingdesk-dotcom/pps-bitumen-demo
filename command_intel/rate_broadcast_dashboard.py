"""
PPS Anantam — Rate Broadcast Dashboard
=========================================
Send personalized bitumen rates via WhatsApp + Email.
Auto 9 AM daily + IOCL/HPCL revision trigger + Manual broadcast.
"""
import streamlit as st
import pandas as pd
import datetime
import json


def _get_contacts(city_filter=None, grade_filter=None, vip_filter=None):
    try:
        from rate_broadcast_engine import get_broadcast_contacts
        return get_broadcast_contacts(city_filter, grade_filter, vip_filter)
    except Exception:
        return []


def _get_all_contacts():
    try:
        from rate_broadcast_engine import get_broadcast_contacts
        return get_broadcast_contacts()
    except Exception:
        return []


def render():
    st.header("📡 Rate Broadcast Center")
    st.caption("Send personalized bitumen rates to customers via WhatsApp + Email.")

    tabs = st.tabs(["📡 Broadcast Now", "⏰ Schedule", "📊 History", "⚙️ Settings"])

    # ── Tab 1: Broadcast Now ──
    with tabs[0]:
        all_contacts = _get_all_contacts()

        # Get unique values for filters
        all_cities = sorted(set(c.get("city", "") for c in all_contacts if c.get("city")))
        all_grades = sorted(set(c.get("grade", "VG30") for c in all_contacts))
        all_vip = ["platinum", "gold", "silver", "standard"]

        st.subheader("Select Audience")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            city_sel = st.multiselect("Cities", ["All"] + all_cities, default=["All"], key="rb_city")
        with fc2:
            grade_sel = st.multiselect("Grades", ["All"] + all_grades, default=["All"], key="rb_grade")
        with fc3:
            vip_sel = st.multiselect("VIP Tier", ["All"] + all_vip, default=["All"], key="rb_vip")

        # Apply filters
        city_f = None if "All" in city_sel else city_sel
        grade_f = None if "All" in grade_sel else grade_sel
        vip_f = None if "All" in vip_sel else vip_sel

        filtered = _get_contacts(city_f, grade_f, vip_f)

        # Preview counts
        wa_count = sum(1 for c in filtered if c.get("phone") and c.get("wa_opted_in"))
        email_count = sum(1 for c in filtered if c.get("email") and "@" in c.get("email", ""))
        both_count = sum(1 for c in filtered if (c.get("phone") and c.get("wa_opted_in")) and (c.get("email") and "@" in c.get("email", "")))

        st.markdown("---")
        st.markdown("### Audience Preview")

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Total Recipients", len(filtered))
        p2.metric("WhatsApp", wa_count)
        p3.metric("Email", email_count)
        p4.metric("Both Channels", both_count)

        # VIP breakdown
        vip_counts = {}
        for c in filtered:
            tier = c.get("vip_tier", "standard")
            vip_counts[tier] = vip_counts.get(tier, 0) + 1

        if vip_counts:
            vip_text = " | ".join([f"{'👑' if t=='platinum' else '🥇' if t=='gold' else '🥈' if t=='silver' else '📋'} {t.title()}: {n}" for t, n in sorted(vip_counts.items())])
            st.caption(f"VIP Breakdown: {vip_text}")

        # Message preview — graphical WhatsApp bubble
        with st.expander("📝 Message Preview (first customer)", expanded=False):
            if filtered:
                sample = filtered[0]
                try:
                    from rate_broadcast_engine import calculate_personalized_rate, generate_wa_message
                    from components.message_preview import render_msg_preview
                    bulk = calculate_personalized_rate(sample.get("city", ""), sample.get("grade", "VG30"), "Bulk")
                    drum = calculate_personalized_rate(sample.get("city", ""), sample.get("grade", "VG30"), "Drum")
                    msg = generate_wa_message(sample, {"bulk": bulk, "drum": drum}, "manual")
                    render_msg_preview(msg, channel="whatsapp",
                                        sender=f"PPS Anantam → {sample.get('name', 'Customer')}")
                except Exception as e:
                    st.info(f"Preview not available: {e}")
            else:
                st.info("No contacts match filters.")

        # Send button
        st.markdown("")
        if len(filtered) > 0:
            bc1, bc2 = st.columns([3, 1])
            with bc1:
                confirm = st.checkbox(f"Confirm: Send to {len(filtered)} contacts via WhatsApp + Email", key="rb_confirm")
            with bc2:
                if st.button("🚀 Broadcast Now", type="primary", disabled=not confirm, use_container_width=True):
                    with st.spinner(f"Broadcasting to {len(filtered)} contacts..."):
                        try:
                            from rate_broadcast_engine import execute_broadcast
                            result = execute_broadcast(city_f, grade_f, vip_f, "manual")
                            st.success(f"""Broadcast Complete!
- Total: {result.get('total', 0)} contacts
- WhatsApp: {result.get('wa_sent', 0)} sent, {result.get('wa_failed', 0)} failed
- Email: {result.get('email_sent', 0)} sent, {result.get('email_failed', 0)} failed
- Broadcast ID: {result.get('broadcast_id', '')}""")
                        except Exception as e:
                            st.error(f"Broadcast failed: {e}")
        else:
            st.warning("No contacts match your filters. Adjust the segment selection.")

    # ── Tab 2: Schedule ──
    with tabs[1]:
        st.subheader("Automated Broadcasts")

        try:
            from settings_engine import get as gs, save as ss

            st.markdown("### ⏰ Daily Morning Broadcast")
            auto_morning = st.toggle("Enable 9 AM Daily Broadcast",
                                     value=gs("rate_broadcast_auto_morning", False), key="rb_auto_am")
            if auto_morning != gs("rate_broadcast_auto_morning", False):
                ss("rate_broadcast_auto_morning", auto_morning)
                if auto_morning:
                    try:
                        from rate_broadcast_engine import start_scheduler
                        start_scheduler()
                    except Exception:
                        pass
                    st.success("9 AM daily broadcast enabled!")
                else:
                    st.info("Daily broadcast disabled.")

            st.markdown("### ⚡ Price Revision Auto-Trigger")
            auto_revision = st.toggle("Auto-broadcast on IOCL/HPCL revision",
                                      value=gs("rate_broadcast_auto_revision", False), key="rb_auto_rev")
            if auto_revision != gs("rate_broadcast_auto_revision", False):
                ss("rate_broadcast_auto_revision", auto_revision)
                st.success("Price revision trigger " + ("enabled" if auto_revision else "disabled"))

            st.markdown("---")

            # Status
            st.markdown("### 📊 Scheduler Status")
            try:
                from rate_broadcast_engine import _scheduler_running
                status = "🟢 Running" if _scheduler_running else "🔴 Stopped"
                st.markdown(f"**Morning Scheduler:** {status}")
            except Exception:
                st.markdown("**Morning Scheduler:** Unknown")

            try:
                from rate_broadcast_engine import get_broadcast_history
                last = get_broadcast_history(limit=1)
                if last:
                    st.markdown(f"**Last Broadcast:** {last[0].get('created_at', 'Never')} | "
                               f"{last[0].get('trigger_type', '')} | "
                               f"{last[0].get('total_recipients', 0)} recipients")
                else:
                    st.markdown("**Last Broadcast:** Never")
            except Exception:
                pass

        except ImportError:
            st.info("Settings engine not available. Configure manually in settings.json.")

            auto_morning = st.toggle("Enable 9 AM Daily Broadcast", value=False, key="rb_auto_am2")
            auto_revision = st.toggle("Auto-broadcast on price revision", value=False, key="rb_auto_rev2")

    # ── Tab 3: History ──
    with tabs[2]:
        st.subheader("Broadcast History")

        try:
            from rate_broadcast_engine import get_broadcast_history
            history = get_broadcast_history(limit=50)
        except Exception:
            history = []

        if history:
            # Summary KPIs
            total_broadcasts = len(history)
            total_wa = sum(h.get("wa_sent", 0) for h in history)
            total_email = sum(h.get("email_sent", 0) for h in history)
            total_recipients = sum(h.get("total_recipients", 0) for h in history)

            h1, h2, h3, h4 = st.columns(4)
            h1.metric("Total Broadcasts", total_broadcasts)
            h2.metric("WA Messages Sent", f"{total_wa:,}")
            h3.metric("Emails Sent", f"{total_email:,}")
            h4.metric("Total Reached", f"{total_recipients:,}")

            st.markdown("---")

            # Filter
            trigger_filter = st.selectbox("Filter by Trigger", ["All", "manual", "scheduled", "price_revision"], key="rb_hist_f")
            filtered_hist = history if trigger_filter == "All" else [h for h in history if h.get("trigger_type") == trigger_filter]

            df = pd.DataFrame(filtered_hist)
            display_cols = [c for c in ["broadcast_id", "trigger_type", "total_recipients",
                                        "wa_sent", "wa_failed", "email_sent", "email_failed",
                                        "status", "created_at"] if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=400)
        else:
            st.info("No broadcast history yet. Send your first broadcast from the 'Broadcast Now' tab.")

    # ── Tab 4: Settings ──
    with tabs[3]:
        st.subheader("Broadcast Settings")

        try:
            from settings_engine import get as gs, save as ss

            st.markdown("### Rate Limits")
            sc1, sc2 = st.columns(2)
            with sc1:
                wa_limit = st.number_input("WhatsApp/min", value=gs("whatsapp_rate_limit_per_minute", 20),
                                           min_value=1, max_value=100, key="rb_wa_lim")
            with sc2:
                email_limit = st.number_input("Email/hour", value=gs("email_rate_limit_per_hour", 50),
                                              min_value=1, max_value=500, key="rb_em_lim")

            st.markdown("### VIP Stagger (minutes between tiers)")
            vc1, vc2, vc3 = st.columns(3)
            with vc1:
                gold_gap = st.number_input("Gold delay (min)", value=gs("rb_gold_gap", 1),
                                           min_value=0, max_value=30, key="rb_gold")
            with vc2:
                silver_gap = st.number_input("Silver delay (min)", value=gs("rb_silver_gap", 2),
                                             min_value=0, max_value=30, key="rb_silver")
            with vc3:
                std_gap = st.number_input("Standard delay (min)", value=gs("rb_std_gap", 3),
                                          min_value=0, max_value=30, key="rb_std")

            st.markdown("### Test Mode")
            test_mode = st.toggle("Test Mode (send only to self)", value=gs("rb_test_mode", False), key="rb_test")
            if test_mode:
                test_phone = st.text_input("Your WhatsApp number", value=gs("rb_test_phone", "+91 9969562424"), key="rb_tph")
                test_email = st.text_input("Your Email", value=gs("rb_test_email", "princepshah20@gmail.com"), key="rb_tem")

            if st.button("Save Settings", type="primary"):
                ss("whatsapp_rate_limit_per_minute", wa_limit)
                ss("email_rate_limit_per_hour", email_limit)
                ss("rb_gold_gap", gold_gap)
                ss("rb_silver_gap", silver_gap)
                ss("rb_std_gap", std_gap)
                ss("rb_test_mode", test_mode)
                if test_mode:
                    ss("rb_test_phone", test_phone)
                    ss("rb_test_email", test_email)
                st.success("Settings saved!")

        except ImportError:
            st.info("Settings engine not available. Using defaults.")

            st.markdown("**Default Rate Limits:**")
            st.markdown("- WhatsApp: 20/min, 1000/day")
            st.markdown("- Email: 50/hr")
            st.markdown("- VIP Stagger: Platinum→0, Gold→1min, Silver→2min, Standard→3min")
