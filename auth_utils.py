"""Authentication utilities for IntervueX."""

import streamlit as st
import database as db
from datetime import datetime


def init_session_state():
    """Initialize session state for authentication."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'user_email' not in st.session_state:
        st.session_state.user_email = None
    if 'user_name' not in st.session_state:
        st.session_state.user_name = None
    if 'auth_token' not in st.session_state:
        st.session_state.auth_token = None


def login(email: str, password: str) -> bool:
    """Attempt to log in a user."""
    user = db.authenticate_user(email, password)
    if user:
        # Create auth token
        token = db.create_auth_token(user['id'], 'session', expires_in_hours=168)  # 7 days
        
        # Set session state
        st.session_state.authenticated = True
        st.session_state.user_id = user['id']
        st.session_state.user_email = user['email']
        st.session_state.user_name = user['name']
        st.session_state.auth_token = token
        
        # Log activity
        db.log_activity(
            user_id=user['id'],
            action='User logged in',
            action_type='authentication',
            details=f'Login successful for {email}'
        )
        return True
    return False


def register(name: str, email: str, password: str) -> bool:
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = db.get_user_by_email(email)
        if existing_user and existing_user.get('password_hash'):
            return False  # User already registered with password
        
        # Create or update user with password
        user_id = db.create_user(name, email, password)
        
        # Log activity
        db.log_activity(
            user_id=user_id,
            action='User registered',
            action_type='authentication',
            details=f'New user registration: {email}'
        )
        return True
    except Exception as e:
        st.error(f"Registration error: {e}")
        return False


def logout():
    """Log out the current user."""
    if st.session_state.get('auth_token'):
        db.invalidate_auth_token(st.session_state.auth_token)
    
    if st.session_state.get('user_id'):
        db.log_activity(
            user_id=st.session_state.user_id,
            action='User logged out',
            action_type='authentication',
            details=f'Logout: {st.session_state.user_email}'
        )
    
    # Clear session state
    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.user_email = None
    st.session_state.user_name = None
    st.session_state.auth_token = None


def require_auth():
    """Decorator/function to require authentication for a page."""
    init_session_state()
    if not st.session_state.authenticated:
        st.warning("⚠️ Please log in to access this page.")
        st.switch_page("app.py")
        st.stop()
    return True


def get_current_user():
    """Get the current logged-in user."""
    if st.session_state.authenticated and st.session_state.user_id:
        return db.get_user(st.session_state.user_id)
    return None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    init_session_state()
    return st.session_state.authenticated
