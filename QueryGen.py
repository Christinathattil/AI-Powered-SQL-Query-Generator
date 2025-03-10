# SqlProj/QueryGen.py
import streamlit as st
from Pages import SessionState, Home, Login, Main, Documentation, AdminApproval
import os

# Force single-page mode by preventing Streamlit from auto-detecting other pages
os.environ["STREAMLIT_SINGLE_PAGE_MODE"] = "true"

st.set_page_config(
    page_title="SQL Query Generator & Executor",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="collapsed"  # Collapses the sidebar by default
)

# Initialize session state
SessionState.initialize_session_state()

# Complete page mapping
page_map = {
    "Home": Home.main,
    "Login": Login.main,
    "Main": Main.main,
    "Documentation": Documentation.main,
    "AdminApproval": AdminApproval.main,
}

# Set the default page to Home on app start
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"


st.markdown(
    """
    <style>
    /* Hide Streamlit's default sidebar menu */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar navigation customization based on authentication and role
if st.session_state.get("authenticated", False):
    # For logged-in users, remove Home, Login, and Main from sidebar
    if st.session_state.get("admin", False):
        sidebar_options = ["Main","Documentation", "AdminApproval"]
        # If the current page is not one of the allowed sidebar pages, default to Documentation
        if st.session_state.current_page not in sidebar_options:
            st.session_state.current_page = "Main"
    else:
        sidebar_options = ["Main","Documentation"]
        st.session_state.current_page = "Main"
    
    # Render the sidebar navigation
    selected_sidebar = st.sidebar.radio("Navigation", sidebar_options, index=sidebar_options.index(st.session_state.current_page))
    st.session_state.current_page = selected_sidebar

# Run the selected page from the page map
page_map[st.session_state.current_page]()
