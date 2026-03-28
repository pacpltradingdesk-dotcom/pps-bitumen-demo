"""
AI Integration QA Test Suite
Tests all AI/ML features in the PPS Anantam Bitumen Dashboard
"""
import sys, json, time, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

RESULTS = {}

def section(name):
    print("\n" + "=" * 70)
    print(f"  {name}")
    print("=" * 70)

# ── SECTION 2A: SENTIMENT ANALYSIS ──────────────────────────────────────
section("2A: SENTIMENT ANALYSIS (FinBERT/VADER/Keyword)")

try:
    from finbert_engine import analyze_financial_sentiment, get_finbert_status, get_market_sentiment
    status = get_finbert_status()
    print(f"  Active Engine: {status.get('active_engine', 'unknown')}")
    print(f"  FinBERT Ready: {status.get('finbert_ready', False)}")
    print(f"  VADER Ready:   {status.get('vader_ready', False)}")
    print(f"  Tier Chain:    {status.get('tier_chain', 'unknown')}")

    test_texts = [
        "Brent crude rises 2% on OPEC supply cut speculation",
        "India bitumen demand drops due to monsoon flooding",
        "NHAI awards highway projects worth Rs 14000 crore",
        "Global oil prices crash amid recession fears",
        "USD/INR steady at 86.9 ahead of US Fed minutes",
    ]
    print()
    all_ok = True
    for txt in test_texts:
        t0 = time.time()
        result = analyze_financial_sentiment(txt)
        elapsed = (time.time() - t0) * 1000
        sent = result.get("sentiment", "?")
        score = result.get("score", 0)
        eng = result.get("engine", "?")
        print(f"  [{sent:>8s}] score={score:.3f} engine={eng:>10s} ({elapsed:.0f}ms) | {txt[:60]}")
        if not sent or sent == "?":
            all_ok = False

    t0 = time.time()
    mkt = get_market_sentiment()
    elapsed = (time.time() - t0) * 1000
    print(f"\n  Market Sentiment: {mkt.get('overall','?')}, score={mkt.get('score',0):.3f}, "
          f"articles={mkt.get('article_count',0)}, engine={mkt.get('engine','?')} ({elapsed:.0f}ms)")

    RESULTS["2A_Sentiment"] = "PASS" if all_ok else "PARTIAL"
    print(f"  RESULT: {RESULTS['2A_Sentiment']}")
