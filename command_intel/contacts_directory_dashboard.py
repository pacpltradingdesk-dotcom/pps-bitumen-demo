"""
PPS Anantam — Contacts Directory Dashboard
=============================================
Browse 25K+ business contacts with search, filter, export, and bulk import.
"""
import streamlit as st
import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _load_contacts():
    """Load contacts from JSON file, fallback to database."""
    contacts = []
    try:
        cf = ROOT / "tbl_contacts.json"
        if cf.exists():
            with open(cf, "r", encoding="utf-8") as f:
                contacts = json.load(f)
    except Exception:
        pass
    if not contacts:
        try:
            from database import get_all_contacts
            contacts = get_all_contacts()
        except Exception:
            pass
    return contacts


def render():
    st.header("📱 Contacts Directory")
    st.caption("Browse, search, and manage business contacts.")

    contacts = _load_contacts()

    # ── KPI Row ──
    cities = set(c.get("city", "") for c in contacts if c.get("city"))
    states = set(c.get("state", "") for c in contacts if c.get("state"))
    categories = sorted(set(c.get("category", "General") for c in contacts if c.get("category")))
    with_phone = sum(1 for c in contacts if c.get("contact") or c.get("phone") or c.get("whatsapp"))

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Contacts", f"{len(contacts):,}")
    k2.metric("States", len(states))
    k3.metric("Cities", len(cities))
    k4.metric("With Phone", f"{with_phone:,}")

    st.markdown("---")

    tabs = st.tabs(["📋 Directory", "📥 Import", "📊 Analytics"])

    # ── Tab 1: Directory ──
    with tabs[0]:
        # Search & filters
        fc1, fc2, fc3 = st.columns([3, 1, 1])
        with fc1:
            search = st.text_input("Search", placeholder="Name, company, city, phone...", key="cd_search")
        with fc2:
            cat_filter = st.selectbox("Category", ["All"] + categories, key="cd_cat")
        with fc3:
            state_list = sorted(states) if states else []
            state_filter = st.selectbox("State", ["All"] + state_list, key="cd_state")

        # Apply filters
        filtered = contacts
        if search:
            q = search.lower()
            filtered = [c for c in filtered if q in json.dumps(c, default=str).lower()]
        if cat_filter != "All":
            filtered = [c for c in filtered if c.get("category") == cat_filter]
        if state_filter != "All":
            filtered = [c for c in filtered if c.get("state") == state_filter]

        st.caption(f"Showing {len(filtered):,} of {len(contacts):,} contacts")

        # Display
        if filtered:
            df = pd.DataFrame(filtered[:500])
            display_cols = [c for c in ["name", "category", "city", "state", "contact", "gstin", "type"] if c in df.columns]
            if display_cols:
                st.dataframe(df[display_cols], use_container_width=True, hide_index=True, height=450)
            else:
                st.dataframe(df, use_container_width=True, hide_index=True, height=450)

            if len(filtered) > 500:
                st.warning(f"Showing first 500 of {len(filtered):,}. Use search to narrow down.")

            # ── Set Active Customer from this list ─────────────────────
            st.markdown("##### 🎯 Set Active Customer")
            st.caption("Kisi ek contact ko 'Active' banao — uska data Pricing Calc, Comm Hub, CRM sab pe auto-fill ho jayega.")
            _names = [c.get("name", "") for c in filtered[:500] if c.get("name")]
            if _names:
                _pick = st.selectbox("Contact chuno", ["(select)"] + _names, key="_pick_active_contact")
                if _pick and _pick != "(select)":
                    _c = next((c for c in filtered if c.get("name") == _pick), None)
                    if _c and st.button(f"Set '{_pick}' as Active",
                                         key="_set_active_contact_btn",
                                         type="primary", use_container_width=True):
                        try:
                            from navigation_engine import set_active_customer
                            set_active_customer(
                                name=_c.get("name", ""),
                                phone=str(_c.get("contact", "") or ""),
                                city=_c.get("city", "") or "",
                                state=_c.get("state", "") or "",
                                category=_c.get("category", "") or "",
                            )
                            st.success(f"✅ Active: {_c['name']} — ab har page pe yeh customer pre-filled hoga.")
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Failed: {_e}")

            # Export
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                full_df = pd.DataFrame(filtered)
                csv = full_df.to_csv(index=False)
                st.download_button("📥 Export CSV", data=csv,
                                   file_name="pps_contacts_export.csv", mime="text/csv",
                                   use_container_width=True)
            with exp_col2:
                json_str = json.dumps(filtered, indent=2, default=str)
                st.download_button("📥 Export JSON", data=json_str,
                                   file_name="pps_contacts_export.json", mime="application/json",
                                   use_container_width=True)
        else:
            st.info("No contacts match your search criteria.")

    # ── Tab 2: Import ──
    with tabs[1]:
        st.subheader("Bulk Import Contacts")
        st.info("Upload Excel or CSV file with columns: name, category, city, state, contact, gstin")

        uploaded = st.file_uploader("Upload contacts file", type=["xlsx", "csv"], key="cd_import")
        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    new_df = pd.read_csv(uploaded)
                else:
                    new_df = pd.read_excel(uploaded)

                st.success(f"Loaded {len(new_df)} rows from {uploaded.name}")
                st.dataframe(new_df.head(10), use_container_width=True, hide_index=True)

                # Column mapping
                expected_cols = ["name", "category", "city", "state", "contact", "gstin"]
                missing = [c for c in expected_cols if c not in new_df.columns]
                if missing:
                    st.warning(f"Missing columns: {', '.join(missing)}. Available: {', '.join(new_df.columns.tolist())}")

                if st.button("Import Contacts", type="primary"):
                    import datetime
                    new_records = new_df.to_dict("records")
                    for r in new_records:
                        r["imported_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        r["source"] = f"import_{uploaded.name}"

                    existing = _load_contacts()
                    merged = existing + new_records
                    cf = ROOT / "tbl_contacts.json"
                    with open(cf, "w", encoding="utf-8") as f:
                        json.dump(merged, f, indent=2, default=str)
                    st.success(f"Imported {len(new_records)} contacts. Total: {len(merged)}")
                    st.rerun()

            except Exception as e:
                st.error(f"Import failed: {e}")

    # ── Tab 3: Analytics ──
    with tabs[2]:
        st.subheader("Contact Analytics")
        if contacts:
            # Category breakdown
            cat_counts = {}
            for c in contacts:
                cat = c.get("category", "Unknown")
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            import plotly.express as px

            c1, c2 = st.columns(2)
            with c1:
                cat_df = pd.DataFrame(list(cat_counts.items()), columns=["Category", "Count"])
                cat_df = cat_df.sort_values("Count", ascending=False)
                fig = px.bar(cat_df, x="Category", y="Count", title="Contacts by Category",
                             color="Count", color_continuous_scale="Blues")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                state_counts = {}
                for c in contacts:
                    s = c.get("state", "Unknown")
                    if s:
                        state_counts[s] = state_counts.get(s, 0) + 1
                state_df = pd.DataFrame(list(state_counts.items()), columns=["State", "Count"])
                state_df = state_df.sort_values("Count", ascending=False).head(15)
                fig = px.bar(state_df, x="State", y="Count", title="Top 15 States",
                             color="Count", color_continuous_scale="Greens")
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            # City breakdown
            city_counts = {}
            for c in contacts:
                ct = c.get("city", "Unknown")
                if ct:
                    city_counts[ct] = city_counts.get(ct, 0) + 1
            city_df = pd.DataFrame(list(city_counts.items()), columns=["City", "Count"])
            city_df = city_df.sort_values("Count", ascending=False).head(20)
            fig = px.bar(city_df, x="City", y="Count", title="Top 20 Cities",
                         color="Count", color_continuous_scale="Purples")
            fig.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No contacts data available for analytics.")
