"""PPS Anantam — AI Learning Page: Learning dashboard from deal outcomes."""
import streamlit as st
import json
from pathlib import Path
try:
    import pandas as pd
except ImportError:
    pd = None
try:
    import plotly.graph_objects as go
except ImportError:
    go = None

ROOT = Path(__file__).parent.parent.parent


def _load_json_file(filename):
    """Load a JSON file from project root."""
    try:
        fpath = ROOT / filename
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def render():
    st.markdown('<div class="pps-page-header"><div class="pps-page-title">🤖 AI Learning</div></div>', unsafe_allow_html=True)
    st.info("AI learning engine — daily/weekly/monthly cycles that improve prediction accuracy over time.")

    try:
        from ai_learning_engine import AILearningEngine
        _ai_eng = AILearningEngine()
        engine_available = True
    except ImportError:
        _ai_eng, engine_available = None, False
        st.warning("AI Learning Engine not available. Showing data from JSON files.")

    # Load JSON data directly
    weights_data = _load_json_file("ai_learned_weights.json")
    log_data = _load_json_file("ai_learning_log.json")

    tabs = st.tabs(["📊 Model Status", "▶️ Run Learning", "📜 Learning History", "⚖️ Weights", "📈 Visualizations"])

    # ─── TAB 1: Model Status ───
    with tabs[0]:
        st.subheader("Model Accuracy")
        if engine_available:
            _acc = _ai_eng.get_model_accuracy()
            c1, c2, c3 = st.columns(3)
            c1.metric("Price Accuracy (7d)", f"{_acc.get('price_7d', 50)}%")
            c2.metric("Total Learning Cycles", _acc.get("total_cycles", 0))
            c3.metric("Last Updated", _acc.get("last_updated", "Never"))
        elif log_data and isinstance(log_data, list):
            # Derive from log data
            latest = log_data[-1] if log_data else {}
            acc_scores = latest.get("accuracy_scores", {})
            c1, c2, c3 = st.columns(3)
            c1.metric("Price Accuracy (7d)", f"{acc_scores.get('price_7d', 50)}%")
            c2.metric("Total Learning Cycles", len(log_data))
            c3.metric("Last Run", latest.get("run_date", "Never"))
        else:
            st.info("No model accuracy data available.")

        # Weights summary card
        if weights_data and isinstance(weights_data, dict):
            st.markdown("---")
            st.markdown("#### Current Weight Configuration")
            w1, w2 = st.columns([2, 1])
            with w1:
                weights = weights_data.get("weights", {})
                for wk, wv in weights.items():
                    label = wk.replace("_", " ").title()
                    st.progress(min(1.0, wv), text=f"{label}: {wv:.3f}")
            with w2:
                st.metric("Version", weights_data.get("version", "-"))
                st.metric("Updated At", weights_data.get("updated_at", "-"))

    # ─── TAB 2: Run Learning ───
    with tabs[1]:
        st.subheader("Manual Learning Trigger")
        if engine_available:
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Run Daily Learn", type="primary", use_container_width=True, key="ai_daily"):
                    result = _ai_eng.daily_learn()
                    st.json(result)
            with c2:
                if st.button("Run Weekly Learn", use_container_width=True, key="ai_weekly"):
                    result = _ai_eng.weekly_learn()
                    st.json(result)
            with c3:
                if st.button("Run Monthly Learn", use_container_width=True, key="ai_monthly"):
                    result = _ai_eng.monthly_learn()
                    st.json(result)
        else:
            st.info("AI Learning Engine not available. Learning triggers require the engine module.")

    # ─── TAB 3: Learning History ───
    with tabs[2]:
        st.subheader("Learning History")

        if engine_available:
            hist = _ai_eng.get_learning_history(limit=30)
        elif log_data and isinstance(log_data, list):
            hist = log_data[-30:]
        else:
            hist = []

        if hist and pd is not None:
            # Flatten history for table display
            rows = []
            for entry in hist:
                acc_scores = entry.get("accuracy_scores", {})
                preds = entry.get("predictions_evaluated", [])
                avg_error = 0
                if preds:
                    errors = [p.get("error_pct", 0) for p in preds if p.get("error_pct")]
                    avg_error = sum(errors) / len(errors) if errors else 0
                rows.append({
                    "Run Date": entry.get("run_date", ""),
                    "Cycle Type": entry.get("cycle_type", ""),
                    "Price Accuracy (7d)": f"{acc_scores.get('price_7d', '-')}%",
                    "Predictions Evaluated": len(preds),
                    "Avg Error %": f"{avg_error:.2f}%",
                    "Adjustments": len(entry.get("adjustments", [])),
                })
            df_hist = pd.DataFrame(rows)

            # Filters
            hf1, hf2 = st.columns([1, 3])
            with hf1:
                cycle_filter = st.selectbox("Cycle Type", ["All", "daily", "weekly", "monthly"], key="hist_cycle")
            if cycle_filter != "All":
                df_hist = df_hist[df_hist["Cycle Type"] == cycle_filter]

            st.dataframe(df_hist, use_container_width=True, hide_index=True)
        elif hist:
            st.json(hist[-5:])
        else:
            st.caption("No learning cycles recorded yet.")

    # ─── TAB 4: Weights ───
    with tabs[3]:
        st.subheader("Learned Factor Weights")

        if engine_available:
            weights = _ai_eng.get_learned_weights()
        elif weights_data and isinstance(weights_data, dict):
            weights = weights_data.get("weights", {})
        else:
            weights = {}

        if weights:
            for wk, wv in weights.items():
                label = wk.replace("_", " ").title()
                st.progress(min(1.0, wv), text=f"{label}: {wv:.3f}")

            # Comparison table: current vs initial defaults
            st.markdown("---")
            st.subheader("⚖️ Current vs Initial Weights")
            initial_weights = {
                "crude_trend": 0.30,
                "fx_trend": 0.20,
                "seasonal_pattern": 0.20,
                "refinery_utilization": 0.15,
                "import_volume": 0.15,
            }
            if pd is not None:
                comp_rows = []
                for key in set(list(weights.keys()) + list(initial_weights.keys())):
                    current = weights.get(key, 0)
                    initial = initial_weights.get(key, 0)
                    delta = current - initial
                    direction = "↑" if delta > 0 else ("↓" if delta < 0 else "=")
                    comp_rows.append({
                        "Factor": key.replace("_", " ").title(),
                        "Initial Weight": f"{initial:.3f}",
                        "Current Weight": f"{current:.3f}",
                        "Change": f"{direction} {abs(delta):.3f}",
                    })
                df_comp = pd.DataFrame(comp_rows)
                st.dataframe(df_comp, use_container_width=True, hide_index=True)

            # Weight sum validation
            total_w = sum(weights.values())
            if abs(total_w - 1.0) < 0.01:
                st.success(f"✅ Weights sum to {total_w:.3f} (valid)")
            else:
                st.warning(f"⚠️ Weights sum to {total_w:.3f} (expected 1.0)")
        else:
            st.info("No weight data available.")

    # ─── TAB 5: Visualizations ───
    with tabs[4]:
        st.subheader("📈 Learning Visualizations")

        if not log_data or not isinstance(log_data, list):
            st.info("No learning log data available for visualization.")
        elif go is None:
            st.warning("Plotly not available. Install plotly for interactive charts.")
        elif pd is None:
            st.warning("pandas not available for data processing.")
        else:
            # Parse log data for charts
            chart_rows = []
            for entry in log_data:
                acc = entry.get("accuracy_scores", {})
                preds = entry.get("predictions_evaluated", [])
                avg_error = 0
                if preds:
                    errors = [p.get("error_pct", 0) for p in preds if p.get("error_pct")]
                    avg_error = sum(errors) / len(errors) if errors else 0
                chart_rows.append({
                    "run_date": entry.get("run_date", ""),
                    "cycle_type": entry.get("cycle_type", ""),
                    "accuracy_7d": acc.get("price_7d", 50),
                    "avg_error": avg_error,
                    "preds_count": len(preds),
                })
            df_chart = pd.DataFrame(chart_rows)
            df_chart["run_date_parsed"] = pd.to_datetime(df_chart["run_date"], errors="coerce")
            df_chart = df_chart.dropna(subset=["run_date_parsed"]).sort_values("run_date_parsed")

            # Chart 1: Accuracy over time
            st.markdown("#### Accuracy Trend Over Time")
            fig_acc = go.Figure()
            fig_acc.add_trace(go.Scatter(
                x=df_chart["run_date_parsed"], y=df_chart["accuracy_7d"],
                mode="lines+markers", name="Price Accuracy (7d)",
                line=dict(color="#22c55e", width=2),
                marker=dict(size=5)
            ))
            fig_acc.add_hline(y=90, line_dash="dash", line_color="gray",
                              annotation_text="Target: 90%", annotation_position="top left")
            fig_acc.update_layout(
                title="7-Day Price Accuracy Over Learning Cycles",
                xaxis_title="Run Date", yaxis_title="Accuracy (%)",
                template="plotly_white", height=400,
                yaxis=dict(range=[0, 100])
            )
            st.plotly_chart(fig_acc, use_container_width=True)

            # Chart 2: Average error trend
            st.markdown("#### Prediction Error Trend")
            non_zero_errors = df_chart[df_chart["avg_error"] > 0]
            if not non_zero_errors.empty:
                fig_err = go.Figure()
                fig_err.add_trace(go.Scatter(
                    x=non_zero_errors["run_date_parsed"], y=non_zero_errors["avg_error"],
                    mode="lines+markers", name="Avg Error %",
                    line=dict(color="#ef4444", width=2),
                    fill="tozeroy", fillcolor="rgba(239,68,68,0.1)"
                ))
                fig_err.update_layout(
                    title="Average Prediction Error (%) Over Time",
                    xaxis_title="Run Date", yaxis_title="Error %",
                    template="plotly_white", height=350
                )
                st.plotly_chart(fig_err, use_container_width=True)
            else:
                st.caption("No prediction error data to chart.")

            # Chart 3: Weight visualization
            if weights_data and isinstance(weights_data, dict):
                st.markdown("#### Current Weight Distribution")
                w = weights_data.get("weights", {})
                if w:
                    labels = [k.replace("_", " ").title() for k in w.keys()]
                    values = list(w.values())
                    wc1, wc2 = st.columns(2)
                    with wc1:
                        fig_w_bar = go.Figure(go.Bar(
                            x=labels, y=values,
                            marker_color=["#1e3a5f", "#3b82f6", "#e8dcc8", "#f59e0b", "#22c55e"][:len(labels)],
                            text=[f"{v:.3f}" for v in values], textposition="auto"
                        ))
                        fig_w_bar.update_layout(
                            title="Factor Weights (Bar)",
                            template="plotly_white", height=350,
                            yaxis_title="Weight"
                        )
                        st.plotly_chart(fig_w_bar, use_container_width=True)
                    with wc2:
                        fig_w_pie = go.Figure(go.Pie(
                            labels=labels, values=values,
                            hole=0.4,
                            marker_colors=["#1e3a5f", "#3b82f6", "#e8dcc8", "#f59e0b", "#22c55e"][:len(labels)]
                        ))
                        fig_w_pie.update_layout(title="Factor Weights (Pie)", height=350)
                        st.plotly_chart(fig_w_pie, use_container_width=True)

                    # Cycle type distribution
            st.markdown("#### Learning Cycle Distribution")
            cycle_counts = df_chart["cycle_type"].value_counts()
            cols = st.columns(min(3, len(cycle_counts)))
            for idx, (ctype, cnt) in enumerate(cycle_counts.items()):
                cols[idx % len(cols)].metric(ctype.title(), cnt)