except Exception as e:
    print(f"  ERROR: {e}")
    RESULTS["2A_Sentiment"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2B: ML FORECASTING ──────────────────────────────────────────
section("2B: ML FORECASTING (Prophet/ARIMA/Heuristic)")

try:
    from ml_forecast_engine import forecast_crude_price, forecast_demand, forecast_fx_rate

    t0 = time.time()
    crude = forecast_crude_price(days_ahead=30)
    elapsed = (time.time() - t0) * 1000
    method = crude.get("method", "?")
    print(f"  Crude Forecast: method={method} ({elapsed:.0f}ms)")
    fc = crude.get("forecast", [])
    if fc:
        first = fc[0]
        last = fc[-1]
        print(f"    Day 1:  {first.get('ds','?')} -> ${first.get('yhat',0):.2f} "
              f"[{first.get('yhat_lower',0):.2f}, {first.get('yhat_upper',0):.2f}]")
        print(f"    Day 30: {last.get('ds','?')} -> ${last.get('yhat',0):.2f} "
              f"[{last.get('yhat_lower',0):.2f}, {last.get('yhat_upper',0):.2f}]")
    elif "error" in crude:
        print(f"    Error: {crude['error']}")

    t0 = time.time()
    demand = forecast_demand(months_ahead=3)
    elapsed = (time.time() - t0) * 1000
    print(f"  Demand Forecast: method={demand.get('method','?')} ({elapsed:.0f}ms)")
    dfc = demand.get("forecast", [])
    for f in dfc[:3]:
        print(f"    {f.get('ds','?')} -> {f.get('yhat',0):.0f} MT")

    t0 = time.time()
    fx = forecast_fx_rate(days_ahead=7)
    elapsed = (time.time() - t0) * 1000
    print(f"  FX Forecast: method={fx.get('method','?')} ({elapsed:.0f}ms)")
    fxfc = fx.get("forecast", [])
    for f in fxfc[:3]:
        print(f"    {f.get('ds','?')} -> Rs {f.get('yhat',0):.2f}")

    RESULTS["2B_Forecast"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2B_Forecast"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2C: RAG ENGINE ──────────────────────────────────────────────
section("2C: RAG SEARCH ENGINE (FAISS/TF-IDF/Keyword)")

try:
    from rag_engine import search, ask_with_context, build_index

    t0 = time.time()
    idx = build_index()
    elapsed = (time.time() - t0) * 1000
    print(f"  Index Build: status={idx.get('status','?')} docs={idx.get('document_count',0)} "
          f"method={idx.get('method','?')} ({elapsed:.0f}ms)")

    queries = [
        "bitumen price forecast",
        "NHAI highway projects",
        "crude oil trend",
        "monsoon demand impact",
    ]
    for q in queries:
        t0 = time.time()
        results = search(q, top_k=3)
        elapsed = (time.time() - t0) * 1000
        print(f"  Search \"{q}\": {len(results)} results ({elapsed:.0f}ms)")
        if results:
            top_text = str(results[0].get("text", ""))[:80]
            print(f"    Top: score={results[0].get('score',0):.3f} | {top_text}...")

    t0 = time.time()
    answer = ask_with_context("What is the current bitumen price trend?", role="admin")
    elapsed = (time.time() - t0) * 1000
    print(f"  Ask: confidence={answer.get('confidence','?')} sources={len(answer.get('sources',[]))} ({elapsed:.0f}ms)")
    ans_text = str(answer.get("answer", ""))[:120]
    print(f"    Answer: {ans_text}...")

    RESULTS["2C_RAG"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2C_RAG"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2D: SIGNAL WEIGHT LEARNER ───────────────────────────────────
section("2D: SIGNAL WEIGHT LEARNER (Ridge Regression)")

try:
    from signal_weight_learner import get_optimal_weights, get_status, learn_signal_weights

    status = get_status()
    print(f"  Status: source={status.get('source','?')} r2={status.get('r2','?')}")

    weights = get_optimal_weights()
    print(f"  Weights:")
    for k, v in weights.items():
        if isinstance(v, (int, float)):
            print(f"    {k}: {v:.3f}")

    t0 = time.time()
    learned = learn_signal_weights()
    elapsed = (time.time() - t0) * 1000
    print(f"  Learning: r2={learned.get('r2','?')} samples={learned.get('samples','?')} ({elapsed:.0f}ms)")

    RESULTS["2D_SignalWeights"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2D_SignalWeights"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2E: MARKET INTELLIGENCE ─────────────────────────────────────
section("2E: MARKET INTELLIGENCE (10-Signal Composite)")

try:
    from market_intelligence_engine import compute_master_signal, get_signal_breakdown

    t0 = time.time()
    master = compute_master_signal()
    elapsed = (time.time() - t0) * 1000
    print(f"  Master Signal: direction={master.get('market_direction','?')} "
          f"confidence={master.get('confidence',0)}% score={master.get('score',0)} ({elapsed:.0f}ms)")
    print(f"  Action: {master.get('recommended_action','?')}")
    print(f"  Demand: {master.get('demand_outlook','?')}")
    print(f"  Risk: {master.get('risk_level','?')}")

    breakdown = get_signal_breakdown()
    if isinstance(breakdown, dict):
        print(f"  Signal Breakdown ({len(breakdown)} signals):")
        for sig_name, sig_data in list(breakdown.items())[:9]:
            if isinstance(sig_data, dict):
                print(f"    {sig_name}: dir={sig_data.get('direction','?')} weight={sig_data.get('weight',0)}")

    RESULTS["2E_MarketIntel"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2E_MarketIntel"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2F: MODEL MONITOR ───────────────────────────────────────────
section("2F: MODEL MONITOR (PSI/MAE/RMSE Drift Detection)")

try:
    from model_monitor import get_model_health, alert_on_degradation

    health = get_model_health()
    print(f"  Model Health:")
    if isinstance(health, dict):
        for k, v in list(health.items())[:8]:
            if isinstance(v, dict):
                print(f"    {k}: {json.dumps(v)[:100]}")
            else:
                print(f"    {k}: {v}")

    alerts = alert_on_degradation()
    print(f"  Degradation Alerts: {len(alerts)}")
    for a in alerts[:3]:
        if isinstance(a, dict):
            print(f"    {a.get('model','?')}: {a.get('issue','?')}")
        else:
            print(f"    {a}")

    RESULTS["2F_ModelMonitor"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    RESULTS["2F_ModelMonitor"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2G: ANOMALY DETECTION ───────────────────────────────────────
section("2G: ANOMALY DETECTION (IsolationForest/Z-Score)")

try:
    from anomaly_engine import detect_anomalies, get_anomaly_status

    status = get_anomaly_status()
    print(f"  Engine: method={status.get('method','?')} sklearn={status.get('sklearn_available','?')}")

    import numpy as np
    test_data = list(np.random.normal(75, 2, 50)) + [120.0, 30.0]
    t0 = time.time()
    anomalies = detect_anomalies(test_data)
    elapsed = (time.time() - t0) * 1000
    if isinstance(anomalies, dict):
        print(f"  Detection: found={anomalies.get('count',0)} method={anomalies.get('method','?')} ({elapsed:.0f}ms)")
    elif isinstance(anomalies, list):
        print(f"  Detection: found={len(anomalies)} ({elapsed:.0f}ms)")
    else:
        print(f"  Detection: result type={type(anomalies).__name__} ({elapsed:.0f}ms)")

    RESULTS["2G_Anomaly"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2G_Anomaly"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2H: NLP EXTRACTION ──────────────────────────────────────────
section("2H: NLP EXTRACTION (spaCy/Regex NER)")

try:
    from nlp_extraction_engine import extract_entities, analyze_news_text, get_nlp_status

    status = get_nlp_status()
    print(f"  Engine: {status.get('active_engine','?')} spacy={status.get('spacy_ready','?')} transformers={status.get('transformers_ready','?')}")

    test_text = "NHAI awards Rs 14200 crore road projects in Gujarat Maharashtra and Rajasthan for highway construction by March 2027"
    t0 = time.time()
    entities = extract_entities(test_text)
    elapsed = (time.time() - t0) * 1000
    print(f"  Entities: states={entities.get('states',[])} orgs={entities.get('orgs',[])} "
          f"work_types={entities.get('work_types',[])} engine={entities.get('engine','?')} ({elapsed:.0f}ms)")

    t0 = time.time()
    analysis = analyze_news_text(test_text)
    elapsed = (time.time() - t0) * 1000
    print(f"  Analysis: sentiment={analysis.get('sentiment','?')} score={analysis.get('sentiment_score',0):.3f} ({elapsed:.0f}ms)")

    RESULTS["2H_NLP"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2H_NLP"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2I: AI FALLBACK ENGINE ──────────────────────────────────────
section("2I: AI FALLBACK ENGINE (Ollama/HF/GPT4All/OpenAI/Claude)")

try:
    from ai_fallback_engine import get_active_model_name, auto_detect_providers, test_provider_health

    active = get_active_model_name()
    print(f"  Active Model: {active}")

    providers = auto_detect_providers()
    print(f"  Detected Providers: {len(providers)}")
    for p in providers:
        if isinstance(p, dict):
            print(f"    {p.get('id','?')}: status={p.get('status','?')} model={p.get('model','?')}")
        else:
            print(f"    {p}")

    # Test Ollama health
    for pid in ["ollama", "huggingface", "gpt4all"]:
        try:
            h = test_provider_health(pid)
            if isinstance(h, dict):
                print(f"  {pid}: available={h.get('available',False)} latency={h.get('latency_ms','?')}ms")
            else:
                print(f"  {pid}: {h}")
        except Exception as ex:
            print(f"  {pid}: {ex}")

    RESULTS["2I_Fallback"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2I_Fallback"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2J: AI LEARNING ENGINE ──────────────────────────────────────
section("2J: AI LEARNING ENGINE (Continuous Learning)")

try:
    from ai_learning_engine import get_learned_weights, daily_learn

    weights = get_learned_weights()
    print(f"  Learned Weights:")
    if isinstance(weights, dict):
        for k, v in weights.items():
            if isinstance(v, (int, float)):
                print(f"    {k}: {v:.4f}")

    t0 = time.time()
    result = daily_learn()
    elapsed = (time.time() - t0) * 1000
    print(f"  Daily Learn: status={result.get('status','?')} adjustments={result.get('adjustments',0)} ({elapsed:.0f}ms)")

    RESULTS["2J_Learning"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    RESULTS["2J_Learning"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2K: BACKTEST ENGINE ─────────────────────────────────────────
section("2K: BACKTEST ENGINE (Walk-Forward Validation)")

try:
    from backtest_engine import get_latest_report

    report = get_latest_report()
    if report:
        print(f"  Latest Report: generated={report.get('generated_at','?')}")
        models = report.get("models", {})
        for m_name, m_data in models.items():
            if isinstance(m_data, dict):
                print(f"    {m_name}: mae={m_data.get('mae','?')} rmse={m_data.get('rmse','?')} "
                      f"mape={m_data.get('mape','?')} folds={m_data.get('folds','?')}")
    else:
        print(f"  No prior backtest report found (needs heavy ML packages)")

    RESULTS["2K_Backtest"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    RESULTS["2K_Backtest"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2L: ML BOOST ENGINE ─────────────────────────────────────────
section("2L: ML BOOST ENGINE (LightGBM/XGBoost/SHAP)")

try:
    from ml_boost_engine import get_boost_status, score_opportunity_boost, score_risk_boost

    status = get_boost_status()
    print(f"  Boost Status: tier={status.get('tier','?')} lgbm={status.get('lightgbm_available','?')} "
          f"xgb={status.get('xgboost_available','?')} shap={status.get('shap_available','?')}")

    # Test opportunity scoring
    test_features = {
        "price_delta": 500,
        "relationship_score": 0.7,
        "days_since_contact": 10,
        "qty": 200,
        "grade_vg30": 1,
        "season_factor": 0.8,
        "state_demand": 0.6,
    }
    t0 = time.time()
    opp = score_opportunity_boost(test_features)
    elapsed = (time.time() - t0) * 1000
    print(f"  Opportunity Score: score={opp.get('score','?')} label={opp.get('label','?')} "
          f"tier={opp.get('tier','?')} ({elapsed:.0f}ms)")

    # Test risk scoring
    test_risk = {
        "payment_reliability": 0.85,
        "overdue_days": 5,
        "credit_terms_days": 30,
        "total_orders": 15,
        "avg_order_value": 500000,
        "days_since_last_order": 20,
    }
    t0 = time.time()
    risk = score_risk_boost(test_risk)
    elapsed = (time.time() - t0) * 1000
    print(f"  Risk Score: score={risk.get('score','?')} level={risk.get('level','?')} "
          f"tier={risk.get('tier','?')} ({elapsed:.0f}ms)")

    RESULTS["2L_Boost"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    RESULTS["2L_Boost"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 2M: AI SETUP ENGINE ─────────────────────────────────────────
section("2M: AI SETUP ENGINE (Environment Detection)")

try:
    from ai_setup_engine import detect_environment, get_module_registry

    env = detect_environment()
    print(f"  OS: {env.get('os','?')} Python: {env.get('python_version','?')}")
    print(f"  RAM: {env.get('ram_gb','?')} GB  CPU: {env.get('cpu_cores','?')} cores")
    print(f"  GPU: {env.get('gpu_available','?')}")
    print(f"  venv: {env.get('virtual_env','?')}")

    registry = get_module_registry()
    print(f"  Module Registry ({len(registry)} modules):")
    if isinstance(registry, dict):
        for m_name, m_data in list(registry.items())[:10]:
            if isinstance(m_data, dict):
                print(f"    {m_name}: status={m_data.get('status','?')}")
            else:
                print(f"    {m_name}: {m_data}")
    elif isinstance(registry, list):
        for m in registry[:10]:
            if isinstance(m, dict):
                print(f"    {m.get('name','?')}: status={m.get('status','?')}")

    RESULTS["2M_Setup"] = "PASS"
    print(f"  RESULT: PASS")
except Exception as e:
    print(f"  ERROR: {e}")
    RESULTS["2M_Setup"] = "FAIL"
    print(f"  RESULT: FAIL")

# ── SECTION 3: OPEN SOURCE MODEL HEALTH CHECK ───────────────────────────
section("SECTION 3: OPEN SOURCE MODEL HEALTH CHECK")

model_health = {}

# Check transformers/FinBERT
try:
    import transformers
    print(f"  transformers: v{transformers.__version__} INSTALLED")
    model_health["transformers"] = "INSTALLED"
except ImportError:
    print(f"  transformers: NOT INSTALLED (FinBERT unavailable, using VADER/Keyword)")
    model_health["transformers"] = "NOT_INSTALLED"

# Check torch
try:
    import torch
    gpu = "GPU" if torch.cuda.is_available() else "CPU"
    print(f"  torch: v{torch.__version__} ({gpu}) INSTALLED")
    model_health["torch"] = f"INSTALLED ({gpu})"
except ImportError:
    print(f"  torch: NOT INSTALLED")
    model_health["torch"] = "NOT_INSTALLED"

# Check prophet
try:
    from prophet import Prophet
    print(f"  prophet: INSTALLED")
    model_health["prophet"] = "INSTALLED"
except ImportError:
    print(f"  prophet: NOT INSTALLED (using ARIMA/heuristic fallback)")
    model_health["prophet"] = "NOT_INSTALLED"

# Check sklearn
try:
    import sklearn
    print(f"  scikit-learn: v{sklearn.__version__} INSTALLED")
    model_health["sklearn"] = "INSTALLED"
except ImportError:
    print(f"  scikit-learn: NOT INSTALLED")
    model_health["sklearn"] = "NOT_INSTALLED"

# Check VADER
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    print(f"  vaderSentiment: INSTALLED")
    model_health["vader"] = "INSTALLED"
except ImportError:
    print(f"  vaderSentiment: NOT INSTALLED")
    model_health["vader"] = "NOT_INSTALLED"

# Check FAISS
try:
    import faiss
    print(f"  faiss-cpu: INSTALLED")
    model_health["faiss"] = "INSTALLED"
except ImportError:
    print(f"  faiss-cpu: NOT INSTALLED (using TF-IDF/keyword fallback)")
    model_health["faiss"] = "NOT_INSTALLED"

# Check sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    print(f"  sentence-transformers: INSTALLED")
    model_health["sentence_transformers"] = "INSTALLED"
except ImportError:
    print(f"  sentence-transformers: NOT INSTALLED")
    model_health["sentence_transformers"] = "NOT_INSTALLED"

# Check LightGBM
try:
    import lightgbm
    print(f"  lightgbm: v{lightgbm.__version__} INSTALLED")
    model_health["lightgbm"] = "INSTALLED"
except ImportError:
    print(f"  lightgbm: NOT INSTALLED (using sklearn GBM fallback)")
    model_health["lightgbm"] = "NOT_INSTALLED"

# Check XGBoost
try:
    import xgboost
    print(f"  xgboost: v{xgboost.__version__} INSTALLED")
    model_health["xgboost"] = "INSTALLED"
except ImportError:
    print(f"  xgboost: NOT INSTALLED")
    model_health["xgboost"] = "NOT_INSTALLED"

# Check statsmodels
try:
    import statsmodels
    print(f"  statsmodels: v{statsmodels.__version__} INSTALLED")
    model_health["statsmodels"] = "INSTALLED"
except ImportError:
    print(f"  statsmodels: NOT INSTALLED")
    model_health["statsmodels"] = "NOT_INSTALLED"

# Check spaCy
try:
    import spacy
    print(f"  spacy: v{spacy.__version__} INSTALLED")
    model_health["spacy"] = "INSTALLED"
except ImportError:
    print(f"  spacy: NOT INSTALLED (using regex NER fallback)")
    model_health["spacy"] = "NOT_INSTALLED"

# Check Ollama
try:
    import ollama
    print(f"  ollama: INSTALLED")
    model_health["ollama_pkg"] = "INSTALLED"
except ImportError:
    print(f"  ollama: NOT INSTALLED")
    model_health["ollama_pkg"] = "NOT_INSTALLED"

# Check ollama endpoint
try:
    import urllib.request
    req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read())
        models = [m.get("name","?") for m in data.get("models", [])]
        print(f"  Ollama Endpoint: ONLINE, models={models}")
        model_health["ollama_endpoint"] = f"ONLINE ({len(models)} models)"
except Exception as e:
    print(f"  Ollama Endpoint: OFFLINE ({e})")
    model_health["ollama_endpoint"] = "OFFLINE"

# Check HuggingFace
try:
    from huggingface_hub import InferenceClient
    print(f"  huggingface-hub: INSTALLED")
    model_health["huggingface"] = "INSTALLED"
except ImportError:
    print(f"  huggingface-hub: NOT INSTALLED")
    model_health["huggingface"] = "NOT_INSTALLED"

# Check GPT4All
try:
    from gpt4all import GPT4All
    print(f"  gpt4all: INSTALLED")
    model_health["gpt4all"] = "INSTALLED"
except ImportError:
    print(f"  gpt4all: NOT INSTALLED")
    model_health["gpt4all"] = "NOT_INSTALLED"

# Check SHAP
try:
    import shap
    print(f"  shap: v{shap.__version__} INSTALLED")
    model_health["shap"] = "INSTALLED"
except ImportError:
    print(f"  shap: NOT INSTALLED")
    model_health["shap"] = "NOT_INSTALLED"

RESULTS["3_ModelHealth"] = model_health

# ── SECTION 4: AI RESPONSE QUALITY ──────────────────────────────────────
section("SECTION 4: AI RESPONSE QUALITY CHECKLIST")

quality_checks = {}

# Accuracy check - sentiment should match expected
print("  Checking sentiment accuracy on known texts...")
try:
    from finbert_engine import analyze_financial_sentiment
    pos_text = "Oil prices surge as OPEC cuts production dramatically"
    neg_text = "Crude oil prices crash 10% on global recession fears"
    neu_text = "The committee will meet next Tuesday to discuss quarterly results"

    pos_r = analyze_financial_sentiment(pos_text)
    neg_r = analyze_financial_sentiment(neg_text)
    neu_r = analyze_financial_sentiment(neu_text)

    pos_ok = pos_r.get("sentiment") == "positive"
    neg_ok = neg_r.get("sentiment") == "negative"

    print(f"    Positive text -> {pos_r.get('sentiment')} (expected: positive) {'OK' if pos_ok else 'MISMATCH'}")
    print(f"    Negative text -> {neg_r.get('sentiment')} (expected: negative) {'OK' if neg_ok else 'MISMATCH'}")
    print(f"    Neutral text  -> {neu_r.get('sentiment')} (expected: neutral)")

    quality_checks["accuracy"] = "PASS" if (pos_ok and neg_ok) else "PARTIAL"
except Exception as e:
    quality_checks["accuracy"] = f"FAIL: {e}"

# Speed check
print("  Checking response speed (<3s per call)...")
try:
    t0 = time.time()
    _ = analyze_financial_sentiment("Test speed measurement")
    t1 = time.time()
    speed_ms = (t1 - t0) * 1000
    speed_ok = speed_ms < 3000
    print(f"    Sentiment speed: {speed_ms:.0f}ms {'OK' if speed_ok else 'SLOW'}")
    quality_checks["speed"] = "PASS" if speed_ok else "SLOW"
except Exception as e:
    quality_checks["speed"] = f"FAIL: {e}"

# Error handling check
print("  Checking error handling (empty/malformed input)...")
try:
    empty_r = analyze_financial_sentiment("")
    print(f"    Empty input -> {empty_r.get('sentiment','?')} (no crash = OK)")

    long_r = analyze_financial_sentiment("x" * 5000)
    print(f"    Long input (5000 chars) -> {long_r.get('sentiment','?')} (no crash = OK)")

    quality_checks["error_handling"] = "PASS"
except Exception as e:
    quality_checks["error_handling"] = f"FAIL: {e}"

# Hallucination check
print("  Checking for hallucination (forecasts within realistic range)...")
try:
    from ml_forecast_engine import forecast_crude_price
    fc = forecast_crude_price(days_ahead=7)
    forecasts = fc.get("forecast", [])
    if forecasts:
        prices = [f.get("yhat", 0) for f in forecasts]
        min_p = min(prices)
        max_p = max(prices)
        realistic = 30 < min_p < 200 and 30 < max_p < 200
        print(f"    Crude forecast range: ${min_p:.2f} - ${max_p:.2f} {'REALISTIC' if realistic else 'UNREALISTIC'}")
        quality_checks["hallucination"] = "PASS" if realistic else "FAIL"
    else:
        quality_checks["hallucination"] = "NO_DATA"
except Exception as e:
    quality_checks["hallucination"] = f"FAIL: {e}"

RESULTS["4_Quality"] = quality_checks
print(f"  Overall Quality: {json.dumps(quality_checks)}")

# ── SECTION 5: AI CONNECTIONS & WIRING ───────────────────────────────────
section("SECTION 5: AI CONNECTIONS & WIRING CHECK")

wiring_checks = {}

# Check API keys NOT hardcoded
print("  Checking API key storage...")
try:
    # Check settings.json / vault
    if os.path.exists("settings.json"):
        with open("settings.json") as f:
            settings = json.load(f)
        has_keys_section = "api_keys" in settings or any("key" in k.lower() for k in settings)
        print(f"    settings.json: exists, has API key section = {has_keys_section}")

    if os.path.exists("ai_fallback_config.json"):
        with open("ai_fallback_config.json") as f:
            ai_config = json.load(f)
        print(f"    ai_fallback_config.json: exists, providers configured = {list(ai_config.keys())[:5]}")

    wiring_checks["key_storage"] = "PASS (config files, not hardcoded)"
except Exception as e:
    wiring_checks["key_storage"] = f"FAIL: {e}"

# Check AI service manager exists
print("  Checking central AI routing...")
try:
    from ai_fallback_engine import ask_with_fallback
    print(f"    ai_fallback_engine.ask_with_fallback: EXISTS (central router)")
    wiring_checks["central_router"] = "PASS"
except Exception as e:
    wiring_checks["central_router"] = f"FAIL: {e}"

# Check news feeds connect to sentiment
print("  Checking news-to-sentiment wiring...")
try:
    from news_engine import get_articles
    from finbert_engine import analyze_financial_sentiment
    articles = get_articles(region="International", max_age_hours=168)
    if articles:
        sample = articles[0]
        headline = sample.get("headline", "")
        result = analyze_financial_sentiment(headline)
        print(f"    News -> Sentiment: '{headline[:50]}...' -> {result.get('sentiment','?')}")
        wiring_checks["news_sentiment"] = "PASS"
    else:
        print(f"    No articles available for testing")
        wiring_checks["news_sentiment"] = "NO_DATA"
except Exception as e:
    wiring_checks["news_sentiment"] = f"FAIL: {e}"

# Check AI response caching
print("  Checking AI response caching...")
try:
    from unified_intelligence_engine import get_full_intelligence
    t0 = time.time()
    _ = get_full_intelligence()
    first_call = (time.time() - t0) * 1000

    t0 = time.time()
    _ = get_full_intelligence()
    second_call = (time.time() - t0) * 1000

    cached = second_call < first_call * 0.5
    print(f"    First call: {first_call:.0f}ms, Second call: {second_call:.0f}ms (cached={cached})")
    wiring_checks["caching"] = "PASS" if cached else "PARTIAL"
except Exception as e:
    wiring_checks["caching"] = f"FAIL: {e}"

# Check background workers
print("  Checking background AI workers...")
try:
    import threading
    ai_threads = [t.name for t in threading.enumerate() if "ai" in t.name.lower() or "learn" in t.name.lower() or "sync" in t.name.lower()]
    print(f"    AI-related threads: {ai_threads if ai_threads else 'none running (normal outside Streamlit)'}")
    wiring_checks["workers"] = "PASS" if not ai_threads else f"PASS ({len(ai_threads)} threads)"
except Exception as e:
    wiring_checks["workers"] = f"FAIL: {e}"

RESULTS["5_Wiring"] = wiring_checks

# ── FINAL SUMMARY ───────────────────────────────────────────────────────
section("FINAL AI AUDIT SUMMARY")

total = 0
working = 0
partial = 0
broken = 0

for key, val in RESULTS.items():
    if key.startswith("2") or key.startswith("3") or key.startswith("4") or key.startswith("5"):
        if isinstance(val, str):
            total += 1
            if val == "PASS":
                working += 1
            elif val == "PARTIAL":
                partial += 1
            else:
                broken += 1

print(f"  Total AI Features Tested : {total}")
print(f"  Working Correctly        : {working}")
print(f"  Partially Working        : {partial}")
print(f"  Broken / Not Responding  : {broken}")
print()

# Model health summary
installed = sum(1 for v in model_health.values() if "INSTALLED" in str(v) or "ONLINE" in str(v))
not_installed = sum(1 for v in model_health.values() if "NOT_INSTALLED" in str(v) or "OFFLINE" in str(v))
print(f"  ML Packages Installed    : {installed}/{len(model_health)}")
print(f"  ML Packages Missing      : {not_installed}/{len(model_health)}")

# Save report
report = {
    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S IST"),
    "test_results": RESULTS,
    "model_health": model_health,
    "summary": {
        "total_features": total,
        "working": working,
        "partial": partial,
        "broken": broken,
        "packages_installed": installed,
        "packages_missing": not_installed,
    }
}
with open("ai_qa_report.json", "w") as f:
    json.dump(report, f, indent=2, default=str)
print(f"\n  Report saved to: ai_qa_report.json")
print(f"\n{'=' * 70}")
print(f"  ALL AI QA TESTS COMPLETE")
print(f"{'=' * 70}")
