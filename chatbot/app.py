"""
app.py — Streamlit UI + Main Loop
===================================

This file handles three things:
  1. Session state management  (conversation "memory")
  2. Chat UI rendering         (display past + new messages)
  3. Sidebar tools              (clear button, JSON inspector, prompt editor)

Architecture note:
  Streamlit reruns this ENTIRE script from top to bottom on every user
  interaction (button click, chat input, etc.).  That means normal Python
  variables reset every time.  The only way to persist data across reruns
  is `st.session_state` — a dictionary that Streamlit keeps alive for the
  duration of the browser session.  This is our conversation "memory".
"""

import json
import streamlit as st
import chat_engine

# ── Page config ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Memory Chatbot",
    page_icon="💬",
    layout="centered",
)

# ── Session state initialization ─────────────────────────────────────────
# This block runs on the very first load.  On subsequent reruns,
# st.session_state already has these keys, so the `if` guards skip them.
#
# WHY THIS MATTERS:
#   Without session_state, `messages` would be an empty list on every
#   rerun — the model would have zero memory.  Session state is what
#   lets us accumulate turns and send the full history each time.

if "messages" not in st.session_state:
    st.session_state.messages = []    # list of {"role": ..., "content": ...}

if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = chat_engine.DEFAULT_SYSTEM_PROMPT

# ── Sidebar ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🛠️ Controls")

    # --- Clear conversation button ----------------------------------------
    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()  # Immediately rerun so the UI reflects the cleared state.

    st.divider()

    # --- System prompt editor ---------------------------------------------
    # Letting the user edit the system prompt at runtime is one of the most
    # powerful teaching tools here.  Try changing it to "Reply only in
    # haiku" or "You are a pirate" and watch how the model's behavior
    # shifts — even though the conversation history stays the same.
    st.subheader("📝 System Prompt")
    new_prompt = st.text_area(
        "Edit the system prompt to steer the model's behavior:",
        value=st.session_state.system_prompt,
        height=150,
        key="system_prompt_input",
    )
    if new_prompt != st.session_state.system_prompt:
        st.session_state.system_prompt = new_prompt

    st.divider()

    # --- Raw JSON inspector -----------------------------------------------
    # This expander lets the user see exactly what `st.session_state.messages`
    # looks like — the raw list of role/content dicts that gets sent to the
    # API.  It demystifies the "shape" of a prompt.
    with st.expander("🔍 View raw message history (JSON)"):
        if st.session_state.messages:
            st.code(
                json.dumps(st.session_state.messages, indent=2),
                language="json",
            )
        else:
            st.caption("No messages yet. Start chatting!")

    st.divider()

    # --- Stretch goals (listed, not built) --------------------------------
    st.caption(
        "**Future ideas:**\n"
        "- Token count of running history\n"
        "- System prompt preset dropdown\n"
        "- History truncation (keep last N turns)"
    )

# ── Main chat area ───────────────────────────────────────────────────────
st.title("💬 Memory Chatbot")
st.caption(
    "A teaching chatbot — see the sidebar to inspect raw message history, "
    "edit the system prompt, or clear the conversation."
)

# --- Render existing conversation history ---------------------------------
# On every rerun, we loop through ALL past messages and display them.
# This is how the chat "remembers" visually — the data lives in
# session_state, and we just re-render it each time.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Handle new user input ------------------------------------------------
# `st.chat_input` returns None on every rerun *unless* the user just
# submitted a message.  This makes it a natural "event guard".
if prompt := st.chat_input("Type a message…"):

    # 1. Append the user's message to history.
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. Display it immediately so the user sees their own message.
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. Call the API with the FULL history.
    #    Notice: we pass every turn — user AND assistant — so the model
    #    can "see" the entire conversation.  The API is stateless; it has
    #    no memory of its own.  Our session_state IS the memory.
    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            reply = chat_engine.get_response(
                history=st.session_state.messages,
                system_prompt=st.session_state.system_prompt,
            )
        st.markdown(reply)

    # 4. Append the assistant's reply to history so it persists across
    #    reruns and gets included in future API calls.
    st.session_state.messages.append({"role": "assistant", "content": reply})
