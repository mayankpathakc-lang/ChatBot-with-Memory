"""
chat_engine.py — Prompt Formatting + API Call Logic (Gemini Edition)
======================================================================

This is the educational core of the project. It answers two questions:

  1. How does a "system prompt + conversation history" get assembled into
     a single API request?
  2. What does the actual API call look like, and what comes back?

Key insight: Chat APIs are *stateless*. The server does not remember your
previous messages.  Every request must send the FULL conversation history
so the model can "see" prior context.  This is why we store history in
Streamlit's session_state and pass it here on every turn.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# 1. Load API key
# ---------------------------------------------------------------------------
# python-dotenv reads the .env file and sets environment variables so we
# never hard-code secrets in source code.
load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY")

# We create the client once at module level. If the key is missing we
# defer the error to get_response() so the Streamlit UI can show a
# friendly message instead of crashing on import.
_client = genai.Client(api_key=_api_key) if _api_key else None


# ---------------------------------------------------------------------------
# 2. System Prompt
# ---------------------------------------------------------------------------
# The system prompt is *separate* from user/model turns. It acts as
# persistent instructions that shape every reply — like giving the model a
# "role card" before the conversation starts.
#
# In the Gemini API, the system prompt is passed in the request configuration
# object as `system_instruction`.
#
# We expose it as a module-level constant so app.py can let the user
# edit it at runtime — a great way to see how the system prompt steers
# the model's behavior.

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful, concise coding assistant. "
    "Answer questions clearly. When showing code, add brief comments. "
    "If you don't know something, say so."
)


# ---------------------------------------------------------------------------
# 3. format_messages  —  Shape the history for the API
# ---------------------------------------------------------------------------
def format_messages(history: list[dict]) -> list[dict]:
    """
    Take the raw session history and return it in the exact shape
    the Gemini contents API expects.

    Our session history stores entries as:
        {"role": "user" | "assistant", "content": "..."}

    But Gemini API expects:
      - The role name for the assistant to be "model" instead of "assistant".
      - The message content to be wrapped inside a "parts" list containing
        text blocks: {"role": "user" | "model", "parts": [{"text": "..."}]}

    This translation is the main reason format_messages() exists!

    ── What the final payload looks like ──────────────────────────
    The API call sends a JSON body roughly like this:

        {
          "model": "gemini-2.5-flash",
          "config": {
              "system_instruction": "<system prompt string>"  ← separate config
          },
          "contents": [
              {
                  "role": "user",
                  "parts": [{"text": "Hi, who are you?"}]
              },
              {
                  "role": "model",
                  "parts": [{"text": "I'm a coding assistant..."}]
              },
              {
                  "role": "user",
                  "parts": [{"text": "Explain decorators."}]
              }
          ]
        }

    Notice: the contents list alternates user → model → user.
    ────────────────────────────────────────────────────────────────
    """
    formatted = []
    for msg in history:
        # Translate role "assistant" to "model" for Gemini
        role = "user" if msg["role"] == "user" else "model"
        formatted.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    return formatted


# ---------------------------------------------------------------------------
# 4. get_response  —  Call the API and return the reply text
# ---------------------------------------------------------------------------
def get_response(history: list[dict], system_prompt: str | None = None) -> str:
    """
    Send the full conversation history to the Gemini API and return
    the model's reply as a plain string.

    Parameters
    ----------
    history : list[dict]
        The full conversation so far (user + assistant turns).
    system_prompt : str | None
        Override the default system prompt. Useful for the sidebar
        "edit system prompt" feature in app.py.

    Why pass the FULL history every time?
    -------------------------------------
    Chat APIs are stateless — the server forgets everything between
    requests. The only way the model "remembers" the conversation is
    if we send every prior turn in the `contents` list. This is also
    why very long conversations eventually need *truncation*: the
    model has a finite context window, and sending too many messages
    will hit that limit.
    """
    # --- Guard: missing API key -------------------------------------------
    if _client is None:
        return (
            "⚠️ **Gemini API key not found.**\n\n"
            "1. Copy `.env.example` to `.env`\n"
            "2. Paste your Google AI Studio API key in `GEMINI_API_KEY`\n"
            "3. Restart the app (`streamlit run app.py`)"
        )

    # --- Build the request ------------------------------------------------
    prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
    contents = format_messages(history)

    try:
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,      # ← the full conversation history
            config=types.GenerateContentConfig(
                system_instruction=prompt  # ← system prompt lives here
            )
        )

        # Return the generated text reply
        if response.text:
            return response.text
        else:
            return "⚠️ **Empty response received from the model.**"

    except Exception as e:
        # Catch-all so the app never crashes — we always return a string.
        # This will catch auth errors, rate limits, network errors, etc.
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg:
            return (
                "🔑 **Authentication failed.** "
                "Double-check the API key in your `.env` file."
            )
        return f"❌ **Unexpected error:** {error_msg}"
