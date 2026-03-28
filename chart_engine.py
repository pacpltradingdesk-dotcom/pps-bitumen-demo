"""
PPS Anantam — Chart Engine v1.0
================================
Plotly chart generator for all dashboard visualizations.
Uses Vastu Design System color palette.
All charts are Streamlit-compatible (use st.plotly_chart).
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Vastu Design System — colour palette
# ---------------------------------------------------------------------------
VASTU_COLORS = {
    'navy':     '#1e3a5f',
    'navy_mid': '#2c4f7c',
    'green':    '#2d6a4f',
    'gold':     '#c9a84c',
    'fire':     '#b85c38',
    'earth':    '#8c6d46',
    'ivory':    '#faf7f2',
    'cream':    '#f0ebe1',
    'success':  '#22c55e',
    'warning':  '#f59e0b',
    'error':    '#f43f5e',
    'info':     '#3b82f6',
}

# Ordered multi-colour sequence for charts that need several distinct colours
_VASTU_SEQUENCE = [
    VASTU_COLORS['navy'],
    VASTU_COLORS['fire'],
    VASTU_COLORS['green'],
    VASTU_COLORS['gold'],
    VASTU_COLORS['earth'],
    VASTU_COLORS['navy_mid'],
    VASTU_COLORS['info'],
    VASTU_COLORS['success'],
    VASTU_COLORS['warning'],
    VASTU_COLORS['error'],
]

# Shared font stack
_FONT_FAMILY = "Inter, Segoe UI, Roboto, Helvetica Neue, Arial, sans-serif"


# ---------------------------------------------------------------------------
# Helper — Indian comma format  (e.g. 1,23,456.00)
# ---------------------------------------------------------------------------
def _format_inr(amount, decimals: int = 2, symbol: bool = True) -> str:
    """Return *amount* in Indian numbering format with optional rupee symbol.

    Examples
    --------
    >>> _format_inr(123456.5)
    '₹1,23,456.50'
    >>> _format_inr(9500, decimals=0, symbol=False)
    '9,500'
    """
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return str(amount)

    is_negative = amount < 0
    amount = abs(amount)

    if decimals > 0:
        fmt = f"{amount:.{decimals}f}"
    else:
        fmt = f"{int(round(amount))}"

    parts = fmt.split(".")
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""

    # Indian grouping: last three digits, then groups of two
    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while remaining:
            groups.append(remaining[-2:])
            remaining = remaining[:-2]
        groups.reverse()
        integer_part = ",".join(groups) + "," + last_three
    # else: leave as-is for numbers <= 999

    result = integer_part
    if decimal_part:
        result += "." + decimal_part

    if is_negative:
        result = "-" + result
    if symbol:
        result = "\u20b9" + result          # ₹ prefix

    return result


# ═══════════════════════════════════════════════════════════════════════════
# ChartEngine
# ═══════════════════════════════════════════════════════════════════════════
class ChartEngine:
    """Centralised Plotly chart factory for the Bitumen Sales Dashboard.

    Usage
    -----
    >>> engine = ChartEngine()
    >>> fig = engine.price_trend_chart(price_data, days=30)
    >>> st.plotly_chart(fig, use_container_width=True)
    """

    # ------------------------------------------------------------------
    # Internal: apply Vastu Design System theme to any figure
    # ------------------------------------------------------------------
    @staticmethod
    def _apply_vastu_theme(fig: go.Figure, height: int | None = None) -> go.Figure:
        """Apply standard Vastu Design System styling to a Plotly figure.

        * Transparent / ivory backgrounds
        * Inter / Segoe UI font
        * Responsive auto-size
        * Minimal grid lines
        """
        layout_kwargs: dict = dict(
            font=dict(family=_FONT_FAMILY, color=VASTU_COLORS['navy']),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=30, t=50, b=40),
            autosize=True,
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor=VASTU_COLORS['ivory'],
                font_size=12,
                font_family=_FONT_FAMILY,
                font_color=VASTU_COLORS['navy'],
                bordercolor=VASTU_COLORS['cream'],
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                bordercolor=VASTU_COLORS['cream'],
                borderwidth=1,
                font=dict(size=11),
            ),
        )
        if height is not None:
            layout_kwargs["height"] = height

        fig.update_layout(**layout_kwargs)

        # Light grid lines on both axes
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(30,58,95,0.08)",
            zeroline=False,
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor="rgba(30,58,95,0.08)",
            zeroline=False,
        )
        return fig

    # ------------------------------------------------------------------
    # 1. Price Trend Chart — dual Y-axis (Brent/WTI + VG30)
    # ------------------------------------------------------------------
    def price_trend_chart(self, price_data: list, days: int = 30) -> go.Figure:
        """Dual Y-axis line chart: Brent / WTI (USD/bbl) on the left,
        VG30 (INR/MT) on the right.

        Parameters
        ----------
        price_data : list[dict]
            Each record must have keys ``date_time``, ``benchmark``
            (one of 'Brent', 'WTI', 'VG30'), and ``price``.
        days : int
            Number of trailing days to display (default 30).

        Returns
        -------
        go.Figure
        """
        # ---- filter by date window -----------------------------------
        cutoff = datetime.utcnow() - timedelta(days=days)
        filtered: list[dict] = []
        for rec in price_data:
            dt_raw = rec.get("date_time", "")
            try:
                if isinstance(dt_raw, str):
                    dt = datetime.fromisoformat(dt_raw.replace("Z", "+00:00"))
                else:
                    dt = dt_raw
                if dt.replace(tzinfo=None) >= cutoff:
                    filtered.append({**rec, "_dt": dt})
            except Exception:
                filtered.append({**rec, "_dt": datetime.utcnow()})

        # ---- bucket by benchmark ------------------------------------
        benchmarks: dict[str, tuple[list, list]] = {}
        for rec in filtered:
            bm = rec.get("benchmark", "Unknown")
            benchmarks.setdefault(bm, ([], []))
            benchmarks[bm][0].append(rec["_dt"])
            benchmarks[bm][1].append(rec.get("price", 0))

        fig = make_subplots(specs=[[{"secondary_y": True}]])

        colour_map = {
            "Brent": VASTU_COLORS['navy'],
            "WTI":   VASTU_COLORS['fire'],
            "VG30":  VASTU_COLORS['green'],
        }

        for bm, (dates, prices) in benchmarks.items():
            is_vg30 = bm.upper() == "VG30"
            colour = colour_map.get(bm, VASTU_COLORS['navy_mid'])
            hover_tpl = (
                f"<b>{bm}</b><br>"
                + ("₹%{y:,.0f} /MT" if is_vg30 else "$%{y:.2f} /bbl")
                + "<br>%{x|%d-%b-%Y}<extra></extra>"
            )
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=prices,
                    name=bm,
                    mode="lines+markers",
                    marker=dict(size=5, color=colour),
                    line=dict(width=2, color=colour),
                    hovertemplate=hover_tpl,
                ),
                secondary_y=is_vg30,
            )

        fig.update_yaxes(
            title_text="USD / bbl",
            secondary_y=False,
            tickprefix="$",
            tickformat=",.2f",
        )
        fig.update_yaxes(
            title_text="INR / MT",
            secondary_y=True,
            tickprefix="\u20b9",
            tickformat=",",
        )
        fig.update_xaxes(title_text="Date", tickformat="%d-%b")
        fig.update_layout(
            title=dict(
                text=f"Price Trend — Last {days} Days",
                font=dict(size=16, color=VASTU_COLORS['navy']),
            ),
        )
        self._apply_vastu_theme(fig, height=420)
        return fig

    # ------------------------------------------------------------------
    # 2. Demand Heatmap — India (fallback: horizontal bar)
    # ------------------------------------------------------------------
    def demand_heatmap_india(self, state_data: dict) -> go.Figure:
        """India state-level demand visualisation.

        Attempts a choropleth first; falls back to a sorted horizontal bar
        chart when the GeoJSON for Indian states is unavailable.

        Parameters
        ----------
        state_data : dict
            ``{state_name: demand_mt}`` mapping.

        Returns
        -------
        go.Figure
        """
        if not state_data:
            fig = go.Figure()
            fig.add_annotation(text="No demand data available", showarrow=False)
            self._apply_vastu_theme(fig, height=300)
            return fig

        # --- try choropleth ------------------------------------------
        geojson_url = (
            "https://gist.githubusercontent.com/jbrobst/"
            "56c13bbbf9d97d187fea01ca62ea5112/raw/"
            "e388c4cae20aa53cb5090210a42ebb9b765c0a36/"
            "india_states.geojson"
        )
        try:
            import requests
            resp = requests.get(geojson_url, timeout=5)
            resp.raise_for_status()
            geojson = resp.json()

            states = list(state_data.keys())
            demands = [state_data[s] for s in states]
            fig = px.choropleth(
                locations=states,
                color=demands,
                geojson=geojson,
                featureidkey="properties.ST_NM",
                color_continuous_scale=[
                    [0.0, VASTU_COLORS['ivory']],
                    [0.5, VASTU_COLORS['gold']],
                    [1.0, VASTU_COLORS['green']],
                ],
                labels={"locations": "State", "color": "Demand (MT)"},
            )
            fig.update_geos(
                fitbounds="locations",
                visible=False,
            )
            fig.update_layout(
                title=dict(
                    text="Bitumen Demand by State (MT)",
                    font=dict(size=16, color=VASTU_COLORS['navy']),
                ),
                coloraxis_colorbar=dict(
                    title="MT",
                    tickformat=",",
                ),
            )
            self._apply_vastu_theme(fig, height=520)
            return fig

        except Exception:
            pass    # fall through to bar chart

        # --- fallback: horizontal bar chart ---------------------------
        return self._demand_bar_fallback(state_data)

    def _demand_bar_fallback(self, state_data: dict) -> go.Figure:
        """Sorted horizontal bar chart used when choropleth is unavailable."""
        sorted_items = sorted(state_data.items(), key=lambda x: x[1])
        states = [s for s, _ in sorted_items]
        demands = [d for _, d in sorted_items]

        # Continuous colour mapping from ivory (low) to green (high)
        max_demand = max(demands) if demands else 1
        bar_colors = []
        for d in demands:
            ratio = d / max_demand
            # Interpolate between ivory (#faf7f2) and green (#2d6a4f)
            r = int(250 + (45 - 250) * ratio)
            g = int(247 + (106 - 247) * ratio)
            b = int(242 + (79 - 242) * ratio)
            bar_colors.append(f"rgb({r},{g},{b})")

        fig = go.Figure(
            go.Bar(
                y=states,
                x=demands,
                orientation="h",
                marker=dict(color=bar_colors, line=dict(width=0)),
                hovertemplate="<b>%{y}</b><br>Demand: %{x:,.0f} MT<extra></extra>",
            )
        )
        fig.update_layout(
            title=dict(
                text="Bitumen Demand by State (MT)",
                font=dict(size=16, color=VASTU_COLORS['navy']),
            ),
            xaxis_title="Demand (MT)",
            yaxis_title="",
        )
        self._apply_vastu_theme(fig, height=max(350, len(states) * 28 + 80))
        return fig

    # ------------------------------------------------------------------
    # 3. Margin Waterfall Chart
    # ------------------------------------------------------------------
    def margin_waterfall_chart(self, breakdown: dict) -> go.Figure:
        """Waterfall showing cost build-up from FOB to Sell Price.

        Parameters
        ----------
        breakdown : dict
            Expected keys (all values in INR):
            ``fob``, ``freight``, ``insurance``, ``port_charges``,
            ``customs_duty``, ``gst``, ``margin``.
            The method auto-computes *Landed Cost* and *Sell Price* totals.

        Returns
        -------
        go.Figure
        """
        fob        = breakdown.get("fob", 0)
        freight    = breakdown.get("freight", 0)
        insurance  = breakdown.get("insurance", 0)
        port       = breakdown.get("port_charges", 0)
        customs    = breakdown.get("customs_duty", 0)
        gst        = breakdown.get("gst", 0)
        margin     = breakdown.get("margin", 0)

        landed = fob + freight + insurance + port + customs + gst
        sell_price = landed + margin

        labels = [
            "FOB Price",
            "Freight",
            "Insurance",
            "Port Charges",
            "Customs Duty",
            "GST (18%)",
            "Landed Cost",
            "Margin",
            "Sell Price",
        ]
        values = [fob, freight, insurance, port, customs, gst, landed, margin, sell_price]
        measures = [
            "absolute",     # FOB
            "relative",     # Freight
            "relative",     # Insurance
            "relative",     # Port
            "relative",     # Customs
            "relative",     # GST
            "total",        # Landed
            "relative",     # Margin
            "total",        # Sell Price
        ]

        # Colour: green for base (FOB), fire for cost add-ons, gold for totals
        marker_colors = [
            VASTU_COLORS['green'],    # FOB
            VASTU_COLORS['fire'],     # Freight
            VASTU_COLORS['fire'],     # Insurance
            VASTU_COLORS['fire'],     # Port
            VASTU_COLORS['fire'],     # Customs
            VASTU_COLORS['fire'],     # GST
            VASTU_COLORS['navy'],     # Landed (subtotal)
            VASTU_COLORS['green'],    # Margin
            VASTU_COLORS['gold'],     # Sell Price
        ]

        text_labels = [_format_inr(v, decimals=0) for v in values]

        fig = go.Figure(
            go.Waterfall(
                orientation="v",
                x=labels,
                y=values,
                measure=measures,
                text=text_labels,
                textposition="outside",
                textfont=dict(size=11, family=_FONT_FAMILY),
                connector=dict(line=dict(color=VASTU_COLORS['cream'], width=1)),
                increasing=dict(marker=dict(color=VASTU_COLORS['fire'])),
                decreasing=dict(marker=dict(color=VASTU_COLORS['green'])),
                totals=dict(marker=dict(color=VASTU_COLORS['gold'])),
            )
        )
        # Override individual bar colours (waterfall does not natively support per-bar)
        fig.data[0].connector.line.color = VASTU_COLORS['cream']

        fig.update_layout(
            title=dict(
                text="Cost Build-up: FOB to Sell Price",
                font=dict(size=16, color=VASTU_COLORS['navy']),
            ),
            yaxis_title="Amount (INR)",
            yaxis_tickprefix="\u20b9",
            yaxis_tickformat=",",
            showlegend=False,
        )
        self._apply_vastu_theme(fig, height=450)
        return fig

    # ------------------------------------------------------------------
    # 4. Source Comparison — Stacked Horizontal Bar
    # ------------------------------------------------------------------
    def source_comparison_bar(self, sources: list, destination: str) -> go.Figure:
        """Stacked horizontal bar chart ranking supply sources by landed cost.

        Parameters
        ----------
        sources : list[dict]
            Each dict: ``{source, landed_cost, base_price, freight}``.
            GST is computed as ``landed_cost - base_price - freight``.
        destination : str
            Name shown in title.

        Returns
        -------
        go.Figure
        """
        if not sources:
            fig = go.Figure()
            fig.add_annotation(text="No source data available", showarrow=False)
            self._apply_vastu_theme(fig, height=300)
            return fig

        # Sort descending so the cheapest ends up at the top of the plot
        sorted_src = sorted(sources, key=lambda s: s.get("landed_cost", 0), reverse=True)

        names = [s["source"] for s in sorted_src]
        base_prices = [s.get("base_price", 0) for s in sorted_src]
        freights = [s.get("freight", 0) for s in sorted_src]
        gsts = [
            max(0, s.get("landed_cost", 0) - s.get("base_price", 0) - s.get("freight", 0))
            for s in sorted_src
        ]
        landed = [s.get("landed_cost", 0) for s in sorted_src]

        # Cheapest source (now last in sorted list = top bar)
        cheapest_idx = len(sorted_src) - 1

        # Per-bar colours — highlight cheapest in green
        base_colors = [
            VASTU_COLORS['success'] if i == cheapest_idx else VASTU_COLORS['navy']
            for i in range(len(sorted_src))
        ]
        freight_colors = [
            VASTU_COLORS['success'] if i == cheapest_idx else VASTU_COLORS['earth']
            for i in range(len(sorted_src))
        ]
        gst_colors = [
            VASTU_COLORS['success'] if i == cheapest_idx else VASTU_COLORS['gold']
            for i in range(len(sorted_src))
        ]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=names, x=base_prices, name="Base Price",
            orientation="h",
            marker=dict(color=base_colors),
            hovertemplate="Base: %{x:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            y=names, x=freights, name="Freight",
            orientation="h",
            marker=dict(color=freight_colors),
            hovertemplate="Freight: %{x:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            y=names, x=gsts, name="GST & Duties",
            orientation="h",
            marker=dict(color=gst_colors),
            hovertemplate="GST/Duties: %{x:,.0f}<extra></extra>",
        ))

        # Landed-cost annotation at end of each bar
        for i, (name, cost) in enumerate(zip(names, landed)):
            fig.add_annotation(
                x=cost,
                y=name,
                text=_format_inr(cost, decimals=0),
                showarrow=False,
                xanchor="left",
                xshift=6,
                font=dict(size=10, color=VASTU_COLORS['navy']),
            )

        fig.update_layout(
            barmode="stack",
            title=dict(
                text=f"Source Comparison — Landed Cost at {destination}",
                font=dict(size=16, color=VASTU_COLORS['navy']),
            ),
            xaxis_title="Cost (INR / MT)",
            xaxis_tickprefix="\u20b9",
            xaxis_tickformat=",",
            yaxis_title="",
            legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
        )
        self._apply_vastu_theme(fig, height=max(320, len(sources) * 40 + 100))
        return fig

    # ------------------------------------------------------------------
    # 5. Pipeline Funnel
    # ------------------------------------------------------------------
    def pipeline_funnel(self, stage_counts: dict) -> go.Figure:
        """Sales pipeline funnel chart.

        Parameters
        ----------
        stage_counts : dict
            ``{stage_name: count}`` — ordered from widest to narrowest.
            Typical stages: Enquiry, Quoted, Negotiation, PO, Dispatch,
            Delivered, Payment, Closed.

        Returns
        -------
        go.Figure
        """
        # Canonical order (use whatever subset is provided)
        canonical = [
            "Enquiry", "Quoted", "Negotiation", "PO",
            "Dispatch", "Delivered", "Payment", "Closed",
        ]
        ordered_stages = [s for s in canonical if s in stage_counts]
        # Add any extra stages not in canonical list
        for s in stage_counts:
            if s not in ordered_stages:
                ordered_stages.append(s)

        labels = ordered_stages
        values = [stage_counts[s] for s in labels]

        # Gradient from navy to green
        n = max(len(labels), 1)
        funnel_colors = []
        # Navy (#1e3a5f) -> Green (#2d6a4f)
        r_start, g_start, b_start = 30, 58, 95      # navy
        r_end, g_end, b_end       = 45, 106, 79     # green
        for i in range(n):
            t = i / max(n - 1, 1)
            r = int(r_start + (r_end - r_start) * t)
            g = int(g_start + (g_end - g_start) * t)
            b = int(b_start + (b_end - b_start) * t)
            funnel_colors.append(f"rgb({r},{g},{b})")

        fig = go.Figure(
            go.Funnel(
                y=labels,
                x=values,
                textinfo="value+percent initial",
                textposition="inside",
                textfont=dict(size=13, color="white", family=_FONT_FAMILY),
                marker=dict(color=funnel_colors, line=dict(width=0)),
                connector=dict(line=dict(color=VASTU_COLORS['cream'], width=1)),
                hovertemplate="<b>%{y}</b><br>Count: %{x}<br>%{percentInitial:.1%} of enquiries<extra></extra>",
            )
        )

        fig.update_layout(
            title=dict(
                text="Sales Pipeline",
                font=dict(size=16, color=VASTU_COLORS['navy']),
            ),
            showlegend=False,
        )
        self._apply_vastu_theme(fig, height=max(350, len(labels) * 52 + 80))
        return fig

    # ------------------------------------------------------------------
    # 6. Sparkline — minimal inline chart
    # ------------------------------------------------------------------
    def sparkline(self, values: list, color: str | None = None, height: int = 60) -> go.Figure:
        """Tiny inline area chart with no axes, grid, or labels.

        Parameters
        ----------
        values : list[float]
            Ordered numeric values.
        color : str, optional
            Line / fill colour (default: navy).
        height : int
            Figure height in pixels (default 60).

        Returns
        -------
        go.Figure
        """
        if color is None:
            color = VASTU_COLORS['navy']

        x = list(range(len(values)))

        fig = go.Figure(
            go.Scatter(
                x=x,
                y=values,
                mode="lines",
                fill="tozeroy",
                line=dict(color=color, width=1.5),
                fillcolor=self._alpha(color, 0.15),
                hoverinfo="skip",
            )
        )
        fig.update_layout(
            height=height,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            autosize=True,
            showlegend=False,
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

    # ------------------------------------------------------------------
    # 7. Alert Timeline
    # ------------------------------------------------------------------
    def alert_timeline(self, alerts: list) -> go.Figure:
        """Scatter plot of alerts over time, coloured by severity.

        Parameters
        ----------
        alerts : list[dict]
            Each dict: ``{timestamp, severity, message}``.
            Severity should be one of 'Critical', 'Warning', 'Info'.

        Returns
        -------
        go.Figure
        """
        severity_config = {
            "Critical": {"color": VASTU_COLORS['error'],   "symbol": "circle", "y": 3},
            "Warning":  {"color": VASTU_COLORS['warning'], "symbol": "diamond", "y": 2},
            "Info":     {"color": VASTU_COLORS['info'],    "symbol": "square",  "y": 1},
        }

        fig = go.Figure()

        # Group alerts by severity
        grouped: dict[str, list] = {}
        for a in alerts:
            sev = a.get("severity", "Info")
            grouped.setdefault(sev, []).append(a)

        for sev in ["Critical", "Warning", "Info"]:
            items = grouped.get(sev, [])
            if not items:
                continue
            cfg = severity_config.get(sev, severity_config["Info"])
            timestamps = []
            messages = []
            for a in items:
                ts = a.get("timestamp", "")
                if isinstance(ts, str):
                    try:
                        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    except Exception:
                        ts = datetime.utcnow()
                timestamps.append(ts)
                messages.append(a.get("message", ""))

            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=[cfg["y"]] * len(timestamps),
                    mode="markers",
                    name=sev,
                    marker=dict(
                        color=cfg["color"],
                        size=10,
                        symbol=cfg["symbol"],
                        line=dict(width=1, color="white"),
                    ),
                    text=messages,
                    hovertemplate=(
                        f"<b>{sev}</b><br>"
                        "%{x|%d-%b %H:%M}<br>"
                        "%{text}<extra></extra>"
                    ),
                )
            )

        fig.update_yaxes(
            tickvals=[1, 2, 3],
            ticktext=["Info", "Warning", "Critical"],
            range=[0.5, 3.5],
        )
        fig.update_xaxes(title_text="Time", tickformat="%d-%b %H:%M")
        fig.update_layout(
            title=dict(
                text="Alert Timeline",
                font=dict(size=16, color=VASTU_COLORS['navy']),
            ),
            hovermode="closest",
        )
        self._apply_vastu_theme(fig, height=320)
        return fig

    # ------------------------------------------------------------------
    # 8. Revenue Pie (Donut) Chart
    # ------------------------------------------------------------------
    def revenue_pie_chart(self, revenue_by_segment: dict) -> go.Figure:
        """Donut chart showing revenue split by customer category.

        Parameters
        ----------
        revenue_by_segment : dict
            ``{category: revenue_inr}``

        Returns
        -------
        go.Figure
        """
        categories = list(revenue_by_segment.keys())
        revenues = [revenue_by_segment[c] for c in categories]
        total = sum(revenues)

        colors = _VASTU_SEQUENCE[: len(categories)]

        fig = go.Figure(
            go.Pie(
                labels=categories,
                values=revenues,
                hole=0.55,
                marker=dict(colors=colors, line=dict(color="white", width=2)),
                textinfo="label+percent",
                textfont=dict(size=12, family=_FONT_FAMILY),
                hovertemplate="<b>%{label}</b><br>Revenue: %{value:,.0f}<br>Share: %{percent}<extra></extra>",
                sort=False,
            )
        )

        fig.add_annotation(
            text=f"<b>{_format_inr(total, decimals=0)}</b><br><span style='font-size:11px'>Total Revenue</span>",
            x=0.5, y=0.5,
            font=dict(size=15, color=VASTU_COLORS['navy'], family=_FONT_FAMILY),
            showarrow=False,
        )

        fig.update_layout(
            title=dict(
                text="Revenue by Segment",
                font=dict(size=16, color=VASTU_COLORS['navy']),
            ),
            showlegend=True,
            legend=dict(orientation="h", yanchor="top", y=-0.05, xanchor="center", x=0.5),
        )
        self._apply_vastu_theme(fig, height=420)
        return fig

    # ------------------------------------------------------------------
    # 9. Price Forecast Chart (with confidence bands)
    # ------------------------------------------------------------------
    def price_forecast_chart(self, forecast_data: list) -> go.Figure:
        """Line chart with confidence band and actual-vs-predicted markers.

        Parameters
        ----------
        forecast_data : list[dict]
            Each dict: ``{date, predicted_price, low_band, high_band, actual_price}``.
            ``actual_price`` may be ``None`` for future dates.

        Returns
        -------
        go.Figure
        """
        dates          = []
        predicted      = []
        low_band       = []
        high_band      = []
        actual_dates   = []
        actual_prices  = []
        pass_dates     = []
        pass_prices    = []
        fail_dates     = []
        fail_prices    = []

        for rec in forecast_data:
            dt = rec.get("date", "")
            if isinstance(dt, str):
                try:
                    dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
                except Exception:
                    continue
            dates.append(dt)
            predicted.append(rec.get("predicted_price", 0))
            low_band.append(rec.get("low_band", 0))
            high_band.append(rec.get("high_band", 0))

            ap = rec.get("actual_price")
            if ap is not None:
                actual_dates.append(dt)
                actual_prices.append(ap)
                # PASS if actual within band, FAIL otherwise
                if rec.get("low_band", 0) <= ap <= rec.get("high_band", 0):
                    pass_dates.append(dt)
                    pass_prices.append(ap)
                else:
                    fail_dates.append(dt)
                    fail_prices.append(ap)

        fig = go.Figure()

        # Confidence band (filled area between low and high)
        fig.add_trace(go.Scatter(
            x=dates + dates[::-1],
            y=high_band + low_band[::-1],
            fill="toself",
            fillcolor="rgba(59,130,246,0.12)",
            line=dict(color="rgba(0,0,0,0)"),
            name="Confidence Band",
            hoverinfo="skip",
            showlegend=True,
        ))

        # Predicted line (dashed)
        fig.add_trace(go.Scatter(
            x=dates,
            y=predicted,
            mode="lines",
            name="Predicted",
            line=dict(color=VASTU_COLORS['navy'], width=2, dash="dash"),
            hovertemplate="Predicted: %{y:,.0f}<br>%{x|%d-%b-%Y}<extra></extra>",
        ))

        # Actual line (solid green)
        if actual_dates:
            fig.add_trace(go.Scatter(
                x=actual_dates,
                y=actual_prices,
                mode="lines+markers",
                name="Actual",
                line=dict(color=VASTU_COLORS['green'], width=2.5),
                marker=dict(size=5, color=VASTU_COLORS['green']),
                hovertemplate="Actual: %{y:,.0f}<br>%{x|%d-%b-%Y}<extra></extra>",
            ))

        # PASS markers
        if pass_dates:
            fig.add_trace(go.Scatter(
                x=pass_dates,
                y=pass_prices,
                mode="markers",
                name="PASS",
                marker=dict(
                    size=10, color=VASTU_COLORS['success'],
                    symbol="circle",
                    line=dict(width=1.5, color="white"),
                ),
                hovertemplate="PASS: %{y:,.0f}<extra></extra>",
            ))

        # FAIL markers
        if fail_dates:
            fig.add_trace(go.Scatter(
                x=fail_dates,
                y=fail_prices,
                mode="markers",
                name="FAIL",
                marker=dict(
                    size=10, color=VASTU_COLORS['error'],
                    symbol="x",
                    line=dict(width=2, color=VASTU_COLORS['error']),
                ),
                hovertemplate="FAIL: %{y:,.0f}<extra></extra>",
            ))

        fig.update_xaxes(title_text="Date", tickformat="%d-%b")
        fig.update_yaxes(title_text="Price (INR / MT)", tickprefix="\u20b9", tickformat=",")
        fig.update_layout(
            title=dict(
                text="Price Forecast vs Actual",
                font=dict(size=16, color=VASTU_COLORS['navy']),
            ),
            hovermode="x unified",
        )
        self._apply_vastu_theme(fig, height=440)
        return fig

    # ------------------------------------------------------------------
    # 10. Inventory Gauge
    # ------------------------------------------------------------------
    def inventory_gauge(self, current_mt: float, max_mt: float, label: str) -> go.Figure:
        """Gauge / indicator showing inventory level with colour zones.

        Zones:
            Green  > 60 %
            Yellow 30-60 %
            Red    < 30 %

        Parameters
        ----------
        current_mt : float
            Current inventory in metric tonnes.
        max_mt : float
            Maximum capacity in metric tonnes.
        label : str
            Title / label for the gauge.

        Returns
        -------
        go.Figure
        """
        safe_max = max(max_mt, 1)
        pct = (current_mt / safe_max) * 100

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=current_mt,
                number=dict(
                    suffix=" MT",
                    font=dict(size=24, color=VASTU_COLORS['navy'], family=_FONT_FAMILY),
                ),
                title=dict(
                    text=label,
                    font=dict(size=15, color=VASTU_COLORS['navy'], family=_FONT_FAMILY),
                ),
                gauge=dict(
                    axis=dict(
                        range=[0, safe_max],
                        tickwidth=1,
                        tickcolor=VASTU_COLORS['navy'],
                        tickformat=",",
                    ),
                    bar=dict(color=VASTU_COLORS['navy_mid']),
                    bgcolor=VASTU_COLORS['cream'],
                    borderwidth=1,
                    bordercolor=VASTU_COLORS['cream'],
                    steps=[
                        {"range": [0, safe_max * 0.30], "color": self._alpha(VASTU_COLORS['error'], 0.25)},
                        {"range": [safe_max * 0.30, safe_max * 0.60], "color": self._alpha(VASTU_COLORS['warning'], 0.25)},
                        {"range": [safe_max * 0.60, safe_max], "color": self._alpha(VASTU_COLORS['success'], 0.25)},
                    ],
                    threshold=dict(
                        line=dict(color=VASTU_COLORS['fire'], width=3),
                        thickness=0.8,
                        value=current_mt,
                    ),
                ),
            )
        )

        fig.update_layout(
            height=250,
            margin=dict(l=30, r=30, t=60, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family=_FONT_FAMILY),
        )
        return fig

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    # ------------------------------------------------------------------
    # Chart Export Helpers
    # ------------------------------------------------------------------

    def render_with_export(self, fig: go.Figure, key: str, data_df=None):
        """Render a Plotly chart with CSV + PNG export buttons below it."""
        import streamlit as st
        st.plotly_chart(fig, use_container_width=True, key=f"chart_{key}")

        col1, col2 = st.columns([1, 1])
        if data_df is not None:
            with col1:
                csv = data_df.to_csv(index=False)
                st.download_button(
                    "Export CSV", csv, f"{key}.csv", "text/csv",
                    key=f"csv_{key}", use_container_width=True,
                )
        with col2:
            try:
                img_bytes = fig.to_image(format="png", width=1200, height=500)
                st.download_button(
                    "Export PNG", img_bytes, f"{key}.png", "image/png",
                    key=f"png_{key}", use_container_width=True,
                )
            except Exception:
                pass  # kaleido not installed

    # ------------------------------------------------------------------
    # Period Comparison Chart
    # ------------------------------------------------------------------

    def comparison_chart(
        self,
        current_data: list[float],
        previous_data: list[float],
        labels: list[str],
        current_label: str = "Current Period",
        previous_label: str = "Previous Period",
        title: str = "Period Comparison",
    ) -> go.Figure:
        """Overlay two time periods on the same chart for comparison."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=labels, y=current_data, name=current_label,
            mode="lines+markers",
            line=dict(color=VASTU_COLORS['navy'], width=2),
        ))
        fig.add_trace(go.Scatter(
            x=labels, y=previous_data, name=previous_label,
            mode="lines+markers",
            line=dict(color=VASTU_COLORS['gold'], width=2, dash="dash"),
        ))
        self._apply_vastu_theme(fig, height=400)
        fig.update_layout(title=title, hovermode="x unified")
        return fig

    # ------------------------------------------------------------------
    # Enhanced KPI Card with Sparkline
    # ------------------------------------------------------------------

    def kpi_with_sparkline(
        self,
        label: str,
        value: str,
        delta: str = "",
        trend_data: list[float] | None = None,
        delta_color: str = "green",
    ) -> str:
        """Return HTML for a KPI card with embedded inline sparkline SVG."""
        sparkline_svg = ""
        if trend_data and len(trend_data) >= 3:
            # Build SVG sparkline inline
            mn, mx = min(trend_data), max(trend_data)
            rng = mx - mn if mx != mn else 1
            w, h = 80, 24
            points = []
            for i, v in enumerate(trend_data[-10:]):
                x = i * w / max(len(trend_data[-10:]) - 1, 1)
                y = h - (v - mn) / rng * h
                points.append(f"{x:.1f},{y:.1f}")
            polyline = " ".join(points)
            color = "#22c55e" if delta_color == "green" else "#ef4444"
            sparkline_svg = (
                f'<svg width="{w}" height="{h}" style="margin-top:4px;">'
                f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5"/>'
                f'</svg>'
            )

        delta_html = ""
        if delta:
            c = "#22c55e" if delta_color == "green" else "#ef4444"
            arrow = "▲" if delta_color == "green" else "▼"
            delta_html = f'<span style="font-size:0.75rem;color:{c};">{arrow} {delta}</span>'

        return f"""
<div style="background:#0d1b2e;border:1px solid #1e3a5f;border-radius:10px;padding:14px 16px;">
<div style="font-size:0.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>
<div style="font-size:1.5rem;font-weight:800;color:#f8fafc;margin:2px 0;">{value} {delta_html}</div>
{sparkline_svg}
</div>"""

    @staticmethod
    def _alpha(hex_color: str, alpha: float) -> str:
        """Convert a hex colour to an ``rgba(...)`` string with the given
        alpha transparency.

        Parameters
        ----------
        hex_color : str
            CSS hex colour, e.g. ``'#1e3a5f'``.
        alpha : float
            Opacity between 0 and 1.

        Returns
        -------
        str
            E.g. ``'rgba(30,58,95,0.15)'``
        """
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"


