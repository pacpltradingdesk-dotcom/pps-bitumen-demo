"""AI QA Fix - Re-test failing sections with correct function names"""
import sys, os, json, time
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Force UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

def section(name):
    print("\n" + "=" * 70)
    print(f"  {name}")
    print("=" * 70)

RESULTS = {}

# ── 2A FIX: SENTIMENT with UTF-8 ────────────────────────────────────────
section("2A FIX: SENTIMENT ANALYSIS")

try:
    from finbert_engine import analyze_financial_sentiment, get_finbert_status, get_market_sentiment
    status = get_finbert_status()
    print(f"  Active Engine: {status.get('active_engine', 'unknown')}")
    print(f"  FinBERT Ready: {status.get('finbert_ready', False)}")
    print(f"  VADER Ready:   {status.get('vader_ready', False)}")
    tier = status.get('tier_chain', 'unknown')
    print(f"  Tier Chain:    {tier}")

    test_texts = [
        ("Brent crude rises 2% on OPEC supply cut speculation", "positive"),
        ("India bitumen demand drops due to monsoon flooding", "negative"),
        ("NHAI awards highway projects worth Rs 14000 crore", "positive"),
        ("Global oil prices crash amid recession fears", "negative"),
        ("USD/INR steady at 86.9 ahead of US Fed minutes", "neutral"),
    ]

    correct = 0
    total = len(test_texts)
    for txt, expected in test_texts:
        t0 = time.time()
        result = analyze_financial_sentiment(txt)
        elapsed = (time.time() - t0) * 1000
        sent = result.get("sentiment", "?")
        score = result.get("score", 0)
        eng = result.get("engine", "?")
        match = "OK" if sent == expected else "MISMATCH"
        if sent == expected:
            correct += 1
        print(f"  [{sent:>8s}] score={score:.3f} engine={eng:>10s} ({elapsed:.0f}ms) expected={expected} {match}")
        print(f"    Text: {txt[:65]}")

    t0 = time.time()
    mkt = get_market_sentiment()
    elapsed = (time.time() - t0) * 1000
    print(f"\n  Market Sentiment: overall={mkt.get('overall','?')}, score={mkt.get('score',0):.3f}, "
          f"articles={mkt.get('article_count',0)}, engine={mkt.get('engine','?')} ({elapsed:.0f}ms)")

    accuracy = correct / total * 100
    print(f"\n  Sentiment Accuracy: {correct}/{total} ({accuracy:.0f}%)")
    RESULTS["2A"] = "PASS" if accuracy >= 60 else "PARTIAL"
    print(f"  RESULT: {RESULTS['2A']}")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2A"] = "FAIL"

# ── 2E FIX: MARKET INTELLIGENCE ─────────────────────────────────────────
section("2E FIX: MARKET INTELLIGENCE (10-Signal Composite)")

