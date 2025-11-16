# ================================================================
# IMPORTS & INITIAL SETUP
# ================================================================
import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime
import google.generativeai as genai
from fl_core import GlobalModel, ClientNode, run_federated_round

# ================================================================
# GEMINI SETUP
# ================================================================
API_KEY = "AIzaSyCz8ZroOwEQ3sLB4gR3xrN47VxOThb5hOw"
genai.configure(api_key=API_KEY)

try:
    model = genai.GenerativeModel("gemini-pro")
except Exception as e:
    st.error(f"Failed loading Gemini model: {e}")
    st.stop()

# ================================================================
# CONSTANTS
# ================================================================
CUSS_WORDS = ["fuck", "shit", "bitch", "bastard", "asshole", "idiot"]
STATS_FILE = "stats.json"

# ================================================================
# SESSION INIT
# ================================================================
if "global_model" not in st.session_state:
    st.session_state.global_model = GlobalModel(threshold=0.4)

if "clients" not in st.session_state:
    st.session_state.clients = [
        ClientNode("client_1"),
        ClientNode("client_2"),
        ClientNode("client_3")
    ]

if "messages" not in st.session_state:
    st.session_state.messages = []

# ================================================================
# FUNCTIONS
# ================================================================
def detect_cuss_words(text):
    found = {}
    text_lower = text.lower()
    for word in CUSS_WORDS:
        pattern = r"\b" + re.escape(word) + r"\b"
        matches = re.findall(pattern, text_lower)
        if matches:
            found[word] = len(matches)
    return found

def rewrite_with_gemini(message):
    try:
        prompt = f"""
Rewrite the following message into a polite tone WITHOUT changing its meaning. 
Return ONLY the rewritten sentence:

"{message}"""

        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        return f"[Gemini Error: {e}]"

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    return json.load(open(STATS_FILE, "r"))

def save_stats(stats):
    json.dump(stats, open(STATS_FILE, "w"), indent=2)

def stats_to_df(stats):
    rows = []
    for user, info in stats.items():
        rows.append({
            "user": user,
            "total_messages": info.get("total_messages", 0),
            "total_cuss": info.get("total_cuss", 0),
            "last_message": info.get("last_message", ""),
            "last_time": info.get("last_time", "")
        })
    return pd.DataFrame(rows)

# ================================================================
# PAGE CONFIG
# ================================================================
st.set_page_config(page_title="Federated Cuss Monitor", layout="wide")
st.title("🧠 Federated Cuss Word Monitoring + Gemini Rewrite")
stats = load_stats()

# ================================================================
# TABS
# ================================================================
tab1, tab2, tab3 = st.tabs(["🔍 Analyze Message", "📊 Dashboard", "🛰 Federated Learning"])

# ================================================================
# TAB 1 — ANALYZE MESSAGE
# ================================================================
with tab1:
    st.subheader("Analyze & Rewrite")
    
    user_id = st.text_input("User ID", value="user_1", key="user_id_input")
    text = st.text_area("Message", height=150, key="main_message_input")

    if st.button("Analyze & Rewrite", key="analyze_btn_main"):
        if not text.strip():
            st.warning("Please enter a message.")
        else:
            global_model = st.session_state.global_model
            score = global_model.predict_score(text)
            abusive = global_model.is_abusive(text)

            st.write(f"### Global Model Abuse Score: `{score:.2f}`")
            if abusive:
                st.error("⚠ Marked as abusive")
                label = 1
            else:
                st.success("✅ Marked as clean")
                label = 0

            # Local cuss detection (non-ML)
            found = detect_cuss_words(text)
            if found:
                st.write("Detected explicit cuss words:")
                st.json(found)

            # LLM rewriting
            rewritten = rewrite_with_gemini(text)

            st.markdown("#### Original Message")
            st.code(text)

            st.markdown("#### Polite (Gemini Rewritten)")
            st.code(rewritten)

            # Assign message to a simulated FL client
            clients = st.session_state.clients
            idx = hash(user_id) % len(clients)
            client = clients[idx]
            client.add_sample(text, label)

            # Add to dashboard stats
            st.session_state.messages.append({
                "user": user_id,
                "text": text,
                "label": label,
                "score": score,
                "client": client.client_id
            })

            # persist stats.json
            user_stats = stats.get(user_id, {
                "total_messages": 0,
                "total_cuss": 0,
                "last_message": "",
                "last_time": ""
            })
            user_stats["total_messages"] += 1
            user_stats["total_cuss"] += sum(found.values()) if found else 0
            user_stats["last_message"] = text
            user_stats["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            stats[user_id] = user_stats
            save_stats(stats)

# ================================================================
# TAB 2 — DASHBOARD
# ================================================================
with tab2:
    st.subheader("User Abuse Statistics")

    df = stats_to_df(stats)
    if df.empty:
        st.info("No messages analyzed yet.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("### Abusive Word Count by User")
        st.bar_chart(df.set_index("user")["total_cuss"])

        st.markdown("### Latest Messages")
        st.dataframe(df[["user", "last_message", "last_time"]])

    with st.expander("Models available"):
        if st.button("Show available models", key="model_list_btn"):
            try:
                models = genai.list_models()
                st.write([m.name for m in models])
            except Exception as e:
                st.error(f"Error listing models: {e}")

# ================================================================
# TAB 3 — FEDERATED LEARNING
# ================================================================
with tab3:
    st.subheader("Simulated Federated Learning")

    threshold = st.slider("Client Accuracy Threshold", 0.0, 1.0, 0.4, 0.05, key="fl_threshold")

    if st.button("Run 1 Federated Round", key="fl_round_btn"):
        result = run_federated_round(
            st.session_state.global_model,
            st.session_state.clients,
            threshold=threshold
        )

        st.success(f"Round {result['round']} completed. {result['num_updates']} clients contributed.")
        st.write(f"Updated Global Weight: `{result['global_weight']:.3f}`")

        st.write("### Client Metrics")
        st.json(result["client_metrics"])
