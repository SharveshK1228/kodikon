# =================================================================
# IMPORTS
# =================================================================
import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime
import google.generativeai as genai
from fl_core import GlobalModel, ClientNode, run_federated_round

# =================================================================
# MODERN UI THEME CSS (glassy, minimal, dashboard look)
# =================================================================
st.markdown("""
<style>

/* -------------- GENERAL PAGE STYLE ---------------- */
body {
    background-color: #0E1117;
    color: #E1E1E1;
}

section.main > div {
    padding-top: 1rem;
}

/* -------------- TITLES ---------------- */
h1,h2,h3,h4 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700;
    letter-spacing: -0.5px;
}

/* -------------- INPUTS + BUTTONS ---------------- */
.stTextInput, .stTextArea textarea {
    background-color: #1E1E1E !important;
    border-radius: 10px !important;
    border: 1px solid #333 !important;
    color: white !important;
}

.stTextArea textarea:focus {
    border: 1px solid #4CAF50 !important;
}

.stButton>button {
    background-color: #4CAF50 !important;
    color: white !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 8px 18px;
    border: none;
}

.stButton>button:hover {
    background-color: #5FD364 !important;
}

/* -------------- SMALL BADGES ---------------- */
.badge-clean {
    color:#4DFF88;
    font-weight:600;
    font-size: 1.0rem;
}

.badge-bad {
    color:#FF4D4D;
    font-weight:600;
    font-size: 1.0rem;
}

/* Code box style */
code {
    font-size: 0.95rem !important;
    border-radius: 8px !important;
}

/* Tabs style */
.stTabs [role="tablist"] {
    gap: 3rem;
}

.stTabs [role="tab"] {
    font-size: 1.1rem !important;
    padding: 0.8rem 1.2rem !important;
}

</style>
""", unsafe_allow_html=True)

# =================================================================
# GEMINI MODEL SETUP
# =================================================================
API_KEY = "AIzaSyCz8ZroOwEQ3sLB4gR3xrN47VxOThb5hOw"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-pro")

# =================================================================
# CONSTANTS
# =================================================================
CUSS_WORDS = ["fuck", "shit", "bitch", "bastard", "asshole", "idiot"]
STATS_FILE = "stats.json"

# =================================================================
# SESSION
# =================================================================
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

# =================================================================
# FUNCTIONS
# =================================================================
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
    prompt = f"""
Rewrite the following message politely WITHOUT changing the meaning.
Return ONLY the rewritten sentence:

"{message}"""
    try:
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

# =================================================================
# PAGE
# =================================================================
st.set_page_config(page_title="EventHorizon – Federated Toxicity Monitor", layout="wide")

st.title("✨ EventHorizon – Federated Cuss Word Monitoring + Gemini Rewrite")
st.caption("A modern, federated, privacy-safe content moderation pipeline.")

stats = load_stats()

# =================================================================
# TABS
# =================================================================
tab1, tab2, tab3 = st.tabs(["💬 Analyze Message", "📊 Dashboard", "🛰 Federated Learning"])

# =================================================================
# TAB 1: ANALYZE
# =================================================================
with tab1:
    st.subheader("Message Analyzer")
    
    user_id = st.text_input("User ID", "user_1", key="user_input")
    text = st.text_area("Enter Message", height=140, key="msg_input")

    if st.button("Analyze & Rewrite", key="analyze_btn"):
        if not text.strip():
            st.warning("Please type a message.")
        else:
            # No global score shown!
            model_obj = st.session_state.global_model
            abusive = model_obj.is_abusive(text)
            found = detect_cuss_words(text)
            rewritten = rewrite_with_gemini(text)

            if abusive:
                st.markdown("<span class='badge-bad'>⚠ Abusive content detected</span>", unsafe_allow_html=True)
                label = 1
            else:
                st.markdown("<span class='badge-clean'>✓ Message is read</span>", unsafe_allow_html=True)
                label = 0

            st.markdown("#### Original Message")
            st.code(text)

            st.markdown("#### Polite Rewritten Message (via Gemini)")
            st.code(rewritten)

            # Save to client for FL
            idx = hash(user_id) % len(st.session_state.clients)
            st.session_state.clients[idx].add_sample(text, label)

            # Store for dashboard
            stats_entry = stats.get(user_id, {
                "total_messages": 0,
                "total_cuss": 0,
                "last_message": "",
                "last_time": ""
            })
            
            stats_entry["total_messages"] += 1
            stats_entry["total_cuss"] += sum(found.values()) if found else 0
            stats_entry["last_message"] = text
            stats_entry["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            stats[user_id] = stats_entry
            save_stats(stats)

# =================================================================
# TAB 2: DASHBOARD
# =================================================================
with tab2:
    st.subheader("User Behavior Dashboard")

    df = stats_to_df(stats)
    if df.empty:
        st.info("No activity yet.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("### 🔥 Cuss Count by User")
        st.bar_chart(df.set_index("user")["total_cuss"])

        st.markdown("### 🕒 Recent Messages")
        st.dataframe(df[["user", "last_message", "last_time"]])

# =================================================================
# TAB 3: FEDERATED LEARNING
# =================================================================
with tab3:
    st.subheader("Federated Learning Simulation")

    threshold = st.slider("Client participation threshold", 0.0, 1.0, 0.4, 0.05)

    if st.button("Run Federated Round", key="fl_btn"):
        result = run_federated_round(
            st.session_state.global_model,
            st.session_state.clients,
            threshold=threshold
        )

        st.success(f"FL Round {result['round']} completed! {result['num_updates']} clients contributed.")
        st.json(result["client_metrics"])



