import streamlit as st

def apply_global_css():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
    }
    
    .block-container {
        max-width: 100% !important;
        padding-left: 3rem !important;
        padding-right: 3rem !important;
    }
    
    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.1);
    }
    
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: transparent;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(128, 128, 128, 0.25);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(128, 128, 128, 0.4);
    }
    
    .stButton > button {
        background-color: #4F46E5 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.5rem !important;
        transition: all 0.2s ease !important;
        letter-spacing: 0.5px !important;
    }
    .stButton > button:hover {
        background-color: #4338CA !important;
        transform: scale(1.02);
    }
    
    /* File Uploader Customization */
    [data-testid="stFileUploader"] section {
        border: 2px dashed #4F46E5 !important;
        background-color: #EEF2FF !important;
        border-radius: 12px;
    }
    
    [data-testid="stFileUploader"] button {
        background-color: #4F46E5 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stFileUploader"] button:hover {
        background-color: #4338CA !important;
    }
    
    [data-testid="stFileUploaderDropzone"] svg {
        color: #4F46E5 !important;
        fill: #4F46E5 !important;
    }
    .st-emotion-cache-1gulkj5, .st-emotion-cache-1wmy9hl, .st-emotion-cache-5z2nqc {
        color: #4F46E5 !important;
        fill: #4F46E5 !important;
    }
    .st-emotion-cache-13m7zcc svg { /* explicit catch for uploader icon */
        color: #4F46E5 !important;
    }
    
    /* Floating Header Logo */
    .fixed-logo {
        position: fixed;
        top: 20px;
        left: 65px;
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4F46E5, #7C3AED, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        z-index: 999999;
        pointer-events: none;
    }

    /* Center Sidebar Toggle Button Vertically */
    [data-testid="collapsedControl"] {
        top: 50vh !important;
        transform: translateY(-50%) !important;
        background-color: #4F46E5 !important;
        color: white !important;
        border-radius: 0 8px 8px 0 !important;
        box-shadow: 2px 0 8px rgba(0,0,0,0.1);
        z-index: 999999 !important;
    }
    
    /* Attempt to style the expand/collapse button when sidebar is open */
    [title="Collapse sidebar"] {
        position: fixed !important;
        top: 50vh !important;
        transform: translateY(-50%) !important;
        background-color: #4F46E5 !important;
        color: white !important;
        border-radius: 8px 0 0 8px !important;
        z-index: 999999 !important;
        right: 0 !important;
    }
</style>
<div class="fixed-logo">IntervueX</div>
    """, unsafe_allow_html=True)
