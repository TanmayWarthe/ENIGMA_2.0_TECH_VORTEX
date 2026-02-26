"""Voice handler module using Deepgram for Speech-to-Text and gTTS for Text-to-Speech."""

import os
import io
import httpx
from dotenv import load_dotenv

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

load_dotenv()

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
DEEPGRAM_URL = "https://api.deepgram.com/v1/listen"


def transcribe_audio(audio_bytes: bytes, mimetype: str = "audio/wav") -> dict:
    """Transcribe audio bytes using Deepgram API.
    
    Returns:
        dict with 'transcript', 'confidence', and 'words' keys.
    """
    if not DEEPGRAM_API_KEY:
        return {
            "transcript": "",
            "confidence": 0,
            "words": [],
            "error": "Deepgram API key not configured"
        }

    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": mimetype,
    }

    params = {
        "model": "nova-2",
        "smart_format": "true",
        "punctuate": "true",
        "diarize": "false",
        "language": "en",
        "filler_words": "true",
    }

    try:
        response = httpx.post(
            DEEPGRAM_URL,
            headers=headers,
            params=params,
            content=audio_bytes,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        result = data.get("results", {}).get("channels", [{}])[0].get("alternatives", [{}])[0]

        return {
            "transcript": result.get("transcript", ""),
            "confidence": result.get("confidence", 0),
            "words": result.get("words", []),
            "error": None
        }
    except httpx.HTTPStatusError as e:
        return {
            "transcript": "",
            "confidence": 0,
            "words": [],
            "error": f"Deepgram API error: {e.response.status_code} - {e.response.text}"
        }
    except Exception as e:
        return {
            "transcript": "",
            "confidence": 0,
            "words": [],
            "error": f"Transcription error: {str(e)}"
        }


def analyze_speech_patterns(words: list) -> dict:
    """Analyze speech patterns from word-level data.
    
    Returns metrics about speaking pace, filler words, and pauses.
    """
    if not words:
        return {
            "speaking_pace_wpm": 0,
            "filler_word_count": 0,
            "filler_words_found": [],
            "total_duration_seconds": 0,
            "pause_count": 0,
            "avg_pause_duration": 0,
        }

    filler_words = {"um", "uh", "like", "you know", "basically", "actually",
                    "so", "well", "I mean", "right", "okay"}

    total_words = len(words)
    if total_words == 0:
        return {
            "speaking_pace_wpm": 0,
            "filler_word_count": 0,
            "filler_words_found": [],
            "total_duration_seconds": 0,
            "pause_count": 0,
            "avg_pause_duration": 0,
        }

    start_time = words[0].get("start", 0)
    end_time = words[-1].get("end", 0)
    duration = end_time - start_time

    wpm = (total_words / duration * 60) if duration > 0 else 0

    fillers_found = []
    for w in words:
        word_text = w.get("word", "").lower().strip(".,!?")
        if word_text in filler_words:
            fillers_found.append(word_text)

    # Detect pauses (gaps > 1 second between words)
    pauses = []
    for i in range(1, len(words)):
        gap = words[i].get("start", 0) - words[i - 1].get("end", 0)
        if gap > 1.0:
            pauses.append(gap)

    return {
        "speaking_pace_wpm": round(wpm),
        "filler_word_count": len(fillers_found),
        "filler_words_found": fillers_found,
        "total_duration_seconds": round(duration, 1),
        "pause_count": len(pauses),
        "avg_pause_duration": round(sum(pauses) / len(pauses), 1) if pauses else 0,
    }


def synthesize_speech(text: str, voice: str = "default") -> dict:
    """Convert text to speech audio bytes using gTTS (Google Text-to-Speech).

    Returns:
        dict with 'audio' (bytes) and 'error' keys.
    """
    if not GTTS_AVAILABLE:
        return {"audio": b"", "error": "gTTS library not installed. Run: pip install gTTS"}

    if not text or not text.strip():
        return {"audio": b"", "error": "No text provided for synthesis"}

    try:
        tts = gTTS(text=text, lang="en", slow=False)
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()
        return {"audio": audio_bytes, "error": None}
    except Exception as e:
        return {"audio": b"", "error": f"TTS error: {str(e)}"}


def get_browser_stt_component() -> str:
    """Return an HTML/JS component that uses the Web Speech API for speech recognition.

    This injects a browser-based speech-to-text widget using the built-in
    Web Speech API (works in Chrome, Edge, and other Chromium-based browsers).
    The recognized text is sent back to Streamlit via session storage.
    """
    return """
    <div id="stt-container" style="text-align:center;padding:15px;">
        <button id="stt-btn" onclick="toggleRecording()"
                style="background:#4F46E5;color:white;border:none;border-radius:12px;
                       padding:12px 24px;font-size:1rem;font-weight:600;cursor:pointer;
                       transition:all 0.2s ease;display:inline-flex;align-items:center;gap:8px;">
            <span id="stt-icon">&#127908;</span>
            <span id="stt-label">Click to Speak</span>
        </button>
        <p id="stt-status" style="margin-top:10px;font-size:0.9rem;color:#6B7280;">Ready to listen...</p>
        <div id="stt-result" style="margin-top:10px;padding:10px;background:#F3F4F6;border-radius:8px;
                                     min-height:40px;text-align:left;font-size:0.95rem;display:none;"></div>
    </div>

    <script>
        let recognition = null;
        let isRecording = false;
        let finalTranscript = '';

        function toggleRecording() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        }

        function startRecording() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                document.getElementById('stt-status').textContent =
                    'Speech recognition not supported. Please use Chrome or Edge.';
                document.getElementById('stt-status').style.color = '#EF4444';
                return;
            }

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            finalTranscript = '';

            recognition.onstart = function() {
                isRecording = true;
                document.getElementById('stt-btn').style.background = '#EF4444';
                document.getElementById('stt-label').textContent = 'Stop Listening';
                document.getElementById('stt-icon').innerHTML = '&#9209;';
                document.getElementById('stt-status').textContent = 'Listening... Speak now.';
                document.getElementById('stt-status').style.color = '#10B981';
                document.getElementById('stt-result').style.display = 'block';
            };

            recognition.onresult = function(event) {
                let interimTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript + ' ';
                    } else {
                        interimTranscript += event.results[i][0].transcript;
                    }
                }
                document.getElementById('stt-result').innerHTML =
                    '<strong>Recognized:</strong> ' + finalTranscript +
                    '<span style="color:#9CA3AF;">' + interimTranscript + '</span>';

                // Store transcript for Streamlit to pick up
                window.parent.sessionStorage.setItem('browser_stt_transcript', finalTranscript.trim());
            };

            recognition.onerror = function(event) {
                document.getElementById('stt-status').textContent = 'Error: ' + event.error;
                document.getElementById('stt-status').style.color = '#EF4444';
                stopRecording();
            };

            recognition.onend = function() {
                if (isRecording) {
                    // Restart if still recording (continuous mode can stop)
                    recognition.start();
                }
            };

            recognition.start();
        }

        function stopRecording() {
            isRecording = false;
            if (recognition) {
                recognition.stop();
            }
            document.getElementById('stt-btn').style.background = '#4F46E5';
            document.getElementById('stt-label').textContent = 'Click to Speak';
            document.getElementById('stt-icon').innerHTML = '&#127908;';
            document.getElementById('stt-status').textContent =
                finalTranscript ? 'Recording complete. Transcript saved.' : 'Ready to listen...';
            document.getElementById('stt-status').style.color = '#6B7280';

            // Final save
            if (finalTranscript) {
                window.parent.sessionStorage.setItem('browser_stt_transcript', finalTranscript.trim());
            }
        }
    </script>
    """
