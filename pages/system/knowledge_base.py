import streamlit as st
import datetime


def render():
    _today_str = datetime.date.today().strftime("%d %b %Y")
    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            border-bottom:2px solid var(--sandal,#e8dcc8);
            padding-bottom:6px;
            margin-bottom:10px;">
  <div style="display:flex;align-items:baseline;gap:10px;">
    <span style="font-size:1.08rem;font-weight:800;color:var(--navy,#1e3a5f);">📚 Knowledge Base</span>
    <span style="font-size:0.7rem;color:#64748b;font-weight:500;">Knowledge & AI</span>
  </div>
  <div style="display:flex;align-items:center;gap:8px;">
    <span style="font-size:0.68rem;color:var(--steel-light,#64748b);">{_today_str}</span>
  </div>
</div>
""", unsafe_allow_html=True)

    st.header("📚 Bitumen Sales Knowledge Base")
    st.caption("Training Manual, FAQs, and Process Guidelines")

    try:
        from sales_knowledge_base import (
            TRAINING_SECTIONS, KNOWLEDGE_BASE, get_section_questions,
            get_knowledge_count, get_chatbot_response
        )
    except Exception as _e:
        st.error(f"⚠️ Knowledge Base failed to load: {_e}")
        st.stop()

    # KPI Header
    total_qa = get_knowledge_count()
    section_count = len(TRAINING_SECTIONS)
    sections_with_content = sum(1 for sk in TRAINING_SECTIONS if len(get_section_questions(sk)) > 0)

    km1, km2, km3, km4 = st.columns(4)
    km1.metric("📖 Total Q&A", total_qa)
    km2.metric("📂 Sections", section_count)
    km3.metric("✅ Active Sections", sections_with_content)
    km4.metric("📅 Updated", _today_str)

    st.markdown("---")

    # Main tabs
    tab_search, tab_browse, tab_stats = st.tabs(["🔍 Search", "📂 Browse by Category", "📊 Stats"])

    # ─── TAB 1: Search with highlights ───
    with tab_search:
        st.subheader("🔍 Search Knowledge Base")
        search_query = st.text_input(
            "Enter your question or keywords",
            placeholder="e.g. payment terms, VG30, logistics...",
            key="kb_search_main"
        )

        if search_query:
            response = get_chatbot_response(search_query)
            if response['found']:
                st.success(f"**Best Match Found** (Confidence: {response['confidence']:.0f}%)")

                # Highlight matching text
                answer_text = response['answer']
                question_text = response['question']

                # Highlight search terms in the response
                highlighted_q = question_text
                highlighted_a = answer_text
                for term in search_query.lower().split():
                    if len(term) >= 3:
                        import re
                        pattern = re.compile(re.escape(term), re.IGNORECASE)
                        highlighted_q = pattern.sub(
                            lambda m: f"<mark style='background:#fef08a;padding:0 2px;border-radius:2px;'>{m.group()}</mark>",
                            highlighted_q
                        )
                        highlighted_a = pattern.sub(
                            lambda m: f"<mark style='background:#fef08a;padding:0 2px;border-radius:2px;'>{m.group()}</mark>",
                            highlighted_a
                        )

                st.markdown(f"**Q:** {highlighted_q}", unsafe_allow_html=True)
                st.markdown(f"**A:** {highlighted_a}", unsafe_allow_html=True)
                st.caption(f"Section: {response['section']}")
            else:
                st.warning("No direct match found. Try different keywords or browse sections below.")

            # Also show related results (keyword matching)
            st.markdown("---")
            st.markdown("#### Related Results")
            query_terms = [t.lower() for t in search_query.split() if len(t) >= 3]
            related = []
            for item in KNOWLEDGE_BASE:
                keywords = item.get("keywords", [])
                q_lower = item.get("question", "").lower()
                a_lower = item.get("answer", "").lower()
                score = 0
                for term in query_terms:
                    if term in q_lower:
                        score += 3
                    if term in a_lower:
                        score += 2
                    if any(term in kw.lower() for kw in keywords):
                        score += 4
                if score > 0:
                    related.append((score, item))

            related.sort(key=lambda x: x[0], reverse=True)

            if related:
                shown = 0
                for score, item in related[:8]:
                    if item['question'] == response.get('question', ''):
                        continue
                    shown += 1
                    section_name = TRAINING_SECTIONS.get(item['section'], item['section'])
                    with st.expander(f"📌 {item['question']} (Section: {section_name})"):
                        # Highlight search terms
                        ans_html = item['answer']
                        for term in query_terms:
                            import re
                            pattern = re.compile(re.escape(term), re.IGNORECASE)
                            ans_html = pattern.sub(
                                lambda m: f"<mark style='background:#fef08a;padding:0 2px;border-radius:2px;'>{m.group()}</mark>",
                                ans_html
                            )
                        st.markdown(f"💡 {ans_html}", unsafe_allow_html=True)
                if shown == 0:
                    st.caption("No additional related results.")
            else:
                st.caption("No related results found.")
        else:
            st.info("Type your question above to search the knowledge base.")

    # ─── TAB 2: Browse by Category ───
    with tab_browse:
        st.subheader("📂 Browse by Category")

        # Category selector
        category_options = {sk: f"{sn} ({len(get_section_questions(sk))} Qs)" for sk, sn in TRAINING_SECTIONS.items()}
        selected_category = st.selectbox(
            "Select Category",
            ["All Categories"] + list(category_options.keys()),
            format_func=lambda x: "📋 All Categories" if x == "All Categories" else f"📂 {category_options.get(x, x)}",
            key="kb_browse_cat"
        )

        if selected_category == "All Categories":
            # Show all sections as expanders
            for section_key, section_name in TRAINING_SECTIONS.items():
                questions = get_section_questions(section_key)
                count = len(questions)
                if count > 0:
                    with st.expander(f"📌 {section_name} ({count} Qs)"):
                        for item in questions:
                            st.markdown(f"**Q: {item['question']}**")
                            st.write(f"💡 {item['answer']}")
                            st.markdown("---")
        else:
            # Show selected section
            section_name = TRAINING_SECTIONS.get(selected_category, selected_category)
            questions = get_section_questions(selected_category)
            st.markdown(f"### {section_name}")
            st.caption(f"{len(questions)} questions in this section")

            if questions:
                # Filter within category
                cat_search = st.text_input("Filter within category", placeholder="Type to filter...", key="cat_filter")
                for item in questions:
                    if cat_search and cat_search.lower() not in item['question'].lower() and cat_search.lower() not in item['answer'].lower():
                        continue
                    with st.expander(f"❓ {item['question']}"):
                        st.write(f"💡 {item['answer']}")
                        if item.get('keywords'):
                            st.caption(f"Tags: {', '.join(item['keywords'][:5])}")
            else:
                st.info("No questions in this section yet.")

    # ─── TAB 3: Stats ───
    with tab_stats:
        st.subheader("📊 Knowledge Base Statistics")

        # Section-wise breakdown
        st.markdown("#### Questions per Section")
        try:
            import pandas as pd
        except ImportError:
            pd = None

        stats_data = []
        for sk, sn in TRAINING_SECTIONS.items():
            qs = get_section_questions(sk)
            avg_ans_len = sum(len(q.get('answer', '')) for q in qs) / len(qs) if qs else 0
            total_keywords = sum(len(q.get('keywords', [])) for q in qs)
            stats_data.append({
                "Section": sn,
                "Questions": len(qs),
                "Avg Answer Length": f"{avg_ans_len:.0f} chars",
                "Total Keywords": total_keywords,
            })

        if pd is not None:
            df_stats = pd.DataFrame(stats_data)
            st.dataframe(df_stats, use_container_width=True, hide_index=True)
        else:
            for row in stats_data:
                st.write(f"**{row['Section']}**: {row['Questions']} Qs")

        # Visual chart
        try:
            import plotly.graph_objects as go_chart
        except ImportError:
            go_chart = None

        if go_chart is not None and stats_data:
            section_names = [d["Section"][:20] for d in stats_data]
            question_counts = [d["Questions"] for d in stats_data]

            sc1, sc2 = st.columns(2)
            with sc1:
                fig_bar = go_chart.Figure(go_chart.Bar(
                    x=section_names, y=question_counts,
                    marker_color="#1e3a5f",
                    text=question_counts, textposition="auto"
                ))
                fig_bar.update_layout(
                    title="Questions per Section",
                    xaxis_title="Section", yaxis_title="Count",
                    template="plotly_white", height=400,
                    xaxis_tickangle=-45
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with sc2:
                fig_pie = go_chart.Figure(go_chart.Pie(
                    labels=section_names, values=question_counts,
                    hole=0.35
                ))
                fig_pie.update_layout(title="Section Distribution", height=400)
                st.plotly_chart(fig_pie, use_container_width=True)

        # Top keywords
        st.markdown("#### 🏷️ Top Keywords")
        keyword_freq = {}
        for item in KNOWLEDGE_BASE:
            for kw in item.get("keywords", []):
                keyword_freq[kw.lower()] = keyword_freq.get(kw.lower(), 0) + 1

        sorted_keywords = sorted(keyword_freq.items(), key=lambda x: x[1], reverse=True)[:20]
        if sorted_keywords and pd is not None:
            df_kw = pd.DataFrame(sorted_keywords, columns=["Keyword", "Frequency"])
            kw1, kw2 = st.columns(2)
            with kw1:
                st.dataframe(df_kw, use_container_width=True, hide_index=True)
            with kw2:
                if go_chart is not None:
                    fig_kw = go_chart.Figure(go_chart.Bar(
                        x=df_kw["Frequency"][:15], y=df_kw["Keyword"][:15],
                        orientation="h", marker_color="#e8dcc8"
                    ))
                    fig_kw.update_layout(
                        title="Top Keywords", template="plotly_white", height=400,
                        yaxis=dict(autorange="reversed")
                    )
                    st.plotly_chart(fig_kw, use_container_width=True)

        # Coverage summary
        st.markdown("#### 📈 Coverage Summary")
        cv1, cv2, cv3 = st.columns(3)
        cv1.metric("Unique Keywords", len(keyword_freq))
        cv2.metric("Avg Qs per Section", f"{total_qa / section_count:.1f}" if section_count > 0 else "0")
        avg_ans_all = sum(len(q.get('answer', '')) for q in KNOWLEDGE_BASE) / len(KNOWLEDGE_BASE) if KNOWLEDGE_BASE else 0
        cv3.metric("Avg Answer Length", f"{avg_ans_all:.0f} chars")

    st.markdown("---")