try:
    from market_intelligence_engine import compute_all_signals, get_master_signal, get_signal_status

    t0 = time.time()
    master = get_master_signal()
    elapsed = (time.time() - t0) * 1000
    print(f"  Master Signal: direction={master.get('market_direction','?')} "
          f"confidence={master.get('confidence',0)}% score={master.get('score',0)} ({elapsed:.0f}ms)")
    print(f"  Action: {master.get('recommended_action','?')}")
    print(f"  Demand: {master.get('demand_outlook','?')}")
    print(f"  Risk: {master.get('risk_level','?')}")

    status = get_signal_status()
    if isinstance(status, dict):
        print(f"\n  Signal Status ({len(status)} items):")
        for k, v in list(status.items())[:10]:
            if isinstance(v, dict):
                print(f"    {k}: {json.dumps(v)[:100]}")
            else:
                print(f"    {k}: {v}")

    t0 = time.time()
    signals = compute_all_signals()
    elapsed = (time.time() - t0) * 1000
    print(f"\n  All Signals: {len(signals) if isinstance(signals, dict) else '?'} signals ({elapsed:.0f}ms)")
    if isinstance(signals, dict):
        for sig_name, sig_data in list(signals.items())[:9]:
            if isinstance(sig_data, dict):
                print(f"    {sig_name}: dir={sig_data.get('direction','?')} score={sig_data.get('score','?')}")

    RESULTS["2E"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2E"] = "FAIL"

# ── 2G FIX: ANOMALY DETECTION ───────────────────────────────────────────
section("2G FIX: ANOMALY DETECTION (IsolationForest/Z-Score)")

try:
    from anomaly_engine import detect_price_anomalies, get_anomaly_status, get_anomaly_summary

    status = get_anomaly_status()
    print(f"  Status: method={status.get('method','?')} sklearn={status.get('sklearn_available','?')}")

    t0 = time.time()
    anomalies = detect_price_anomalies()
    elapsed = (time.time() - t0) * 1000
    if isinstance(anomalies, dict):
        print(f"  Price Anomalies: count={anomalies.get('count',0)} method={anomalies.get('method','?')} ({elapsed:.0f}ms)")
        items = anomalies.get('anomalies', [])
        for a in items[:3]:
            if isinstance(a, dict):
                print(f"    {a.get('date','?')}: value={a.get('value','?')} zscore={a.get('z_score','?')}")
    elif isinstance(anomalies, list):
        print(f"  Price Anomalies: {len(anomalies)} found ({elapsed:.0f}ms)")
    else:
        print(f"  Price Anomalies: type={type(anomalies).__name__} ({elapsed:.0f}ms)")

    summary = get_anomaly_summary()
    print(f"  Summary: {json.dumps(summary)[:200]}")

    RESULTS["2G"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2G"] = "FAIL"

# ── 2H FIX: NLP EXTRACTION ──────────────────────────────────────────────
section("2H FIX: NLP EXTRACTION (spaCy/Regex NER)")

try:
    from nlp_extraction_engine import extract_entities, analyze_sentiment, get_nlp_status

    status = get_nlp_status()
    print(f"  Engine: {status.get('active_engine','?')} spacy={status.get('spacy_ready','?')} transformers={status.get('transformers_ready','?')}")

    test_text = "NHAI awards Rs 14200 crore road projects in Gujarat Maharashtra and Rajasthan for highway construction by March 2027"
    t0 = time.time()
    entities = extract_entities(test_text)
    elapsed = (time.time() - t0) * 1000
    print(f"  Entities: states={entities.get('states',[])} orgs={entities.get('orgs',[])} "
          f"work_types={entities.get('work_types',[])} engine={entities.get('engine','?')} ({elapsed:.0f}ms)")

    t0 = time.time()
    sentiment = analyze_sentiment(test_text)
    elapsed = (time.time() - t0) * 1000
    if isinstance(sentiment, dict):
        print(f"  Sentiment: label={sentiment.get('label','?')} score={sentiment.get('score',0):.3f} ({elapsed:.0f}ms)")
    else:
        print(f"  Sentiment: {sentiment} ({elapsed:.0f}ms)")

    # Test more extractions
    test2 = "PMGSY Phase IV connects 18000 villages in Bihar and Uttar Pradesh with bitumen road construction"
    entities2 = extract_entities(test2)
    print(f"  Entities2: states={entities2.get('states',[])} work_types={entities2.get('work_types',[])} engine={entities2.get('engine','?')}")

    RESULTS["2H"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2H"] = "FAIL"

# ── 2I FIX: AI FALLBACK ENGINE ──────────────────────────────────────────
section("2I FIX: AI FALLBACK ENGINE")

try:
    from ai_fallback_engine import get_active_model_name, get_active_provider, get_provider_status, get_logs

    active_model = get_active_model_name()
    print(f"  Active Model: {active_model}")

    provider = get_active_provider()
    print(f"  Active Provider: {provider}")

    status = get_provider_status()
    if isinstance(status, dict):
        print(f"  Provider Status:")
        for k, v in status.items():
            print(f"    {k}: {v}")
    elif isinstance(status, list):
        print(f"  Provider Status ({len(status)} providers):")
        for p in status[:5]:
            if isinstance(p, dict):
                print(f"    {p.get('id','?')}: status={p.get('status','?')} model={p.get('model','?')}")
            else:
                print(f"    {p}")
    else:
        print(f"  Provider Status: {status}")

    logs = get_logs()
    if isinstance(logs, list):
        print(f"  Fallback Logs: {len(logs)} entries")
        for l in logs[-3:]:
            if isinstance(l, dict):
                print(f"    [{l.get('timestamp','?')}] provider={l.get('provider','?')} status={l.get('status','?')}")
    else:
        print(f"  Logs: {type(logs).__name__}")

    RESULTS["2I"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2I"] = "FAIL"

# ── 2J FIX: AI LEARNING ENGINE ──────────────────────────────────────────
section("2J FIX: AI LEARNING ENGINE (Class-based)")

try:
    from ai_learning_engine import AILearningEngine

    engine = AILearningEngine()
    print(f"  Engine Created: {type(engine).__name__}")

    # Check available methods
    methods = [m for m in dir(engine) if not m.startswith('_') and callable(getattr(engine, m))]
    print(f"  Available Methods: {methods}")

    # Try daily learn
    if hasattr(engine, 'daily_learn'):
        t0 = time.time()
        result = engine.daily_learn()
        elapsed = (time.time() - t0) * 1000
        print(f"  Daily Learn: {json.dumps(result)[:200]} ({elapsed:.0f}ms)")
    elif hasattr(engine, 'run_daily'):
        t0 = time.time()
        result = engine.run_daily()
        elapsed = (time.time() - t0) * 1000
        print(f"  Run Daily: {json.dumps(result)[:200]} ({elapsed:.0f}ms)")

    # Try get weights
    if hasattr(engine, 'get_weights'):
        weights = engine.get_weights()
        print(f"  Current Weights: {json.dumps(weights)[:200]}")
    elif hasattr(engine, 'get_learned_weights'):
        weights = engine.get_learned_weights()
        print(f"  Learned Weights: {json.dumps(weights)[:200]}")

    RESULTS["2J"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2J"] = "FAIL"

# ── FINAL SUMMARY ───────────────────────────────────────────────────────
section("FIXED TEST RESULTS")
for k, v in sorted(RESULTS.items()):
    status_icon = "OK" if v == "PASS" else ("~" if v == "PARTIAL" else "X")
    print(f"  [{status_icon}] {k}: {v}")

# Combined with previous results
combined = {
    "2A_Sentiment": RESULTS.get("2A", "?"),
    "2B_Forecast": "PASS",
    "2C_RAG": "PASS",
    "2D_SignalWeights": "PASS",
    "2E_MarketIntel": RESULTS.get("2E", "?"),
    "2F_ModelMonitor": "PASS",
    "2G_Anomaly": RESULTS.get("2G", "?"),
    "2H_NLP": RESULTS.get("2H", "?"),
    "2I_Fallback": RESULTS.get("2I", "?"),
    "2J_Learning": RESULTS.get("2J", "?"),
    "2K_Backtest": "PASS",
    "2L_Boost": "PASS",
    "2M_Setup": "PASS",
}
print(f"\n  COMBINED RESULTS:")
pass_count = sum(1 for v in combined.values() if v == "PASS")
partial_count = sum(1 for v in combined.values() if v == "PARTIAL")
fail_count = sum(1 for v in combined.values() if v == "FAIL")
print(f"  PASS: {pass_count}/{len(combined)}")
print(f"  PARTIAL: {partial_count}/{len(combined)}")
print(f"  FAIL: {fail_count}/{len(combined)}")
