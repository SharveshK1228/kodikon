import streamlit as st
import pandas as pd
import json
import os
import re
from datetime import datetime
import google.generativeai as genai

# =======================================
# Load Gemini API key from Streamlit Secrets
# =======================================
# 🚨 FIX 1: Load key securely from secrets.
# DO NOT hardcode your key.
try:
    # Assumes you have "GEMINI_API_KEY = 'YourKey...'" in .streamlit/secrets.toml
    api_key = "AIzaSyCyUDvhpsAU3LlwcfPcvSC-3YUniD31Fl8"
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"Failed to configure Gemini API. Is 'GEMINI_API_KEY' in your Streamlit secrets? Error: {e}")
    st.stop() # Stop the app if the key is missing

# 🚨 FIX 2: Instantiate the model. This was the missing line causing your error.
try:
    # You can change 'gemini-1.5-flash' to 'gemini-pro' or another model
    model = genai.GenerativeModel('models/chat-bison-001')
except Exception as e:
    st.error(f"Failed to load Gemini model. Error: {e}")
    st.stop()

# 🚨 FIX 3: Removed the first, incomplete `rewrite_with_gemini` function.

# =======================================
# Abusive Words List
# =======================================
CUSS_WORDS = [
    "fuck", "shit", "bitch", "bastard", "asshole", "idiot"
]

STATS_FILE = "stats.json"

# =======================================
# Utility Functions
# =======================================
def load_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_stats(stats):
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

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
Rewrite the following message into a polite, non-abusive tone
while keeping the same meaning and emotional context.

Return ONLY the rewritten message. No explanations.

Message:
{message}
"""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"Gemini rewrite failed: {e}")
        return f"[Gemini Error: {e}]"

def stats_to_df(stats):
    rows = []
    for user, info in stats.items():
        rows.append({
            "user": user,
            "total_messages": info.get("total_messages", 0),
            "total_cuss": info.get("total_cuss", 0),
            "last_message": info.get("last_message", ""),
            "last_time": info.get("last_time", ""),
        })
    return pd.DataFrame(rows)

# =======================================
# STREAMLIT UI
# =======================================
st.set_page_config(page_title="Cuss Word Monitor (Gemini)", layout="wide")
st.title("🧠 Federated Cuss Word Monitoring (Gemini Edition)")
st.caption("Detect abusive words, track user behavior, and rewrite messages using Gemini API.")

stats = load_stats()

tab1, tab2 = st.tabs(["🔍 Analyze Message", "📊 Dashboard"])

# =======================================
# TAB 1 — Analyze
# =======================================
with tab1:
    st.subheader("Analyze Message & Rewrite")

    user = st.text_input("User ID", "user_1")
    message = st.text_area("Message", height=150)

    if st.button("Analyze"):
        if not message.strip():
            st.warning("Enter a message.")
        else:
            found = detect_cuss_words(message)

            if found:
                st.error(f"⚠ Detected abusive words: {', '.join(found.keys())}")
                st.json(found)
            else:
                st.success("No abusive words detected 🎉")

            st.markdown("### Original Message")
            st.code(message)

            st.markdown("### ✨ Gemini-Toned Version")
            rewritten = rewrite_with_gemini(message)
            st.code(rewritten)

            # Update Stats
            user_stats = stats.get(user, {
                "total_messages": 0,
                "total_cuss": 0,
                "last_message": "",
                "last_time": ""
            })

            user_stats["total_messages"] += 1
            user_stats["total_cuss"] += sum(found.values())
            user_stats["last_message"] = message
            user_stats["last_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            stats[user] = user_stats
            save_stats(stats)

# =======================================
# TAB 2 — Dashboard
# =======================================
with tab2:
    st.subheader("User Abuse Statistics")

    df = stats_to_df(stats)
    if df.empty:
        st.info("No messages analyzed yet.")
    else:
        st.dataframe(df, use_container_width=True)

        st.markdown("### 🔥 Abusive Word Count by User")
        chart_df = df.set_index("user")["total_cuss"]
        st.bar_chart(chart_df)

        st.markdown("### 📅 Latest User Messages")
        st.dataframe(df[["user", "last_message", "last_time"]])
    
    # 🚨 FIX 4: Moved the debug button here
    with st.expander("Admin / Debug"):
        if st.button("Show available models"):
            try:
                models_list = genai.list_models()
                st.write([m.name for m in models_list])
            except Exception as e:
                st.error(f"Error listing models: {e}")