# ═══════════════════════════════════════════════════════════════════════════
# STANDALONE CHART FUNCTIONS (not part of ChartEngine class)
# ═══════════════════════════════════════════════════════════════════════════

def procurement_urgency_gauge(urgency: int, recommendation: str) -> str:
    """Return HTML for a procurement urgency circular gauge."""
    color = "#ef4444" if urgency >= 75 else (
        "#f59e0b" if urgency >= 50 else (
        "#3b82f6" if urgency >= 30 else "#22c55e"))
    return f"""
<div style="text-align:center; padding:20px;">
<div style="position:relative; margin:0 auto; width:120px; height:120px;">
<svg viewBox="0 0 36 36" style="transform:rotate(-90deg);">
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
      fill="none" stroke="#e2e8f0" stroke-width="3"/>
<path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
      fill="none" stroke="{color}" stroke-width="3"
      stroke-dasharray="{urgency}, 100" stroke-linecap="round"/>
</svg>
<div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);">
<div style="font-size:1.8rem; font-weight:900; color:{color};">{urgency}</div>
</div>
</div>
<div style="font-size:0.9rem; font-weight:700; color:{color}; margin-top:8px;">
{recommendation}
</div>
</div>
"""


def volatility_bands_chart(prices: list, window: int = 20):
    """Return a Plotly figure with Bollinger Bands for price volatility."""
    import plotly.graph_objects as go
    import numpy as np

    n = len(prices)
    if n < window:
        window = max(3, n // 2)

    arr = np.array(prices, dtype=float)
    sma = np.convolve(arr, np.ones(window)/window, mode="valid")
    std = np.array([np.std(arr[max(0, i-window+1):i+1]) for i in range(window-1, n)])

    upper = sma + 2 * std
    lower = sma - 2 * std
    x = list(range(window - 1, n))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(n)), y=prices, mode="lines",
                             name="Price", line=dict(color="#1e3a5f", width=2)))
    fig.add_trace(go.Scatter(x=x, y=upper.tolist(), mode="lines",
                             name="Upper Band", line=dict(color="#ef4444", dash="dash", width=1)))
    fig.add_trace(go.Scatter(x=x, y=sma.tolist(), mode="lines",
                             name=f"SMA({window})", line=dict(color="#f59e0b", width=1.5)))
    fig.add_trace(go.Scatter(x=x, y=lower.tolist(), mode="lines",
                             name="Lower Band", line=dict(color="#22c55e", dash="dash", width=1),
                             fill="tonexty", fillcolor="rgba(34,197,94,0.08)"))
    fig.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=20),
                      title="Volatility Bands (Bollinger)", template="plotly_white")
    return fig


