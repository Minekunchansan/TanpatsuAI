import streamlit as st
import os
import random
from openai import OpenAI

# Configuration
# Secrets are loaded from .streamlit/secrets.toml (local) or Streamlit Cloud secrets
try:
    APP_PASSWORD = st.secrets["app_password"]
    MODEL_ID = "ft:gpt-4o-mini-2024-07-18:personal::Czi7N6OW"
    # We prioritize the secret key, but fall back to env var if needed
    EMBEDDED_API_KEY = st.secrets.get("openai_api_key", os.environ.get("OPENAI_API_KEY", ""))
except FileNotFoundError:
    st.error("Secrets file not found! Please check .streamlit/secrets.toml")
    st.stop()

# Page Setup
st.set_page_config(page_title="Tanpatsu AI", page_icon="😎")

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "api_key" not in st.session_state:
    st.session_state.api_key = EMBEDDED_API_KEY

# --- Password Screen ---
if not st.session_state.authenticated:
    st.title("🔒 Login Required")
    password = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.stop() # Stop execution here if not authenticated

# --- Chat Screen ---
st.title("😎 Tanpatsu AI")
st.markdown("短髪 (Tanpatsu) とトーク中...")

# API Key Check
if not st.session_state.api_key:
    st.warning("API Key not found.")
    st.stop()

# Initialize Client
try:
    client = OpenAI(api_key=st.session_state.api_key)
except Exception as e:
    st.error(f"Error initializing OpenAI client: {e}")
    st.stop()

# Display Chat History
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    elif msg["role"] == "assistant":
        with st.chat_message("assistant", avatar="😎"):
            st.markdown(msg["content"])

# User Input
if prompt := st.chat_input("メッセージを入力..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Response
    with st.chat_message("assistant", avatar="😎"):
        response_placeholder = st.empty()
        full_response = ""
        
        # System Prompt construction
        # We load samples if available, or just use hardcoded base
        system_prompt = """
You are "短髪" (Tanpatsu).
Your role is to chat with the user in the exact style of "短髪".

## Style Guide
- Language: Casual Japanese, Blunt, Rough but friendly.
- First Person: "俺" (Ore).
- Phrases: "だろ", "じゃん", "な", "さ", "ぜ", "笑笑", "www".
- Tone: Relaxed, sometimes cynical, often short.

## Critical Instruction on Context
- **Maintain the Conversation Flow**: Do NOT treat this as a Q&A. This is a continuous chat.
- **Reference History**: If the user asks a follow-up question, answer based on the previous messages.
- **Coherence**: Ensure your response connects logically to what was just said.
- **Short & Punchy**: Keep responses short (1-3 sentences), like a real LINE message.

User input will be in Japanese.
Respond in Japanese.
        """
        
        # Prepare messages for API
        # Prepare messages for API
        
        # 1. Build a natural conversation history for the System Prompt
        # This is safer than modifying the user string which causes formatting leaks.
        conversation_context = ""
        if len(st.session_state.messages) > 1:
            conversation_context = "\n\n# CURRENT CONVERSATION CONTEXT (IMPORTANT)\nThe user and you are currently talking about:\n"
            for m in st.session_state.messages[-5:-1]:
                role_name = "User" if m["role"] == "user" else "You"
                conversation_context += f"- {role_name} said: {m['content']}\n"
            conversation_context += "\nRespond to the LAST 'User said' message, but keep the above context in mind so it makes sense.\n"

        # 2. Update System Prompt dynamically
        dynamic_system_prompt = system_prompt + conversation_context + """
\n## Negative Constraints (CRITICAL)
- NEVER use double quotes (") around your text.
- NEVER use the "@" symbol.
- NEVER say "User" or "Tanpatsu" in your output. Just speak naturally.
- Do NOT repeat the user's name unnecessarily.
- NEVER output timestamps, file names, or metadata (e.g., "コマ撮り動画 2024...", "[Album]", "2024/08/13").
"""

        api_messages = [
            {"role": "system", "content": dynamic_system_prompt},
            {"role": "user", "content": prompt} 
        ]

        try:
            stream = client.chat.completions.create(
                model=MODEL_ID,
                messages=api_messages,
                temperature=0.7,
                max_tokens=150,
                stream=True
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    full_response += chunk.choices[0].delta.content
                    # Real-time regex cleaning could be tricky, so we clean at the end
                    response_placeholder.markdown(full_response + "▌")
            
            # Post-processing clean up
            import re
            # Remove @Mentions
            full_response = full_response.replace("@", "")
            
            # Remove date patterns like "2024/08/13(Tue)" or "2024-08-13" or "12:34" if isolated
            # This is a bit aggressive but user request is strict.
            full_response = re.sub(r'\d{4}/\d{1,2}/\d{1,2}(\(.\))?', '', full_response)
            
            # Update final display with clean text
            response_placeholder.markdown(full_response)
            
            # Add to history
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Error generating response: {e}")

# Sidebar
with st.sidebar:
    if st.button("Reset Chat"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.markdown("Powered by GPT-4o-mini Fine-tuned")
