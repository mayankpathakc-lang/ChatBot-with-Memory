# 💬 Memory Chatbot

A minimal, heavily-commented Streamlit chatbot built for **learning**.  It teaches three concepts through working code:

| Concept | Where to look |
|---|---|
| **Prompt formatting** — how a system prompt + conversation turns become one API request | [`chatbot/chat_engine.py`](chatbot/chat_engine.py) → `format_messages()` |
| **Conversation history** — how state persists across Streamlit reruns | [`chatbot/app.py`](chatbot/app.py) → `st.session_state.messages` |
| **App structure** — clean separation of UI, state, and API logic | `chatbot/app.py` handles UI; `chatbot/chat_engine.py` handles the model |

---

## Setup

### 1. Navigate to the project folder
```bash
cd chatbot
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your API key

```bash
cp .env.example .env
```

Open `.env` and replace `your_key_here` with your [Anthropic API key](https://console.anthropic.com/).

### 4. Run the app

```bash
streamlit run app.py
```

The app opens in your browser at `http://localhost:8501`.

---

## How It Works

Here's the data flow for every message you send:

```
┌──────────────────────────────────────────────────────────────┐
│  1. User types a message                                     │
│     └─► Appended to  st.session_state.messages               │
│                                                              │
│  2. format_messages(history)                                 │
│     └─► Returns the list as [{"role": …, "content": …}, …]  │
│                                                              │
│  3. API call                                                 │
│     └─► client.messages.create(                              │
│              system = "<system prompt>",                      │
│              messages = <formatted history>                   │
│         )                                                    │
│     The FULL history is sent every time because the API is   │
│     stateless — it has no server-side memory.                │
│                                                              │
│  4. Reply appended to  st.session_state.messages             │
│     └─► Persists across Streamlit reruns                     │
│     └─► Included in the next API call as context             │
└──────────────────────────────────────────────────────────────┘
```

### Why session_state?

Streamlit re-executes the entire `app.py` script on every interaction. Normal Python variables reset each time. `st.session_state` is a special dictionary that survives reruns — it's the app's "memory".

### Why send the full history?

Chat APIs like Claude and GPT are **stateless**. The server forgets everything between requests. The only way the model "remembers" your conversation is if you send every prior turn in the `messages` list. This is also why very long conversations eventually need **truncation** — the model has a finite context window.

### Why is the system prompt separate?

The system prompt sets the model's persona/instructions and is separate from the user↔assistant turns. In the Anthropic API it's a top-level `system` parameter; in OpenAI's API it's the first message with `role: "system"`. Either way, keeping it separate makes it easy to swap behaviors without touching the conversation history.

---

## Sidebar Features

- **🗑️ Clear conversation** — resets `st.session_state.messages` to `[]`
- **📝 System Prompt editor** — edit the prompt live and watch the model's behavior change
- **🔍 JSON inspector** — see the raw message history that gets sent to the API

---

## Stretch Goals (not built yet)

- Token/character count of the running history (teaches context-window limits)
- System prompt preset dropdown (e.g., "Pirate", "Haiku-only", "Socratic tutor")
- History truncation function — keep last N turns to stay within the context window

---

## File Structure

```
chatbot/
├── app.py              # Streamlit UI + main loop
├── chat_engine.py      # Prompt formatting + API call logic
├── requirements.txt    # Python dependencies
└── .env.example        # Template for your API key
```