def crude_bitumen_lag_chart(crude_prices: list, bitumen_prices: list, lag_days: int = 15):
    """Return a Plotly dual-axis chart showing crude → bitumen price lag."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    n_crude = len(crude_prices)
    n_bitumen = len(bitumen_prices)

    fig.add_trace(go.Scatter(
        x=list(range(n_crude)), y=crude_prices,
        name="Brent Crude ($/bbl)", mode="lines",
        line=dict(color="#1e3a5f", width=2),
    ), secondary_y=False)

    # Shift bitumen left by lag_days to show correlation
    fig.add_trace(go.Scatter(
        x=[i - lag_days for i in range(n_bitumen)], y=bitumen_prices,
        name=f"Bitumen (₹/MT) shifted -{lag_days}d", mode="lines",
        line=dict(color="#c9a84c", width=2, dash="dot"),
    ), secondary_y=True)

    fig.update_layout(
        height=350, margin=dict(l=0, r=0, t=30, b=20),
        title=f"Crude → Bitumen Price Lag ({lag_days} days)",
        template="plotly_white",
    )
    fig.update_yaxes(title_text="Crude ($/bbl)", secondary_y=False)
    fig.update_yaxes(title_text="Bitumen (₹/MT)", secondary_y=True)
    return fig


def volatility_thermometer(score: int, label: str = "Volatility") -> str:
    """Return HTML for a linear thermometer gauge."""
    color = "#22c55e" if score <= 30 else ("#f59e0b" if score <= 60 else "#ef4444")
    level = "Low" if score <= 30 else ("Medium" if score <= 60 else "High")
    return f"""
<div style="background:white; border-radius:10px; padding:12px; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
<span style="font-size:0.75rem; font-weight:600; color:#475569;">{label}</span>
<span style="font-size:0.75rem; font-weight:700; color:{color};">{level} ({score}%)</span>
</div>
<div style="background:#e2e8f0; border-radius:6px; height:14px; overflow:hidden;">
<div style="width:{score}%; height:100%; background:linear-gradient(90deg, #22c55e, #f59e0b, #ef4444);
border-radius:6px; transition:width 0.5s;"></div>
</div>
</div>
"""


# ═══════════════════════════════════════════════════════════════════════════
# Module-level convenience — singleton
# ═══════════════════════════════════════════════════════════════════════════
charts = ChartEngine()
"""Pre-instantiated :class:`ChartEngine` for quick import::

    from chart_engine import charts
    fig = charts.sparkline([10, 12, 11, 14, 13])
"""
