"""
chat_engine.py — Prompt Formatting + API Call Logic
=====================================================

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
import anthropic

# ---------------------------------------------------------------------------
# 1. Load API key
# ---------------------------------------------------------------------------
# python-dotenv reads the .env file and sets environment variables so we
# never hard-code secrets in source code.
load_dotenv()

_api_key = os.getenv("ANTHROPIC_API_KEY")

# We create the client once at module level.  If the key is missing we
# defer the error to get_response() so the Streamlit UI can show a
# friendly message instead of crashing on import.
_client = anthropic.Anthropic(api_key=_api_key) if _api_key else None


# ---------------------------------------------------------------------------
# 2. System Prompt
# ---------------------------------------------------------------------------
# The system prompt is *separate* from user/assistant turns.  It acts as
# persistent instructions that shape every reply — like giving the model a
# "role card" before the conversation starts.
#
# In the Anthropic API, `system` is a top-level parameter, NOT a message
# in the messages list.  (OpenAI puts it as the first message with
# role="system" — same idea, different shape.)
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
    the Anthropic messages API expects.

    Our session history already stores entries as:
        {"role": "user" | "assistant", "content": "..."}

    The Anthropic API wants the same shape, so right now this function
    is a thin pass-through.  But having it as a separate step is
    intentional — it's the place where you would:
      • Trim old messages to fit the context window
      • Inject few-shot examples
      • Convert tool-use results into the right format

    ── What the final payload looks like ──────────────────────────
    The API call sends a JSON body roughly like this:

        {
          "model": "claude-sonnet-4-20250514",
          "max_tokens": 1024,
          "system": "<system prompt string>",    ← top-level, not a message
          "messages": [
              {"role": "user",      "content": "Hi, who are you?"},
              {"role": "assistant", "content": "I'm a coding assistant..."},
              {"role": "user",      "content": "Explain decorators."}
          ]
        }

    Notice: the messages list alternates user → assistant → user.
    The system prompt is NOT in this list — it's a separate field.
    ────────────────────────────────────────────────────────────────
    """
    # Return a clean copy so we never accidentally mutate session state.
    return [{"role": msg["role"], "content": msg["content"]} for msg in history]


# ---------------------------------------------------------------------------
# 4. get_response  —  Call the API and return the reply text
# ---------------------------------------------------------------------------
def get_response(history: list[dict], system_prompt: str | None = None) -> str:
    """
    Send the full conversation history to the Anthropic API and return
    the assistant's reply as a plain string.

    Parameters
    ----------
    history : list[dict]
        The full conversation so far (user + assistant turns).
    system_prompt : str | None
        Override the default system prompt.  Useful for the sidebar
        "edit system prompt" feature in app.py.

    Why pass the FULL history every time?
    -------------------------------------
    Chat APIs are stateless — the server forgets everything between
    requests.  The only way the model "remembers" the conversation is
    if we send every prior turn in the `messages` list.  This is also
    why very long conversations eventually need *truncation*: the
    model has a finite context window (e.g., 200k tokens for Claude),
    and sending too many messages will hit that limit.
    """
    # --- Guard: missing API key -------------------------------------------
    if _client is None:
        return (
            "⚠️ **API key not found.**\n\n"
            "1. Copy `.env.example` to `.env`\n"
            "2. Paste your Anthropic API key\n"
            "3. Restart the app (`streamlit run app.py`)"
        )

    # --- Build the request ------------------------------------------------
    prompt = system_prompt if system_prompt is not None else DEFAULT_SYSTEM_PROMPT
    messages = format_messages(history)

    try:
        response = _client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=prompt,          # ← system prompt lives here, not in messages
            messages=messages,      # ← the full conversation history
        )

        # The response object wraps content in a list of content blocks.
        # For a plain text reply there is one TextBlock at index 0.
        return response.content[0].text

    except anthropic.AuthenticationError:
        return (
            "🔑 **Authentication failed.** "
            "Double-check the API key in your `.env` file."
        )
    except anthropic.RateLimitError:
        return "⏳ **Rate limited.** Wait a moment and try again."
    except anthropic.APIError as e:
        return f"❌ **API error:** {e}"
    except Exception as e:
        # Catch-all so the app never crashes — we always return a string.
        return f"❌ **Unexpected error:** {e}"
