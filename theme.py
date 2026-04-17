"""
PPS Anantam — Global Theme Injection v6.0
"Clean SaaS Light" Aesthetic

Enforces a sleek, high-trust, minimalist Light Mode inspired by Stripe/Linear.
Utilizes pure white cards, crisp silver borders, and subtle drop shadows.
"""

import streamlit as st

def inject_theme() -> None:
    """Inject global CSS for the Crisp Light aesthetic."""
    st.markdown(
        """
        <style>
        /* Sidebar — visible by default at 240px, nav content renders as normal.
           The floating toggle button (injected separately) hides/shows the
           sidebar via the body.pps-sb-hidden class. */
        [data-testid="stSidebar"] {
            display: block !important;
            visibility: visible !important;
            min-width: 240px !important;
            width: 240px !important;
            transform: none !important;
            transition: none !important;
        }
        [data-testid="stSidebar"][aria-expanded="false"] {
            min-width: 240px !important;
            width: 240px !important;
            margin-left: 0 !important;
            transform: none !important;
        }
        /* Hide the native Streamlit collapse chevron — we use our own toggle */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="collapsedControl"],
        button[kind="header"] {
            display: none !important;
        }
        /* When user clicks our custom toggle, fully hide the sidebar */
        body.pps-sb-hidden section[data-testid="stSidebar"],
        body.pps-sb-hidden [data-testid="stSidebar"] {
            display: none !important;
        }

        /* 1. Global CSS Variables - Clean Light Theme */
        :root {
            --bg-app: #FAFAFA;
            --bg-surface: #FFFFFF;
            
            --text-main: #111827;
            --text-muted: #6B7280;
            --text-blue: #4F46E5;
            
            --border-subtle: #E5E7EB;
            --border-hover: #D1D5DB;
            
            --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --shadow-focus: 0 0 0 3px rgba(79, 70, 229, 0.2);
            
            --radius-sm: 6px;
            --radius-md: 12px;
            --radius-lg: 16px;
            
            --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        /* 2. Base Application Styling */
        html, body, [class*="css"] {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-app) !important;
            color: var(--text-main);
            letter-spacing: -0.01em;
        }

        /* Main Container Padding Constraint for that centered "Cloud App" look */
        .block-container {
            max-width: 1280px !important;
            padding-top: 1rem !important;
            padding-bottom: 4rem !important;
        }

        /* 3. The Core Magic: Bento Grids (st.columns / st.container wrappers) */
        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
            background: var(--bg-surface);
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-md);
            padding: 24px !important;
            box-shadow: var(--shadow-sm);
            transition: var(--transition);
        }

        [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"]:hover {
            box-shadow: var(--shadow-md);
            border-color: var(--border-hover);
            transform: translateY(-2px);
        }

        /* Prevent double styling on nested blocks */
        [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] [data-testid="stVerticalBlock"] {
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            transform: none !important;
        }

        /* 4. Streamlit UI Components Reskin */
        
        /* Typography */
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Inter', sans-serif !important;
            color: var(--text-main) !important;
            letter-spacing: -0.02em !important;
            font-weight: 700 !important;
        }

        p, div, span, label {
            color: var(--text-main);
        }
        
        p {
            line-height: 1.6;
        }

        /* Primary Buttons */
        .stButton>button[kind="primary"] {
            background-color: var(--text-blue) !important;
            color: #FFFFFF !important;
            border: 1px solid transparent !important;
            border-radius: var(--radius-sm) !important;
            font-weight: 600 !important;
            box-shadow: var(--shadow-sm) !important;
            padding: 0.5rem 1rem !important;
            transition: var(--transition) !important;
        }
        .stButton>button[kind="primary"]:hover {
            background-color: #4338CA !important; /* darker indigo */
            box-shadow: var(--shadow-md) !important;
            transform: translateY(-1px);
        }

        /* Secondary Buttons / Streamlit Default Buttons */
        .stButton>button[kind="secondary"] {
            background-color: #FFFFFF !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: var(--radius-sm) !important;
            font-weight: 500 !important;
            box-shadow: var(--shadow-sm) !important;
            padding: 0.5rem 1rem !important;
            transition: var(--transition) !important;
        }
        .stButton>button[kind="secondary"]:hover {
            border-color: var(--border-hover) !important;
            background-color: #F9FAFB !important;
            box-shadow: var(--shadow-md) !important;
        }

        /* Inputs (Text, Number, Date, Select) */
        .stTextInput>div>div>input,
        .stNumberInput>div>div>input,
        .stTextArea>div>div>textarea,
        .stSelectbox>div>div>div {
            background-color: #FFFFFF !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: var(--radius-sm) !important;
            padding: 0.5rem 0.75rem !important;
            transition: var(--transition);
        }
        
        .stTextInput>div>div>input:focus,
        .stNumberInput>div>div>input:focus,
        .stTextArea>div>div>textarea:focus,
        .stSelectbox>div>div>div:focus {
            border-color: var(--text-blue) !important;
            box-shadow: var(--shadow-focus) !important;
        }

        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: var(--bg-surface) !important;
            border-right: 1px solid var(--border-subtle) !important;
        }
        [data-testid="stSidebarNav"] {
            display: none; /* Hide native page nav, using our custom one */
        }
        
        /* Metric Styling Native */
        [data-testid="stMetricValue"] {
            font-family: 'Inter', sans-serif !important;
            font-weight: 800 !important;
            letter-spacing: -0.02em !important;
            color: var(--text-main) !important;
        }
        [data-testid="stMetricLabel"] {
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.05em !important;
            color: var(--text-muted) !important;
            font-size: 0.75rem !important;
        }

        /* Hide the annoying 'stDeployButton' permanently */
        [data-testid="stHeader"] {
            background-color: transparent !important;
        }
        [data-testid="stToolbar"] {
            display: none !important;
        }
        [data-testid="stDecoration"] {
            display: none !important;
        }

        /* Dataframes & Tables */
        [data-testid="stDataFrame"] {
            border: 1px solid var(--border-subtle);
            border-radius: var(--radius-sm);
            overflow: hidden;
            box-shadow: var(--shadow-sm);
        }

        /* ═══════════════════════════════════════════════════════════════
           MOBILE RESPONSIVE — Progressive Enhancement
           Breakpoints: 1024px (tablet), 768px (mobile landscape), 480px (mobile portrait)
           ═══════════════════════════════════════════════════════════════ */

        /* Viewport meta (injected via JS below) */

        /* ── Tablet (≤1024px) ── */
        @media (max-width: 1024px) {
            .block-container {
                max-width: 100% !important;
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
        }

        /* ── Mobile Landscape (≤768px) ── */
        @media (max-width: 768px) {
            /* Reduce container padding */
            .block-container {
                max-width: 100% !important;
                padding-left: 0.75rem !important;
                padding-right: 0.75rem !important;
                padding-top: 0.5rem !important;
            }

            /* Stack columns vertically */
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
            div[data-testid="stHorizontalBlock"] {
                flex-wrap: wrap !important;
                gap: 0.5rem !important;
            }

            /* Smaller card padding */
            [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
                padding: 14px !important;
                border-radius: 10px !important;
            }
            [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"]:hover {
                transform: none !important;
            }

            /* Typography scale down */
            h1 { font-size: 1.4rem !important; }
            h2 { font-size: 1.2rem !important; }
            h3 { font-size: 1.05rem !important; }

            /* Metric cards — compact */
            [data-testid="stMetricValue"] {
                font-size: 1.3rem !important;
            }
            [data-testid="stMetricLabel"] {
                font-size: 0.65rem !important;
            }

            /* Touch-friendly buttons (min 44px tap target) */
            .stButton>button {
                min-height: 44px !important;
                font-size: 0.85rem !important;
                padding: 0.5rem 0.75rem !important;
            }

            /* Inputs — bigger tap target */
            .stTextInput>div>div>input,
            .stNumberInput>div>div>input,
            .stTextArea>div>div>textarea {
                min-height: 44px !important;
                font-size: 16px !important; /* prevents iOS zoom on focus */
            }

            /* Selectbox */
            .stSelectbox>div>div {
                min-height: 44px !important;
            }

            /* Tabs — scrollable */
            .stTabs [data-baseweb="tab-list"] {
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch;
                scrollbar-width: none;
                flex-wrap: nowrap !important;
            }
            .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
                display: none;
            }
            .stTabs [data-baseweb="tab"] {
                white-space: nowrap !important;
                font-size: 0.8rem !important;
                padding: 0.5rem 0.75rem !important;
            }

            /* Dataframes — horizontal scroll */
            [data-testid="stDataFrame"] {
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch;
            }

            /* Expander */
            .streamlit-expanderHeader {
                font-size: 0.9rem !important;
            }

            /* Hide top bar pill hover effects on mobile */
            div[style*="border-radius: 100px"] {
                border-radius: 16px !important;
                padding: 12px 16px !important;
                margin-bottom: 16px !important;
            }

            /* Sidebar: auto-collapse defaults, compact when open */
            [data-testid="stSidebar"] {
                min-width: 240px !important;
                max-width: 280px !important;
            }
            [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
                padding: 0 !important;
            }
        }

        /* ── Mobile Portrait (≤480px) ── */
        @media (max-width: 480px) {
            .block-container {
                padding-left: 0.5rem !important;
                padding-right: 0.5rem !important;
                padding-top: 0.25rem !important;
            }

            /* Even smaller typography */
            h1 { font-size: 1.2rem !important; }
            h2 { font-size: 1.05rem !important; }
            h3 { font-size: 0.95rem !important; }

            /* Metrics — 2 per row feel */
            [data-testid="stMetricValue"] {
                font-size: 1.15rem !important;
            }

            /* Cards — minimal padding */
            [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlock"] {
                padding: 10px !important;
                border-radius: 8px !important;
            }

            /* Buttons — full width on small screens */
            .stButton>button {
                width: 100% !important;
                min-height: 48px !important;
                font-size: 0.9rem !important;
            }

            /* Top bar — ultra compact */
            div[style*="border-radius: 100px"],
            div[style*="border-radius: 16px"] {
                border-radius: 12px !important;
                padding: 10px 12px !important;
                margin-bottom: 12px !important;
            }

            /* Sidebar compact */
            [data-testid="stSidebar"] {
                min-width: 220px !important;
                max-width: 260px !important;
            }
        }

        /* ═══ PWA & Mobile Meta ═══ */
        /* Safe area insets for notched phones */
        @supports (padding-top: env(safe-area-inset-top)) {
            .block-container {
                padding-top: calc(0.5rem + env(safe-area-inset-top)) !important;
                padding-bottom: calc(2rem + env(safe-area-inset-bottom)) !important;
                padding-left: calc(0.75rem + env(safe-area-inset-left)) !important;
                padding-right: calc(0.75rem + env(safe-area-inset-right)) !important;
            }
        }

        /* Smooth scrolling on iOS */
        * {
            -webkit-overflow-scrolling: touch;
        }

        /* Disable pull-to-refresh on mobile (prevents accidental refresh) */
        body {
            overscroll-behavior-y: contain;
        }

        /* Hide scrollbar but allow scroll on mobile */
        @media (max-width: 768px) {
            ::-webkit-scrollbar {
                width: 4px;
                height: 4px;
            }
            ::-webkit-scrollbar-thumb {
                background: #D1D5DB;
                border-radius: 4px;
            }
        }

        /* ═══ MOBILE RESPONSIVE ═══ */
        @media (max-width: 1024px) {
            .stApp > header { display: none !important; }
            [data-testid="stSidebar"] { width: 220px !important; }
            .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }
        }

        @media (max-width: 768px) {
            [data-testid="stSidebar"] { width: 200px !important; min-width: 200px !important; }
            .block-container { padding: 0.8rem 1rem !important; }

            /* Stack columns on tablet */
            [data-testid="column"] { width: 100% !important; flex: 100% !important; min-width: 100% !important; }

            /* KPI grids */
            .ck-kpis { grid-template-columns: repeat(2, 1fr) !important; }

            /* Smaller text */
            .ck-kpi .kv { font-size: 1.3rem !important; }
            .ck-hd .t { font-size: 1.2rem !important; }
            .ck-sig .sl { font-size: 1.4rem !important; }

            /* Tables scroll horizontally */
            [data-testid="stDataFrame"] { overflow-x: auto !important; }
            .rate-table { font-size: 0.8rem !important; }

            /* Products grid */
            .products { grid-template-columns: repeat(2, 1fr) !important; }
            .stats { grid-template-columns: repeat(2, 1fr) !important; }

            /* Contact bar stack */
            .contact-bar { flex-direction: column !important; gap: 12px !important; }
            .showcase-hero h1 { font-size: 1.4rem !important; }
        }

        @media (max-width: 480px) {
            [data-testid="stSidebar"] { display: none !important; }
            .block-container { padding: 0.5rem 0.8rem !important; }

            /* Single column everything */
            .ck-kpis { grid-template-columns: 1fr !important; }
            .ck-qg { grid-template-columns: 1fr !important; }
            .products { grid-template-columns: 1fr !important; }
            .stats { grid-template-columns: repeat(2, 1fr) !important; }

            /* Even smaller text */
            .ck-kpi .kv { font-size: 1.1rem !important; }
            .ck-hd .t { font-size: 1rem !important; }
            .ck-hd { padding: 16px !important; flex-direction: column !important; text-align: center !important; }
            .ck-sig .sl { font-size: 1.2rem !important; }

            /* Steps compact */
            .ck-st { flex-direction: column !important; }
            .ck-s { padding: 8px !important; font-size: 0.7rem !important; }

            /* Hide overflow on mobile */
            .showcase-hero .badge-row { flex-direction: column !important; }
            .showcase-hero h1 { font-size: 1.2rem !important; }

            /* Tier cards single column */
            .ck-tr { padding: 16px 10px !important; }
        }

        </style>

        <!-- Mobile viewport + PWA meta tags (injected via JS to avoid Streamlit stripping) -->
        <script>
        (function() {
            // Viewport meta
            if (!document.querySelector('meta[name="viewport"]')) {
                var vp = document.createElement('meta');
                vp.name = 'viewport';
                vp.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes, viewport-fit=cover';
                document.head.appendChild(vp);
            }
            // Theme color
            if (!document.querySelector('meta[name="theme-color"]')) {
                var tc = document.createElement('meta');
                tc.name = 'theme-color';
                tc.content = '#4F46E5';
                document.head.appendChild(tc);
            }
            // Apple mobile web app
            if (!document.querySelector('meta[name="apple-mobile-web-app-capable"]')) {
                var m1 = document.createElement('meta');
                m1.name = 'apple-mobile-web-app-capable';
                m1.content = 'yes';
                document.head.appendChild(m1);

                var m2 = document.createElement('meta');
                m2.name = 'apple-mobile-web-app-status-bar-style';
                m2.content = 'black-translucent';
                document.head.appendChild(m2);

                var m3 = document.createElement('meta');
                m3.name = 'apple-mobile-web-app-title';
                m3.content = 'PPS Anantam';
                document.head.appendChild(m3);
            }
            // PWA Manifest link
            if (!document.querySelector('link[rel="manifest"]')) {
                var ml = document.createElement('link');
                ml.rel = 'manifest';
                ml.href = '/app/static/manifest.json';
                document.head.appendChild(ml);
            }
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )
