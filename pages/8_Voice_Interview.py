"""Real-time Voice Interview powered by Vapi Web SDK.

Architecture note
-----------------
Vapi uses Daily.co for WebRTC under the hood. Daily.co calls postMessage() to
communicate between its nested iframe and the parent window.  Browsers block
postMessage when the parent origin is 'null' — which is exactly what Streamlit's
components.html() produces (it renders via <iframe srcdoc="...">, giving null origin).

Fix: spin up a tiny local HTTP server (daemon thread) on port 8503 that serves
the Vapi HTML page with a real origin (http://localhost:8503), then embed it
via st.components.v1.iframe() pointing at that URL.
"""

import os
import threading
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# ── Bootstrap ────────────────────────────────────────────────────────────────
load_dotenv()

st.set_page_config(
    page_title="IntervueX - DSA Voice Interview",
    page_icon="💻",
    layout="wide",
)

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ui_utils import apply_global_css
apply_global_css()

# ── Auth guard ───────────────────────────────────────────────────────────────
if not st.session_state.get("user_id"):
    st.warning("Please sign in from the home page to start a voice interview.")
    st.stop()

# ── Vapi key ─────────────────────────────────────────────────────────────────
_raw = os.getenv("VAPI_PUBLIC_KEY", "") or ""
VAPI_PUBLIC_KEY = _raw.strip().strip('"').strip("'")

VAPI_PORT = 8503   # local HTTP server port for the Vapi widget

# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("## 💻 DSA Voice Interview")
st.markdown("*Powered by Vapi AI — real-time voice-based DSA interview with AI interviewer Alex.*")
st.markdown("---")



# ── Key guard & debug ────────────────────────────────────────────────────────
if not VAPI_PUBLIC_KEY:
    st.error(
        "\u26a0\ufe0f **`VAPI_PUBLIC_KEY` is not set.** "
        "Add it to your `.env` file and **restart Streamlit** to pick it up."
    )

with st.expander("\U0001f50d Debug: Environment check", expanded=not VAPI_PUBLIC_KEY):
    if VAPI_PUBLIC_KEY:
        st.success(
            f"\u2705 VAPI_PUBLIC_KEY is set "
            f"({len(VAPI_PUBLIC_KEY)} chars, starts with: `{VAPI_PUBLIC_KEY[:8]}\u2026`)"
        )
    else:
        st.error("\u274c VAPI_PUBLIC_KEY is empty or missing.")
        st.code("VAPI_PUBLIC_KEY=pk_live_your_key_here", language="bash")
        st.markdown(
            "After editing `.env`, **stop (Ctrl+C) and re-run** `python3 -m streamlit run app.py`"
        )

