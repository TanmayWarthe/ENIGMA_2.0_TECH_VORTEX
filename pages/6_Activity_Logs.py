"""Activity Logs page for IntervueX."""

import streamlit as st
import database as db
import auth_utils as auth
from ui_utils import apply_global_css
import pandas as pd

# Page config
st.set_page_config(
    page_title="Activity Logs - IntervueX",
    page_icon="📋",
    layout="wide",
)

apply_global_css()

# Require authentication
auth.require_auth()

st.markdown("# 📋 Activity Logs")
st.markdown("Track all your activities and interactions on IntervueX")
st.divider()

# Filter options
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    action_type_filter = st.selectbox(
        "Filter by Type",
        ["All", "Authentication", "Interview", "Resume", "Violation", "System"],
        index=0
    )

with col2:
    limit = st.selectbox(
        "Number of records",
        [50, 100, 200, 500],
        index=0
    )

with col3:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

# Map the filter to database values
action_type_map = {
    "All": None,
    "Authentication": "authentication",
    "Interview": "interview",
    "Resume": "resume",
    "Violation": "violation",
    "System": "system"
}

action_type = action_type_map[action_type_filter]

# Get activity logs
logs = db.get_user_activity_logs(
    st.session_state.user_id, 
    limit=limit,
    action_type=action_type
)

if logs:
    st.markdown(f"### Found {len(logs)} activity records")
    st.divider()
    
    # Display logs in a table
    log_data = []
    for log in logs:
        log_data.append({
            "Time": log["created_at"],
            "Action": log["action"],
            "Type": log["action_type"].title(),
            "Details": log.get("details", "—"),
            "Session ID": log.get("session_id", "—"),
            "IP Address": log.get("ip_address", "—")
        })
    
    df = pd.DataFrame(log_data)
    
    # Display as a styled dataframe
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Time": st.column_config.DatetimeColumn(
                "Timestamp",
                format="DD MMM YYYY, HH:mm:ss"
            ),
            "Action": st.column_config.TextColumn(
                "Action",
                width="medium"
            ),
            "Type": st.column_config.TextColumn(
                "Type",
                width="small"
            ),
            "Details": st.column_config.TextColumn(
                "Details",
                width="large"
            )
        }
    )
    
    # Detailed view in expanders
    st.divider()
    st.markdown("### Detailed View")
    
    for i, log in enumerate(logs[:20]):  # Show first 20 in detail
        type_emoji = {
            "authentication": "🔐",
            "interview": "💼",
            "resume": "📄",
            "violation": "⚠️",
            "system": "⚙️",
            "general": "📝"
        }
        
        emoji = type_emoji.get(log["action_type"], "📝")
        
        with st.expander(f"{emoji} {log['action']} - {log['created_at'][:19]}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Action Type:** {log['action_type'].title()}")
                st.markdown(f"**Timestamp:** {log['created_at']}")
                st.markdown(f"**Log ID:** {log['id']}")
            
            with col2:
                st.markdown(f"**Session ID:** {log.get('session_id', 'N/A')}")
                st.markdown(f"**IP Address:** {log.get('ip_address', 'N/A')}")
                st.markdown(f"**User Agent:** {log.get('user_agent', 'N/A')[:50] if log.get('user_agent') else 'N/A'}")
            
            if log.get("details"):
                st.markdown("**Details:**")
                st.info(log["details"])
    
    # Statistics
    st.divider()
    st.markdown("### Activity Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # Count by type
    type_counts = {}
    for log in logs:
        t = log["action_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    
    with col1:
        st.metric("Total Activities", len(logs))
    
    with col2:
        auth_count = type_counts.get("authentication", 0)
        st.metric("🔐 Authentication", auth_count)
    
    with col3:
        interview_count = type_counts.get("interview", 0)
        st.metric("💼 Interview", interview_count)
    
    with col4:
        violation_count = type_counts.get("violation", 0)
        st.metric("⚠️ Violations", violation_count)

else:
    st.info("No activity logs found. Start using IntervueX to see your activity here!")

# Add manual log entry (for testing)
st.divider()
with st.expander("🔧 Add Manual Log Entry (Testing)"):
    action = st.text_input("Action", "Manual test action")
    action_type_manual = st.selectbox("Type", ["general", "authentication", "interview", "resume", "violation", "system"])
    details_manual = st.text_area("Details", "This is a test log entry")
    
    if st.button("Add Log Entry"):
        log_id = db.log_activity(
            user_id=st.session_state.user_id,
            action=action,
            action_type=action_type_manual,
            details=details_manual
        )
        st.success(f"Log entry created with ID: {log_id}")
        st.rerun()
