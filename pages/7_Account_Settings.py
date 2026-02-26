"""Account Settings page for IntervueX."""

import streamlit as st
import database as db
import auth_utils as auth
from ui_utils import apply_global_css
import pandas as pd

# Page config
st.set_page_config(
    page_title="Account Settings - IntervueX",
    page_icon="⚙️",
    layout="wide",
)

apply_global_css()

# Require authentication
auth.require_auth()

st.markdown("# ⚙️ Account Settings")
st.markdown("Manage your account settings and security")
st.divider()

# Get current user
user = auth.get_current_user()

# Profile Section
st.markdown("### 👤 Profile Information")
col1, col2 = st.columns(2)

with col1:
    st.text_input("Full Name", value=user["name"], disabled=True)
    st.text_input("Email Address", value=user["email"], disabled=True)

with col2:
    st.text_input("Account Created", value=user["created_at"][:19], disabled=True)
    last_login = user.get("last_login", "Never")
    st.text_input("Last Login", value=last_login[:19] if last_login != "Never" else "Never", disabled=True)

st.divider()

# Change Password Section
st.markdown("### 🔒 Change Password")
with st.form("change_password_form"):
    current_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm New Password", type="password")
    
    submit_password = st.form_submit_button("Update Password", type="primary")
    
    if submit_password:
        if not current_password or not new_password or not confirm_password:
            st.error("Please fill all password fields")
        elif new_password != confirm_password:
            st.error("New passwords do not match")
        elif len(new_password) < 6:
            st.error("Password must be at least 6 characters")
        else:
            # Verify current password
            if auth.login(user["email"], current_password):
                # Update password
                db.update_user_password(st.session_state.user_id, new_password)
                db.log_activity(
                    user_id=st.session_state.user_id,
                    action="Password changed",
                    action_type="authentication",
                    details="User changed their password"
                )
                st.success("✅ Password updated successfully!")
            else:
                st.error("Current password is incorrect")

st.divider()

# Active Sessions Section
st.markdown("### 🔑 Active Sessions")
st.markdown("Manage your active login sessions across devices")

active_tokens = db.get_user_active_tokens(st.session_state.user_id)

if active_tokens:
    for token_data in active_tokens:
        with st.expander(
            f"Session from {token_data['created_at'][:19]} - "
            f"Last used: {token_data['last_used'][:19]}"
        ):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Token Type:** {token_data['token_type'].title()}")
                st.markdown(f"**Created:** {token_data['created_at'][:19]}")
                st.markdown(f"**Expires:** {token_data['expires_at'][:19]}")
                st.markdown(f"**Last Used:** {token_data['last_used'][:19]}")
                if token_data.get('device_info'):
                    st.markdown(f"**Device:** {token_data['device_info']}")
                
                # Show if this is the current session
                if token_data['token'] == st.session_state.get('auth_token'):
                    st.success("🟢 Current Session")
            
            with col2:
                if st.button("Revoke", key=f"revoke_{token_data['id']}", type="secondary"):
                    db.invalidate_auth_token(token_data['token'])
                    db.log_activity(
                        user_id=st.session_state.user_id,
                        action="Session revoked",
                        action_type="authentication",
                        details=f"Revoked session from {token_data['created_at'][:19]}"
                    )
                    st.success("Session revoked")
                    # If current session, logout
                    if token_data['token'] == st.session_state.get('auth_token'):
                        auth.logout()
                        st.rerun()
                    else:
                        st.rerun()
    
    st.divider()
    if st.button("🚫 Revoke All Sessions", type="secondary"):
        db.invalidate_user_tokens(st.session_state.user_id)
        db.log_activity(
            user_id=st.session_state.user_id,
            action="All sessions revoked",
            action_type="authentication",
            details="User revoked all active sessions"
        )
        st.success("All sessions revoked. You will be logged out.")
        auth.logout()
        st.rerun()
else:
    st.info("No active sessions found")

st.divider()

# Account Statistics
st.markdown("### 📊 Account Statistics")

analytics = db.get_user_analytics(st.session_state.user_id)
stats = analytics["stats"]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Sessions", stats.get("total", 0))

with col2:
    st.metric("Completed", stats.get("completed", 0))

with col3:
    avg_score = stats.get("avg_overall", 0)
    st.metric("Avg Score", f"{avg_score:.1f}" if avg_score else "N/A")

with col4:
    st.metric("Violations", stats.get("total_violations", 0))

st.divider()

# Danger Zone
st.markdown("### ⚠️ Danger Zone")
with st.expander("🗑️ Delete Account", expanded=False):
    st.warning("This action cannot be undone. All your data will be permanently deleted.")
    st.markdown("To delete your account, contact support at support@intervuex.com")
