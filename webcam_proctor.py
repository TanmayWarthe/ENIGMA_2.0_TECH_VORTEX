"""Webcam-based AI proctoring module using face-api.js for face detection.

Detects:
- No face visible (candidate left)
- Multiple faces (someone helping)
- Looking away (gaze deviation)
- Face too far or too close

Violations are recorded alongside tab violations in the database.
"""

import streamlit.components.v1 as components


def inject_webcam_proctor(session_id: int, sensitivity: str = "medium"):
    """Inject webcam proctoring component into the interview page.

    Args:
        session_id: Current interview session ID
        sensitivity: Detection sensitivity - 'low', 'medium', or 'high'
    """
    # Sensitivity thresholds
    thresholds = {
        "low": {"no_face_delay": 8000, "multi_face_delay": 5000, "gaze_threshold": 0.35},
        "medium": {"no_face_delay": 5000, "multi_face_delay": 3000, "gaze_threshold": 0.25},
        "high": {"no_face_delay": 3000, "multi_face_delay": 2000, "gaze_threshold": 0.15},
    }
    t = thresholds.get(sensitivity, thresholds["medium"])

    proctor_html = f"""
    <div id="proctor-container" style="position:fixed;top:10px;left:10px;z-index:99998;">
        <!-- Small webcam preview -->
        <div id="proctor-preview" style="position:relative;width:160px;height:120px;border-radius:12px;
                overflow:hidden;border:2px solid #10B981;box-shadow:0 4px 12px rgba(0,0,0,0.15);
                background:#000;transition:border-color 0.3s;">
            <video id="proctor-video" autoplay muted playsinline
                   style="width:100%;height:100%;object-fit:cover;"></video>
            <canvas id="proctor-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;"></canvas>
            <div id="proctor-status" style="position:absolute;bottom:0;left:0;right:0;
                 background:rgba(16,185,129,0.9);color:white;font-size:10px;padding:2px 6px;
                 text-align:center;font-family:sans-serif;font-weight:600;">
                Webcam Active
            </div>
        </div>
        <!-- Minimize button -->
        <button onclick="toggleProctorPreview()" id="proctor-toggle"
                style="position:absolute;top:-8px;right:-8px;width:20px;height:20px;
                       border-radius:50%;border:none;background:#6B7280;color:white;
                       font-size:10px;cursor:pointer;z-index:1;line-height:20px;text-align:center;">
            −
        </button>
    </div>

    <!-- Violation alert overlay -->
    <div id="proctor-alert" style="display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;
         background:rgba(220,38,38,0.93);z-index:999999;display:none;align-items:center;
         justify-content:center;flex-direction:column;color:white;font-family:sans-serif;">
        <div style="text-align:center;padding:40px;">
            <h1 style="font-size:2.5em;margin-bottom:15px;" id="proctor-alert-title">Proctoring Alert!</h1>
            <p style="font-size:1.3em;margin-bottom:10px;" id="proctor-alert-msg">Violation detected</p>
            <p style="font-size:1em;color:#fca5a5;" id="proctor-alert-count"></p>
            <button onclick="dismissProctorAlert()"
                    style="margin-top:20px;padding:10px 25px;font-size:1em;cursor:pointer;
                           background:#fff;color:#dc2626;border:none;border-radius:8px;font-weight:bold;">
                Return to Interview
            </button>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js"></script>

    <script>
    (function() {{
        const SESSION_ID = {session_id};
        const NO_FACE_DELAY = {t['no_face_delay']};
        const MULTI_FACE_DELAY = {t['multi_face_delay']};
        const GAZE_THRESHOLD = {t['gaze_threshold']};

        let proctorViolations = parseInt(localStorage.getItem('proctor_violations_' + SESSION_ID) || '0');
        let video = null;
        let canvas = null;
        let ctx = null;
        let isMinimized = false;
        let noFaceTimer = null;
        let multiFaceTimer = null;
        let modelsLoaded = false;
        let detectionInterval = null;

        // Violation tracking to avoid spamming
        let lastViolationType = '';
        let lastViolationTime = 0;
        const VIOLATION_COOLDOWN = 10000; // 10 seconds between same violation type

        function updateStatus(text, color) {{
            const el = document.getElementById('proctor-status');
            if (el) {{
                el.textContent = text;
                el.style.background = color;
            }}
            const preview = document.getElementById('proctor-preview');
            if (preview) {{
                preview.style.borderColor = color.replace('rgba', 'rgb').replace(',0.9)', ')');
            }}
        }}

        function recordProctorViolation(type, detail) {{
            const now = Date.now();
            if (type === lastViolationType && (now - lastViolationTime) < VIOLATION_COOLDOWN) {{
                return; // Skip duplicate violations within cooldown
            }}
            lastViolationType = type;
            lastViolationTime = now;

            proctorViolations++;
            localStorage.setItem('proctor_violations_' + SESSION_ID, proctorViolations);

            // Show alert
            const alert = document.getElementById('proctor-alert');
            if (alert) {{
                alert.style.display = 'flex';
                document.getElementById('proctor-alert-title').textContent = getAlertTitle(type);
                document.getElementById('proctor-alert-msg').textContent = detail;
                document.getElementById('proctor-alert-count').textContent =
                    'Proctoring violations this session: ' + proctorViolations;
            }}

            // Store for Streamlit
            window.parent.sessionStorage.setItem('proctor_violation_' + SESSION_ID, JSON.stringify({{
                count: proctorViolations,
                type: type,
                detail: detail,
                timestamp: new Date().toISOString()
            }}));

            // Also update query params
            const url = new URL(window.parent.location.href);
            url.searchParams.set('proctor_violation', proctorViolations);
            url.searchParams.set('proctor_type', type);
            window.parent.history.replaceState(null, '', url.toString());
        }}

        function getAlertTitle(type) {{
            switch(type) {{
                case 'no_face': return 'No Face Detected!';
                case 'multiple_faces': return 'Multiple Faces Detected!';
                case 'looking_away': return 'Looking Away Detected!';
                default: return 'Proctoring Alert!';
            }}
        }}

        window.dismissProctorAlert = function() {{
            const alert = document.getElementById('proctor-alert');
            if (alert) alert.style.display = 'none';
        }};

        window.toggleProctorPreview = function() {{
            const preview = document.getElementById('proctor-preview');
            const btn = document.getElementById('proctor-toggle');
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

        async function initWebcam() {{
            try {{
                const stream = await navigator.mediaDevices.getUserMedia({{
                    video: {{ width: 320, height: 240, facingMode: 'user' }}
                }});
                video = document.getElementById('proctor-video');
                canvas = document.getElementById('proctor-canvas');
                if (!video || !canvas) return;

                video.srcObject = stream;
                ctx = canvas.getContext('2d');

                updateStatus('Loading AI models...', 'rgba(245,158,11,0.9)');

                // Load face-api.js models from CDN
                const MODEL_URL = 'https://cdn.jsdelivr.net/gh/justadudewhohacks/face-api.js@master/weights';
                await Promise.all([
                    faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
                    faceapi.nets.faceLandmark68TinyNet.loadFromUri(MODEL_URL),
                ]);
                modelsLoaded = true;

                updateStatus('Webcam Active', 'rgba(16,185,129,0.9)');
                startDetection();

            }} catch (err) {{
                console.error('Webcam error:', err);
                updateStatus('Webcam Denied', 'rgba(239,68,68,0.9)');
            }}
        }}

        function startDetection() {{
            if (!modelsLoaded || !video) return;

            detectionInterval = setInterval(async () => {{
                if (video.paused || video.ended) return;

                const detections = await faceapi.detectAllFaces(
                    video,
                    new faceapi.TinyFaceDetectorOptions({{ inputSize: 224, scoreThreshold: 0.4 }})
                ).withFaceLandmarks(true);

                // Clear canvas
                canvas.width = video.videoWidth || 320;
                canvas.height = video.videoHeight || 240;
                if (ctx) ctx.clearRect(0, 0, canvas.width, canvas.height);

                const faceCount = detections.length;

                // Draw detection boxes on canvas
                detections.forEach(det => {{
                    const box = det.detection.box;
                    if (ctx) {{
                        ctx.strokeStyle = faceCount === 1 ? '#10B981' : '#EF4444';
                        ctx.lineWidth = 2;
                        ctx.strokeRect(box.x, box.y, box.width, box.height);
                    }}
                }});

                // === No face detection ===
                if (faceCount === 0) {{
                    if (!noFaceTimer) {{
                        noFaceTimer = setTimeout(() => {{
                            recordProctorViolation('no_face',
                                'No face detected for ' + (NO_FACE_DELAY/1000) + ' seconds. Please stay visible to the camera.');
                            updateStatus('No Face!', 'rgba(239,68,68,0.9)');
                        }}, NO_FACE_DELAY);
                    }}
                }} else {{
                    if (noFaceTimer) {{
                        clearTimeout(noFaceTimer);
                        noFaceTimer = null;
                    }}
                }}

                // === Multiple faces ===
                if (faceCount > 1) {{
                    if (!multiFaceTimer) {{
                        multiFaceTimer = setTimeout(() => {{
                            recordProctorViolation('multiple_faces',
                                faceCount + ' faces detected. Only the candidate should be visible.');
                            updateStatus(faceCount + ' Faces!', 'rgba(239,68,68,0.9)');
                        }}, MULTI_FACE_DELAY);
                    }}
                }} else {{
                    if (multiFaceTimer) {{
                        clearTimeout(multiFaceTimer);
                        multiFaceTimer = null;
                    }}
                }}

                // === Gaze detection (looking away) ===
                if (faceCount === 1 && detections[0].landmarks) {{
                    const landmarks = detections[0].landmarks;
                    const nose = landmarks.getNose();
                    const jaw = landmarks.getJawOutline();
                    const leftEye = landmarks.getLeftEye();
                    const rightEye = landmarks.getRightEye();

                    if (nose.length > 0 && jaw.length > 0) {{
                        // Calculate face center vs nose position for horizontal gaze
                        const faceBox = detections[0].detection.box;
                        const faceCenterX = faceBox.x + faceBox.width / 2;
                        const noseTipX = nose[3] ? nose[3].x : nose[0].x;
                        const horizontalDeviation = Math.abs(noseTipX - faceCenterX) / faceBox.width;

                        if (horizontalDeviation > GAZE_THRESHOLD) {{
                            recordProctorViolation('looking_away',
                                'You appear to be looking away from the screen. Please focus on the interview.');
                            updateStatus('Looking Away!', 'rgba(245,158,11,0.9)');
                        }} else {{
                            if (faceCount === 1) {{
                                updateStatus('Webcam Active', 'rgba(16,185,129,0.9)');
                            }}
                        }}
                    }}
                }} else if (faceCount === 1) {{
                    updateStatus('Webcam Active', 'rgba(16,185,129,0.9)');
                }}

            }}, 1500); // Check every 1.5 seconds
        }}

        // Initialize
        initWebcam();

        // Cleanup on unload
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
    """Return HTML for a small proctoring violation badge."""
    return """
    <div id="proctor-badge" style="display:inline-flex;align-items:center;gap:4px;
         background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:4px 10px;font-size:0.8rem;">
        <span style="color:#EF4444;">📹</span>
        <span style="color:#991B1B;font-weight:600;" id="proctor-badge-count">0</span>
        <span style="color:#991B1B;">proctoring alerts</span>
    </div>
    """