# ── Build Vapi HTML page ──────────────────────────────────────────────────────
# This HTML is served by a local HTTP server so it has a real origin,
# allowing Daily.co (Vapi's WebRTC layer) to postMessage without CORS errors.
VAPI_WIDGET_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Vapi Voice Interview</title>
<style>
  * { box-sizing:border-box; margin:0; padding:0; }
  body {
    font-family:'Segoe UI',Arial,sans-serif;
    background:linear-gradient(135deg,#F8F9FF 0%,#EEF2FF 100%);
    min-height:100vh; display:flex; flex-direction:column;
    align-items:center; justify-content:center; gap:20px; padding:24px;
  }
  h2 { font-size:1.3rem; font-weight:800; color:#4F46E5; margin-bottom:4px; }
  .subtitle { font-size:.85rem; color:#6B7280; margin-bottom:8px; }

  .status-pill {
    display:inline-flex; align-items:center; gap:8px;
    padding:8px 24px; border-radius:999px;
    font-size:.9rem; font-weight:700; transition:all .3s;
  }
  .idle    { background:rgba(107,114,128,.1); color:#6B7280; border:1.5px solid #D1D5DB; }
  .loading { background:rgba(251,191,36,.15); color:#B45309; border:1.5px solid #FBBF24; }
  .active  { background:rgba(52,211,153,.15); color:#047857; border:1.5px solid #34D399; animation:glow 1.8s infinite; }
  .error   { background:rgba(239,68,68,.1);   color:#B91C1C; border:1.5px solid #FCA5A5; }
  @keyframes glow {
    0%,100% { box-shadow:0 0 0 0 rgba(52,211,153,.5); }
    50%      { box-shadow:0 0 0 10px rgba(52,211,153,0); }
  }

  .controls { display:flex; gap:12px; flex-wrap:wrap; justify-content:center; }
  .btn {
    display:inline-flex; align-items:center; gap:8px;
    padding:14px 36px; border-radius:14px; border:none;
    font-size:1rem; font-weight:700; cursor:pointer;
    transition:transform .15s, box-shadow .15s, opacity .2s;
  }
  .btn:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 6px 24px rgba(0,0,0,.2); }
  .btn:disabled { opacity:.4; cursor:not-allowed; }
  .btn-start { background:linear-gradient(135deg,#4F46E5,#7C3AED); color:#fff; }
  .btn-stop  { background:linear-gradient(135deg,#EF4444,#DC2626); color:#fff; }

  .transcript-box {
    width:100%; max-width:600px;
    background:#fff; border:1px solid #E5E7EB; border-radius:14px;
    padding:16px; min-height:80px; max-height:220px; overflow-y:auto;
    font-size:.87rem; color:#374151; line-height:1.6;
    box-shadow:0 2px 8px rgba(0,0,0,.06);
    display:none;
  }
  .transcript-box .t-label { font-weight:800; color:#4F46E5; margin-bottom:8px; font-size:.8rem; text-transform:uppercase; letter-spacing:.05em; }

  #errorMsg {
    color:#B91C1C; font-size:.84rem; text-align:center;
    background:rgba(239,68,68,.08); border:1px solid #FCA5A5;
    border-radius:10px; padding:10px 16px; display:none; max-width:520px;
  }
  .tip { font-size:.78rem; color:#9CA3AF; text-align:center; }
</style>
</head>
<body>

<div style="text-align:center;">
  <h2>&#127899;&#65039; IntervueX Voice Interview</h2>
  <div class="subtitle">AI Interviewer &bull; DSA &amp; HR &bull; Real-Time</div>
</div>

<div id="statusPill" class="status-pill idle">
  <span id="statusDot">&#9898;</span>
  <span id="statusText">Ready to start</span>
</div>

<div class="controls">
  <button id="startBtn" class="btn btn-start" onclick="startInterview()">
    &#127899;&#65039; Start Voice Interview
  </button>
  <button id="stopBtn" class="btn btn-stop" onclick="stopInterview()" disabled>
    &#9209; Stop Interview
  </button>
</div>

<div class="transcript-box" id="transcriptBox">
  <div class="t-label">&#128172; Live Transcript</div>
  <div id="transcriptContent"></div>
</div>

<div id="errorMsg"></div>

<div class="tip">Grant microphone access when prompted &bull; Chrome/Edge recommended</div>

<script type="module">
  import Vapi from 'https://esm.sh/@vapi-ai/web@latest';

  const KEY = '%%VAPI_KEY%%';
  let vapi = null, active = false;

  const $ = id => document.getElementById(id);

  function setStatus(mode, text) {
    const pill = $('statusPill');
    pill.className = 'status-pill ' + mode;
    $('statusDot').innerHTML = {idle:'&#9898;',loading:'&#128993;',active:'&#128994;',error:'&#128308;'}[mode] || '&#9898;';
    $('statusText').textContent = text;
  }

  function showError(msg) {
    const el = $('errorMsg');
    el.style.display = 'block';
    el.innerHTML = '&#9888;&#65039; ' + msg;
    setStatus('error', 'Error');
    $('startBtn').disabled = false;
    $('stopBtn').disabled = true;
    active = false;
  }

  function addLine(speaker, text) {
    if (!text) return;
    const box = $('transcriptBox');
    box.style.display = 'block';
    const line = document.createElement('div');
    line.style.marginBottom = '5px';
    const isAI = speaker === 'assistant';
    line.innerHTML =
      '<strong style="color:' + (isAI ? '#4F46E5' : '#059669') + ';">' +
      (isAI ? '&#129302; Alex' : '&#128100; You') + ':</strong> ' + text;
    $('transcriptContent').appendChild(line);
    box.scrollTop = box.scrollHeight;
  }

  async function startInterview() {
    if (!KEY) { showError('VAPI_PUBLIC_KEY not set. Edit .env and restart Streamlit.'); return; }
    $('startBtn').disabled = true;
    $('errorMsg').style.display = 'none';
    setStatus('loading', 'Connecting\u2026');

    try {
      vapi = new Vapi(KEY);

      vapi.on('call-start', () => {
        active = true;
        setStatus('active', 'Live \u2014 Interview in progress');
        $('stopBtn').disabled = false;
        $('transcriptBox').style.display = 'block';
        $('transcriptContent').innerHTML = '';
      });

      vapi.on('call-end', () => {
        active = false;
        setStatus('idle', 'Interview ended \u2014 Good job!');
        $('startBtn').disabled = false;
        $('stopBtn').disabled = true;
      });

      vapi.on('error', err => {
        console.error('Vapi error:', err);
        const msg = (err && err.message) ? err.message
          : (err && err.error && err.error.message) ? err.error.message
          : (typeof err === 'string') ? err
          : 'An error occurred. Open browser console (F12) for details.';
        showError(msg);
      });

      vapi.on('message', msg => {
        if (msg && msg.type === 'transcript') addLine(msg.role, msg.transcript);
      });

      vapi.on('speech-start', () => { if (active) setStatus('active', '&#129302; Alex is speaking\u2026'); });
      vapi.on('speech-end',   () => { if (active) setStatus('active', '&#127899; Listening to you\u2026'); });

      await vapi.start({
        transcriber: { provider: 'deepgram', model: 'nova-2', language: 'en-US' },
        model: {
          provider: 'openai',
          model: 'gpt-4o-mini',
          temperature: 0.7,
          messages: [{
            role: 'system',
            content: `You are Alex, a senior technical interviewer at a top-tier tech company.
Conduct structured interviews covering DSA and HR/behavioural questions.

Interview structure:
1. Warm welcome (10-15 seconds).
2. Ask 2-3 DSA questions (arrays, linked lists, trees, graphs, DP, sorting, hashing, recursion).
3. Ask 1-2 HR questions (teamwork, conflict resolution, achievements, goals).
4. Wrap up professionally.

Guidelines:
- Professional, encouraging, concise.
- Let candidate finish before responding.
- Ask follow-ups when answers are unclear.
- Interrupt gracefully, yield when candidate speaks.
- Keep responses under 60 words (unless explaining a solution).
- Give brief verbal feedback after each answer.`
          }]
        },
        voice: { provider: '11labs', voiceId: '21m00Tcm4TlvDq8ikWAM' },
        name: 'IntervueX Voice Interviewer',
        firstMessage: "Hello! I'm Alex, your interviewer today. We'll cover some DSA and HR questions. Take your time before answering. Ready to begin?"
      });

    } catch (err) {
      console.error('startInterview threw:', err);
      showError(err.message || 'Could not start. Check browser console (F12).');
    }
  }

  function stopInterview() {
    if (vapi && active) {
      setStatus('loading', 'Ending call\u2026');
      vapi.stop();
    }
  }

  window.startInterview = startInterview;
  window.stopInterview  = stopInterview;
</script>
</body>
</html>
"""

# ── Local HTTP server (daemon thread) ─────────────────────────────────────────
# Serves the Vapi HTML at http://localhost:8503 so it has a real origin.
# Without a real origin, Daily.co's postMessage is blocked by the browser.

def _make_vapi_html(key: str) -> bytes:
    return VAPI_WIDGET_HTML.replace("%%VAPI_KEY%%", key).encode("utf-8")

def _start_vapi_server(key: str, port: int) -> None:
    import http.server

    html_bytes = _make_vapi_html(key)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html_bytes)))
            # Allow embedding in Streamlit's iframe
            self.send_header("X-Frame-Options", "ALLOWALL")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(html_bytes)

        def log_message(self, *_):  # suppress console noise
            pass

    import socketserver
    with socketserver.TCPServer(("localhost", port), Handler) as httpd:
        httpd.serve_forever()


# Start the server once per Streamlit session (daemon threads die with the process)
if "vapi_server_started" not in st.session_state:
    t = threading.Thread(
        target=_start_vapi_server,
        args=(VAPI_PUBLIC_KEY, VAPI_PORT),
        daemon=True,
    )
    t.start()
    st.session_state.vapi_server_started = True

# ── Embed widget via real URL (fixes postMessage null-origin error) ──────────
st.markdown("### \U0001f399\ufe0f Start Your Voice Interview")
components.iframe(f"http://localhost:{VAPI_PORT}", height=460, scrolling=False)
