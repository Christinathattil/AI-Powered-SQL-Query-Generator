#SqlProj/Pages/__init__.py

from pathlib import Path
import streamlit as st

class PageManager:
    def __init__(self):
        self.pages_dir = Path(__file__).parent
        # No need for page order since sidebar is removed
        self._pages = ["Home.py", "Documentation.py", "Login.py", "AdminApproval","Main.py"]

    def get_page_files(self):
        return [self.pages_dir / page for page in self._pages if (self.pages_dir / page).is_file()]

    def get_page_names(self):
        return [Path(f).stem for f in self.get_page_files()]

class SessionState:
    @staticmethod
    def initialize_session_state():
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
        if "query_history" not in st.session_state:
            st.session_state.query_history = []
        if "current_database" not in st.session_state:
            st.session_state.current_database = "student_trial.db"
        if "generated_sql" not in st.session_state:
            st.session_state.generated_sql = ""
        if "edited_sql" not in st.session_state:
            st.session_state.edited_sql = ""
        if "current_page" not in st.session_state:
            st.session_state.current_page = "Home"  # Default to Home

class NavigationManager:
    @staticmethod
    def require_authentication():
        return st.session_state.get("authenticated", False)

    @staticmethod
    def check_authentication():
        if not NavigationManager.require_authentication():
            st.warning("🚫 Access Denied. Redirecting to Login...")
            st.session_state.current_page = "Login"
            st.rerun()

page_manager = PageManager()
SessionState.initialize_session_state()

__all__ = ['page_manager', 'SessionState', 'NavigationManager', 'PageManager']