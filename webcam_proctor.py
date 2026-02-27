"""Webcam-based AI proctoring module using face-api.js for face detection.

Detects:
- No face visible (candidate left)
- Multiple faces (someone helping)
- Looking away (gaze deviation)

Violations are recorded in the database via Python-side query param sync.
"""

import streamlit as st
import streamlit.components.v1 as components
import database as db


def inject_webcam_proctor(session_id: int, sensitivity: str = "medium"):
    """Inject webcam proctoring component into the interview page.

    Args:
        session_id: Current interview session ID
        sensitivity: Detection sensitivity - 'low', 'medium', or 'high'
    """
    # --- Python-side: read proctor violations written by JS via query params ---
    qp = st.query_params
    js_proctor_count = int(qp.get("proctor_violation", 0) or 0)
    proctor_type = qp.get("proctor_type", "webcam") or "webcam"

    # Only write NEW violations since last Python-side check
    key = f"_proctor_last_violation_{session_id}"
    last_seen = st.session_state.get(key, 0)

    if js_proctor_count > last_seen:
        for _ in range(js_proctor_count - last_seen):
            try:
                db.increment_tab_violations(
                    session_id,
                    violation_type=proctor_type,
                    details="Webcam proctoring violation"
                )
            except Exception:
                pass
        st.session_state[key] = js_proctor_count

    # --- Sensitivity thresholds ---
    thresholds = {
        "low":    {"no_face_delay": 8000, "multi_face_delay": 5000, "gaze_threshold": 0.35},
        "medium": {"no_face_delay": 5000, "multi_face_delay": 3000, "gaze_threshold": 0.25},
        "high":   {"no_face_delay": 3000, "multi_face_delay": 2000, "gaze_threshold": 0.15},
    }
    t = thresholds.get(sensitivity, thresholds["medium"])

    proctor_html = f"""
    <!-- ===== Webcam preview widget ===== -->
    <div id="proctor-container" style="position:fixed;top:10px;left:10px;z-index:99998;">
        <div id="proctor-preview"
             style="position:relative;width:160px;height:120px;border-radius:12px;
                    overflow:hidden;border:2px solid #10B981;
                    box-shadow:0 4px 12px rgba(0,0,0,0.2);
                    background:#000;transition:border-color 0.3s;">
            <video id="proctor-video" autoplay muted playsinline
                   style="width:100%;height:100%;object-fit:cover;"></video>
            <canvas id="proctor-canvas"
                    style="position:absolute;top:0;left:0;width:100%;height:100%;"></canvas>
            <div id="proctor-status"
                 style="position:absolute;bottom:0;left:0;right:0;
                        background:rgba(16,185,129,0.9);color:white;
                        font-size:10px;padding:3px 6px;text-align:center;
                        font-family:'Segoe UI',sans-serif;font-weight:600;
                        letter-spacing:0.03em;">
                Initializing…
            </div>
        </div>
        <!-- Minimize / expand button -->
        <button onclick="toggleProctorPreview()" id="proctor-toggle"
                style="position:absolute;top:-8px;right:-8px;width:22px;height:22px;
                       border-radius:50%;border:none;background:#6B7280;color:white;
                       font-size:12px;cursor:pointer;z-index:2;
                       line-height:22px;text-align:center;font-weight:700;">
            −
        </button>
    </div>

    <!-- ===== Violation alert overlay ===== -->
    <div id="proctor-alert"
         style="display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;
                background:rgba(220,38,38,0.95);z-index:999999;
                align-items:center;justify-content:center;flex-direction:column;
                color:white;font-family:'Segoe UI',sans-serif;">
        <div style="text-align:center;padding:40px;max-width:560px;">
            <div style="font-size:3.5em;margin-bottom:12px;" id="proctor-alert-icon">📹</div>
            <h1 style="font-size:2.2em;margin-bottom:14px;font-weight:800;"
                id="proctor-alert-title">Proctoring Alert!</h1>
            <p style="font-size:1.2em;margin-bottom:10px;opacity:0.95;"
               id="proctor-alert-msg">Violation detected</p>
            <p style="font-size:1em;color:#fca5a5;margin-bottom:28px;font-weight:600;"
               id="proctor-alert-count"></p>
            <button onclick="dismissProctorAlert()"
                    style="padding:12px 32px;font-size:1.05em;cursor:pointer;
                           background:#fff;color:#dc2626;border:none;border-radius:10px;
                           font-weight:700;box-shadow:0 4px 14px rgba(0,0,0,0.2);">
                Return to Interview
            </button>
        </div>
    </div>

    <!-- face-api.js from CDN -->
    <script src="https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js"></script>

    <script>
    (function() {{
        const SESSION_ID    = {session_id};
        const NO_FACE_DELAY   = {t['no_face_delay']};
        const MULTI_FACE_DELAY = {t['multi_face_delay']};
        const GAZE_THRESHOLD  = {t['gaze_threshold']};
        const VIOLATION_COOLDOWN = 12000; // ms between same violation type

        let proctorViolations = parseInt(
            localStorage.getItem('proctor_violations_' + SESSION_ID) || '0'
        );
        let video = null;
        let canvas = null;
        let ctx = null;
        let isMinimized = false;
        let noFaceTimer = null;
        let multiFaceTimer = null;
        let modelsLoaded = false;
        let detectionInterval = null;
        let lastViolationType = '';
        let lastViolationTime = 0;

        // ---- DOM refs ----
        const alertEl    = document.getElementById('proctor-alert');
        const statusEl   = document.getElementById('proctor-status');
        const previewEl  = document.getElementById('proctor-preview');

        // ---- Status helpers ----
        function updateStatus(text, hexColor) {{
            if (statusEl) {{
                statusEl.textContent = text;
                statusEl.style.background = hexColor;
            }}
            if (previewEl) {{
                previewEl.style.borderColor = hexColor;
            }}
        }}

        // ---- Violation recording ----
        function recordProctorViolation(type, detail) {{
            const now = Date.now();
            // Cooldown: don't spam the same type over and over
            if (type === lastViolationType && (now - lastViolationTime) < VIOLATION_COOLDOWN) {{
                return;
            }}
            lastViolationType = type;
            lastViolationTime = now;

            proctorViolations++;
            localStorage.setItem('proctor_violations_' + SESSION_ID, proctorViolations);

            // Show alert overlay
            if (alertEl) {{
                alertEl.style.display = 'flex';
                const iconMap = {{
                    no_face: '👤',
                    multiple_faces: '👥',
                    looking_away: '👁️',
                }};
                const titleMap = {{
                    no_face: 'No Face Detected!',
                    multiple_faces: 'Multiple Faces Detected!',
                    looking_away: 'Looking Away Detected!',
                }};
                const iconEl  = document.getElementById('proctor-alert-icon');
                const titleEl = document.getElementById('proctor-alert-title');
                const msgEl   = document.getElementById('proctor-alert-msg');
                const countEl = document.getElementById('proctor-alert-count');
                if (iconEl)  iconEl.textContent  = iconMap[type]  || '📹';
                if (titleEl) titleEl.textContent = titleMap[type] || 'Proctoring Alert!';
                if (msgEl)   msgEl.textContent   = detail;
                if (countEl) countEl.textContent =
                    'Total proctoring violations this session: ' + proctorViolations;
            }}

            // Persist in URL params so Python (Streamlit) picks it up on next rerun
            try {{
                const url = new URL(window.parent.location.href);
                url.searchParams.set('proctor_violation', proctorViolations);
                url.searchParams.set('proctor_type', type);
                window.parent.history.replaceState(null, '', url.toString());
            }} catch(e) {{}}

            // Also stash in sessionStorage as backup
            try {{
                window.parent.sessionStorage.setItem(
                    'proctor_violation_' + SESSION_ID,
                    JSON.stringify({{ count: proctorViolations, type, detail,
                                     timestamp: new Date().toISOString() }})
                );
            }} catch(e) {{}}
        }}

        // ---- Dismiss overlay & trigger Streamlit rerun to sync DB ----
        window.dismissProctorAlert = function() {{
            if (alertEl) alertEl.style.display = 'none';
            // Navigate to updated URL → forces Streamlit rerun → Python writes to DB
            try {{
                window.parent.location.href = window.parent.location.href;
            }} catch(e) {{}}
        }};

        // ---- Minimize / maximise preview ----
        window.toggleProctorPreview = function() {{
            const preview = document.getElementById('proctor-preview');
            const btn     = document.getElementById('proctor-toggle');
            if (isMinimized) {{
                preview.style.display = 'block';
                btn.textContent = '−';
                isMinimized = false;
            }} else {{
                preview.style.display = 'none';
                btn.textContent = '+';
                isMinimized = true;
            }}
        }};

        // ---- Webcam init ----
        async function initWebcam() {{
            // Guard: face-api must be available
            if (typeof faceapi === 'undefined') {{
                updateStatus('face-api unavailable', '#EF4444');
                console.warn('face-api.js failed to load from CDN');
                return;
            }}

            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{
                    video: {{ width: 320, height: 240, facingMode: 'user' }}
                }});

                video  = document.getElementById('proctor-video');
                canvas = document.getElementById('proctor-canvas');
                if (!video || !canvas) return;

                video.srcObject = stream;
                ctx = canvas.getContext('2d');

                updateStatus('Loading AI…', '#F59E0B');

                const MODEL_URL =
                    'https://cdn.jsdelivr.net/gh/justadudewhohacks/face-api.js@master/weights';
                await Promise.all([
                    faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                    faceapi.nets.faceLandmark68TinyNet.loadFromUri(MODEL_URL),
                ]);
                modelsLoaded = true;

                updateStatus('● Webcam Active', '#10B981');
                startDetection();

            }} catch (err) {{
                console.error('Webcam init error:', err);
                if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {{
                    updateStatus('Camera Denied', '#EF4444');
                }} else {{
                    updateStatus('Camera Error', '#EF4444');
                }}
            }}
        }}

        // ---- Detection loop ----
        function startDetection() {{
            if (!modelsLoaded || !video) return;

            detectionInterval = setInterval(async () => {{
                if (!video || video.paused || video.ended || video.readyState < 2) return;

                let detections;
                try {{
                    detections = await faceapi
                        .detectAllFaces(video,
                            new faceapi.TinyFaceDetectorOptions({{
                                inputSize: 224,
                                scoreThreshold: 0.4
                            }}))
                        .withFaceLandmarks(true);
                }} catch(e) {{
                    return; // detection frame dropped — harmless
                }}

                // Resize canvas to match video
                canvas.width  = video.videoWidth  || 320;
                canvas.height = video.videoHeight || 240;
                if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);

                const faceCount = detections.length;

                // Draw bounding boxes
                detections.forEach(det => {{
                    const box = det.detection.box;
                    if (ctx) {{
                        ctx.strokeStyle = faceCount === 1 ? '#10B981' : '#EF4444';
                        ctx.lineWidth   = 2;
                        ctx.strokeRect(box.x, box.y, box.width, box.height);
                    }}
                }});

                // ── No face ──────────────────────────────────────────────
                if (faceCount === 0) {{
                    if (!noFaceTimer) {{
                        noFaceTimer = setTimeout(() => {{
                            recordProctorViolation('no_face',
                                'No face detected for ' + (NO_FACE_DELAY / 1000) +
                                ' seconds. Please stay visible to the camera.');
                            updateStatus('No Face!', '#EF4444');
                        }}, NO_FACE_DELAY);
                    }}
                }} else {{
                    if (noFaceTimer) {{ clearTimeout(noFaceTimer); noFaceTimer = null; }}
                }}

                // ── Multiple faces ────────────────────────────────────────
                if (faceCount > 1) {{
                    if (!multiFaceTimer) {{
                        multiFaceTimer = setTimeout(() => {{
                            recordProctorViolation('multiple_faces',
                                faceCount + ' faces detected. Only the candidate should be visible.');
                            updateStatus(faceCount + ' Faces Detected!', '#EF4444');
                        }}, MULTI_FACE_DELAY);
                    }}
                }} else {{
                    if (multiFaceTimer) {{ clearTimeout(multiFaceTimer); multiFaceTimer = null; }}
                }}

                // ── Gaze / looking away (single face only) ───────────────
                if (faceCount === 1 && detections[0].landmarks) {{
                    const landmarks = detections[0].landmarks;
                    const leftEye   = landmarks.getLeftEye();   // array of points
                    const rightEye  = landmarks.getRightEye();

                    if (leftEye.length > 0 && rightEye.length > 0) {{
                        // Use eye midpoint relative to face box for more reliable gaze
                        const faceBox = detections[0].detection.box;
                        const eyeMidX = (
                            leftEye.reduce( (s, p) => s + p.x, 0) / leftEye.length +
                            rightEye.reduce((s, p) => s + p.x, 0) / rightEye.length
                        ) / 2;
                        const faceCenterX = faceBox.x + faceBox.width / 2;
                        const deviation   = Math.abs(eyeMidX - faceCenterX) / faceBox.width;

                        if (deviation > GAZE_THRESHOLD) {{
                            recordProctorViolation('looking_away',
                                'You appear to be looking away from the screen. Please focus.');
                            updateStatus('Looking Away!', '#F59E0B');
                        }} else {{
                            updateStatus('● Webcam Active', '#10B981');
                        }}
                    }} else {{
                        updateStatus('● Webcam Active', '#10B981');
                    }}
                }} else if (faceCount === 1) {{
                    updateStatus('● Webcam Active', '#10B981');
                }}

            }}, 1500); // Check every 1.5 s
        }}

        // ── Bootstrap ────────────────────────────────────────────────────
        // Small delay to ensure face-api script has executed
        setTimeout(initWebcam, 500);

        // Cleanup webcam stream on page unload
        window.addEventListener('beforeunload', () => {{
            if (detectionInterval) clearInterval(detectionInterval);
            if (video && video.srcObject) {{
                video.srcObject.getTracks().forEach(t => t.stop());
            }}
        }});

    }})();
    </script>
    """
    components.html(proctor_html, height=0)


def get_proctor_violation_badge() -> str:
    """Return HTML for a small inline proctoring violation badge."""
    return """
    <div id="proctor-badge"
         style="display:inline-flex;align-items:center;gap:6px;
                background:#FEF2F2;border:1px solid #FECACA;
                border-radius:8px;padding:4px 12px;font-size:0.8rem;">
        <span style="color:#EF4444;">📹</span>
        <span style="color:#991B1B;font-weight:700;" id="proctor-badge-count">0</span>
        <span style="color:#991B1B;">proctoring alerts</span>
    </div>
    """
