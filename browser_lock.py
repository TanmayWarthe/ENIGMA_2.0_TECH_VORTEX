"""Browser locking mechanism to prevent tab switching during interviews."""

import streamlit.components.v1 as components


def inject_browser_lock(session_id: int):
    """Inject JavaScript for browser locking and tab switch detection.
    
    This monitors:
    - Document visibility changes (tab switching)
    - Window blur events (switching to other apps)
    - Right-click prevention
    - Keyboard shortcut prevention (Ctrl+Tab, Alt+Tab, etc.)
    """
    lock_js = f"""
    <div id="browser-lock-overlay" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh;
         background: rgba(220,38,38,0.95); z-index:999999; display:flex; align-items:center; justify-content:center;
         flex-direction:column; color:white; font-family:sans-serif;">
        <div style="text-align:center; padding:40px;">
            <h1 style="font-size:3em; margin-bottom:20px;">Warning!</h1>
            <p style="font-size:1.5em; margin-bottom:10px;">Tab switch / window change detected!</p>
            <p style="font-size:1.2em; margin-bottom:30px;">This violation has been recorded.</p>
            <p id="violation-count" style="font-size:1.1em; color:#fca5a5;"></p>
            <button onclick="document.getElementById('browser-lock-overlay').style.display='none'"
                    style="margin-top:20px; padding:12px 30px; font-size:1.1em; cursor:pointer;
                           background:#fff; color:#dc2626; border:none; border-radius:8px; font-weight:bold;">
                Return to Interview
            </button>
        </div>
    </div>

    <script>
        (function() {{
            const SESSION_ID = {session_id};
            let violationCount = parseInt(localStorage.getItem('violations_' + SESSION_ID) || '0');
            let isLocked = true;

            function recordViolation(type) {{
                if (!isLocked) return;
                violationCount++;
                localStorage.setItem('violations_' + SESSION_ID, violationCount);

                // Show warning overlay
                const overlay = document.getElementById('browser-lock-overlay');
                if (overlay) {{
                    overlay.style.display = 'flex';
                    document.getElementById('violation-count').textContent =
                        'Total violations this session: ' + violationCount;
                }}

                // Send violation to Streamlit via query params
                const url = new URL(window.parent.location.href);
                url.searchParams.set('tab_violation', violationCount);
                url.searchParams.set('violation_type', type);
                window.parent.history.replaceState(null, '', url.toString());

                // Also store in sessionStorage for Streamlit to pick up
                window.parent.sessionStorage.setItem('tab_violation_' + SESSION_ID, JSON.stringify({{
                    count: violationCount,
                    type: type,
                    timestamp: new Date().toISOString()
                }}));
            }}

            // Monitor visibility changes
            document.addEventListener('visibilitychange', function() {{
                if (document.hidden) {{
                    recordViolation('tab_switch');
                }}
            }});

            // Monitor window blur (switching to other applications)
            window.addEventListener('blur', function() {{
                recordViolation('window_blur');
            }});

            // Also monitor parent window
            try {{
                window.parent.document.addEventListener('visibilitychange', function() {{
                    if (window.parent.document.hidden) {{
                        recordViolation('parent_tab_switch');
                    }}
                }});
                window.parent.addEventListener('blur', function() {{
                    recordViolation('parent_window_blur');
                }});
            }} catch(e) {{}}

            // Prevent right-click
            document.addEventListener('contextmenu', function(e) {{
                e.preventDefault();
                return false;
            }});

            // Prevent common shortcuts
            document.addEventListener('keydown', function(e) {{
                // Ctrl+T (new tab), Ctrl+N (new window), Ctrl+W (close tab)
                if (e.ctrlKey && (e.key === 't' || e.key === 'n' || e.key === 'w')) {{
                    e.preventDefault();
                    recordViolation('shortcut_' + e.key);
                }}
                // F12 (dev tools)
                if (e.key === 'F12') {{
                    e.preventDefault();
                    recordViolation('devtools_attempt');
                }}
            }});

            // Display violation count badge
            const badge = document.createElement('div');
            badge.id = 'violation-badge';
            badge.style.cssText = 'position:fixed;top:10px;right:10px;background:#dc2626;color:white;padding:5px 12px;border-radius:20px;font-size:12px;z-index:99999;font-family:sans-serif;display:' + (violationCount > 0 ? 'block' : 'none');
            badge.textContent = 'Violations: ' + violationCount;
            document.body.appendChild(badge);

            // Update badge
            const observer = new MutationObserver(function() {{
                badge.textContent = 'Violations: ' + violationCount;
                badge.style.display = violationCount > 0 ? 'block' : 'none';
            }});

            window._unlockBrowser = function() {{
                isLocked = false;
                if (badge) badge.style.display = 'none';
            }};

            console.log('Browser lock active for session ' + SESSION_ID);
        }})();
    </script>
    """
    components.html(lock_js, height=0)


def get_violation_count_js(session_id: int) -> str:
    """Return JavaScript to get violation count from localStorage."""
    return f"""
    <script>
        const count = localStorage.getItem('violations_{session_id}') || '0';
        const el = document.getElementById('streamlit-violation-count');
        if (el) el.textContent = count;
    </script>
    """


def clear_violations(session_id: int):
    """Return JavaScript to clear violation count."""
    return f"""
    <script>
        localStorage.removeItem('violations_{session_id}');
    </script>
    """
