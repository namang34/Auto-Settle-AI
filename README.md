# Auto-Settle AI (Streamlit)

## Run on your laptop
    pip install -r requirements.txt
    streamlit run app.py
Choose ONE model backend with environment variables (PowerShell: `$env:NAME="value"`):

| Backend | Variables |
|---|---|
| Claude (default) | `ANTHROPIC_API_KEY`, optional `MODEL` |
| Any OpenAI-compatible API (OpenAI, Gemini, Groq, OpenRouter) | `PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL` (must support images), optional `OPENAI_BASE_URL` |
| Small local model (Ollama, under 20B parameters) | `PROVIDER=ollama`, optional `OLLAMA_MODEL` (default qwen2.5vl:7b) |

Gemini example: `OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/` and a Gemini model name.
Always test your chosen model on your own photos: it must return valid JSON and find all damaged parts.

## Host it publicly (free options)
1. Put app.py, core.py and requirements.txt in a GitHub repository.
2. Streamlit Community Cloud (share.streamlit.io): New app, pick the repo and app.py.
3. In the app's Settings, Secrets, add your variables, for example:
       PROVIDER = "openai"
       OPENAI_API_KEY = "..."
       OPENAI_MODEL = "..."
   Top-level secrets are available to the app as environment variables.
4. Alternative: a Hugging Face Space (SDK: Streamlit) with the same files and secrets.
Note: on free hosting the file claims_db.json is wiped when the app restarts, so the queue and audit trail do not last.

Never paste an API key into the code or a public repository.

## Files
- core.py: estimate, guardrails, risk score, negotiation (plain, testable code)
- app.py: Streamlit interface, claim queue, audit trail
